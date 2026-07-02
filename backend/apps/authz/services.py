"""Lógica de negocio de access-control (F2).

La decisión de autorización vive aquí (no en views ni serializers). Las funciones de
resolución son puras sobre el objeto perfil (sin consultas), testeables aisladas; la
asignación y el seed tocan la BD y van en `transaction.atomic()`.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction

from apps.accounts.models import User
from apps.common.audit import audit
from apps.common.audit_rules import AuditAction
from apps.common.exceptions import Conflict

from .catalog import SYSTEM_PROFILES, role_for_profile_name
from .models import Profile


def resolve_permission(profile: Profile | None, module: str, action: str) -> bool:
    """¿El perfil permite `(módulo, acción)`? Sin perfil, no se permite nada."""
    if profile is None:
        return False
    permissions: dict[str, list[str]] = profile.permissions or {}
    return action in permissions.get(module, [])


def visible_fields_for(profile: Profile | None) -> set[str]:
    """Conjunto de claves de campos sensibles ('recurso.campo') que el perfil puede ver."""
    if profile is None:
        return set()
    return set(profile.visible_sensitive_fields or [])


@audit(action=AuditAction.UPDATE, entity="User")
def assign_profile(*, user: User, target: User, profile: Profile) -> User:
    """Asigna `profile` a `target`, sincroniza el `role` nominal e invalida las sesiones.

    F3 extiende la asignación de F2: además de fijar el perfil, sincroniza el `role` con el
    perfil semilla (los perfiles a medida no lo tocan) y blacklistea los refresh vigentes
    para que los permisos nuevos surtan efecto sin esperar a la expiración del token.
    `user` es el actor (lo atribuye la auditoría).
    """
    # Import local: rompe cualquier ciclo de carga accounts.services <-> authz.services.
    from apps.accounts.services import revoke_all_refresh

    with transaction.atomic():
        target.profile = profile
        fields = ["profile"]
        role = role_for_profile_name(profile.name)
        if role is not None:
            target.role = role
            fields.append("role")
        target.save(update_fields=fields)
        revoke_all_refresh(target)
    return target


@audit(action=AuditAction.UPDATE, entity="Profile")
def update_profile_permissions(*, user: User, profile: Profile, data: dict[str, Any]) -> Profile:
    """Aplica los cambios validados de un perfil (permisos, campos visibles, descripción, flags)."""
    with transaction.atomic():
        for field, value in data.items():
            setattr(profile, field, value)
        profile.save()
    return profile


@audit(action=AuditAction.SOFT_DELETE, entity="Profile")
def deactivate_profile(*, user: User, profile: Profile) -> Profile:
    """Da de baja (soft delete clase 2) un perfil sin usuarios asignados.

    Un perfil con al menos un usuario asignado MUST NOT poder darse de baja: 409 Conflict.
    """
    if profile.users.exists():
        raise Conflict(
            "No se puede dar de baja un perfil con usuarios asignados. "
            "Reasigne esos usuarios a otro perfil primero."
        )
    with transaction.atomic():
        profile.delete()  # soft delete: marca deleted_at, no elimina la fila
    return profile


def seed_system_profiles() -> None:
    """Crea idempotentemente los perfiles semilla del sistema (uno por rol)."""
    with transaction.atomic():
        for spec in SYSTEM_PROFILES.values():
            Profile.objects.get_or_create(
                name=spec["name"],
                defaults={
                    "permissions": spec["permissions"],
                    "auto_approval": spec["auto_approval"],
                },
            )
