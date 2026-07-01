"""Lógica de negocio de la configuración global (capability system-settings, F8).

Las views son delgadas y delegan aquí. `get_settings()` resuelve el singleton (lo crea
la primera vez); las otras fases (kardex, merma) lo consumen como regla de negocio, sin
pasar por los permisos del usuario final. `update_settings()` aplica los toggles dentro
de `transaction.atomic()` y deja rastro de auditoría por cada campo cambiado.

Auditoría con detalle campo/valor-anterior/valor-nuevo: el `AuditLog` del bootstrap ya
modela esos campos y `config.yaml` exige registrarlos. Como el decorador `@audit` solo
deja el rastro acción/entidad (el detalle campo-nivel se completa en `add-audit-rules`),
aquí se emite explícitamente un `AuditLog` por toggle modificado — es la realización fiel
del Requirement "Auditoría del cambio de configuración".
"""

from __future__ import annotations

from typing import Any

from django.db import transaction

from apps.accounts.models import User
from apps.common.models import AuditLog

from .models import SystemSettings

# Toggles auditables (campos de negocio del singleton).
_AUDITED_FIELDS = ("costing_nominal_enabled", "costing_effective_enabled")


def get_settings() -> SystemSettings:
    """Retorna el singleton de configuración, creándolo con los defaults si no existe."""
    settings, _ = SystemSettings.objects.get_or_create(lock=True)
    return settings


def update_settings(
    *, user: User, settings: SystemSettings, data: dict[str, Any]
) -> SystemSettings:
    """Aplica los toggles validados, persiste y audita cada cambio.

    El serializer ya garantizó que no quedan ambas bases desactivadas. Aquí se calcula el
    diff (valor anterior → nuevo) por campo, se persiste dentro de `transaction.atomic()`
    y se registra un `AuditLog` por toggle efectivamente modificado.
    """
    with transaction.atomic():
        changed_fields: list[str] = []
        audit_rows: list[AuditLog] = []
        for field in _AUDITED_FIELDS:
            if field not in data:
                continue
            old_value = getattr(settings, field)
            new_value = data[field]
            if old_value == new_value:
                continue
            setattr(settings, field, new_value)
            changed_fields.append(field)
            audit_rows.append(
                AuditLog(
                    user=user,
                    action="UPDATE",
                    entity="SystemSettings",
                    object_id=str(settings.pk),
                    field=field,
                    old_value=str(old_value),
                    new_value=str(new_value),
                )
            )
        if changed_fields:
            settings.save(update_fields=[*changed_fields, "updated_at"])
            AuditLog.objects.bulk_create(audit_rows)
    return settings
