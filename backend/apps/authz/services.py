"""Lógica de negocio de access-control (F2).

La decisión de autorización vive aquí (no en views ni serializers). Las funciones de
resolución son puras sobre el objeto perfil (sin consultas), testeables aisladas; la
asignación y el seed tocan la BD y van en `transaction.atomic()`.
"""

from __future__ import annotations

from django.db import transaction

from apps.accounts.models import User
from apps.common.audit import audit

from .catalog import SYSTEM_PROFILES
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


@audit(action="UPDATE", entity="User")
def assign_profile(*, user: User, target: User, profile: Profile) -> User:
    """Asigna `profile` a `target`. `user` es el actor (lo atribuye la auditoría)."""
    with transaction.atomic():
        target.profile = profile
        target.save(update_fields=["profile"])
    return target


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
