"""Lógica de negocio del Directorio (capability directory, F4).

Los ViewSets son delgados y delegan aquí. Toda operación multi-tabla va en
`transaction.atomic()` y se audita con `@audit`. Las reglas que dependen del estado de
la BD (unicidad del número entre fichas no inactivas, vínculo O2O ya tomado) viven aquí
y se emiten por el contrato de errores uniforme: `Conflict` (409) y `ValidationError`
(400, mapeado al campo). El dígito verificador se valida en el serializer (formato);
aquí se asume `data` ya validado.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction
from rest_framework import serializers

from apps.accounts.models import User
from apps.common.audit import audit
from apps.common.audit_rules import AuditAction
from apps.common.exceptions import Conflict
from apps.pricing.models import PriceList

from .models import Ficha, FichaRole, FichaStatus

# Acción de transición -> (estados de origen permitidos, estado destino).
_STATUS_TRANSITIONS: dict[str, tuple[tuple[str, ...], str]] = {
    "block": ((FichaStatus.ACTIVO,), FichaStatus.BLOQUEADO),
    "unblock": ((FichaStatus.BLOQUEADO,), FichaStatus.ACTIVO),
    "deactivate": ((FichaStatus.ACTIVO, FichaStatus.BLOQUEADO), FichaStatus.INACTIVO),
    "reactivate": ((FichaStatus.INACTIVO,), FichaStatus.ACTIVO),
}


def _ensure_unique_identification(number: str, *, exclude_pk: Any = None) -> None:
    """El número MUST ser único entre las fichas no inactivas (409 si choca)."""
    qs = Ficha.objects.exclude(status=FichaStatus.INACTIVO).filter(identification_number=number)
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    if qs.exists():
        raise Conflict("Ya existe una ficha activa con este número de identificación.")


@audit(action=AuditAction.CREATE, entity="Ficha")
def create_ficha(*, user: User, data: dict[str, Any]) -> Ficha:
    """Crea una ficha en estado ACTIVO con identificación única."""
    with transaction.atomic():
        _ensure_unique_identification(data["identification_number"])
        ficha = Ficha.objects.create(**data)
    return ficha


@audit(action=AuditAction.UPDATE, entity="Ficha")
def update_ficha(*, user: User, ficha: Ficha, data: dict[str, Any]) -> Ficha:
    """Edita los datos no-estado de una ficha (no cambia `status` ni `user`)."""
    with transaction.atomic():
        new_number = data.get("identification_number", ficha.identification_number)
        _ensure_unique_identification(new_number, exclude_pk=ficha.pk)
        for field, value in data.items():
            setattr(ficha, field, value)
        ficha.save()
    return ficha


@audit(action=AuditAction.STATE_CHANGE, entity="Ficha")
def change_status(*, user: User, ficha: Ficha, action: str) -> Ficha:
    """Aplica una transición de estado (block/unblock/deactivate/reactivate)."""
    allowed_from, target = _STATUS_TRANSITIONS[action]
    if ficha.status not in allowed_from:
        raise Conflict(f"No se puede aplicar '{action}' a una ficha en estado {ficha.status}.")
    with transaction.atomic():
        # Al reactivar, el número vuelve al universo de unicidad de fichas no inactivas.
        if target == FichaStatus.ACTIVO:
            _ensure_unique_identification(ficha.identification_number, exclude_pk=ficha.pk)
        ficha.status = target
        ficha.save(update_fields=["status", "updated_at"])
    return ficha


@audit(action=AuditAction.UPDATE, entity="Ficha")
def assign_price_list(*, user: User, ficha: Ficha, price_list: PriceList | None) -> Ficha:
    """Asigna (o desasigna) una lista de precios a la ficha (F6).

    Integridad asignación↔rol: solo una ficha con rol CLIENTE puede tener lista asignada
    (400 mapeado al campo `price_list` si no lo tiene). Desasignar (`price_list=None`) es
    siempre válido. Es la 1.ª defensa; el `PROTECT` del FK y la unicidad de baja son las
    demás.
    """
    if price_list is not None and FichaRole.CLIENTE not in ficha.roles:
        raise serializers.ValidationError(
            {"price_list": ["Solo una ficha con rol cliente puede tener una lista asignada."]}
        )
    with transaction.atomic():
        ficha.price_list = price_list
        ficha.save(update_fields=["price_list", "updated_at"])
    return ficha


@audit(action=AuditAction.UPDATE, entity="Ficha")
def link_user(*, user: User, ficha: Ficha, target: User) -> Ficha:
    """Vincula la ficha a un usuario en relación 1:1 (409 si el usuario ya tiene ficha)."""
    existing = Ficha.objects.filter(user=target).exclude(pk=ficha.pk).first()
    if existing is not None:
        raise Conflict("El usuario ya está vinculado a otra ficha.")
    with transaction.atomic():
        ficha.user = target
        ficha.save(update_fields=["user", "updated_at"])
    return ficha
