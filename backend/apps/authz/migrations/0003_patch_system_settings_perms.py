"""Parche idempotente: añade `system-settings` a los perfiles semilla ya sembrados (F8).

`seed_system_profiles` usa `get_or_create(defaults=...)`, que NO actualiza perfiles ya
creados. En entornos F1–F7 ya migrados, `JEFE`/`SUPERVISOR` existen sin el módulo
`system-settings`; sin este parche el Jefe no podría editar la configuración. La
migración fusiona la clave `system-settings` en `permissions` sin pisar otros permisos;
el reverse retira SOLO esa clave. Ambas direcciones son idempotentes.
"""

from __future__ import annotations

from django.db import migrations

from apps.authz.catalog import (
    ACTION_READ,
    ACTION_UPDATE,
    MODULE_SYSTEM_SETTINGS,
)

# Acciones a garantizar por perfil semilla.
_PATCH: dict[str, list[str]] = {
    "Jefe": [ACTION_READ, ACTION_UPDATE],
    "Supervisor": [ACTION_READ],
}


def patch(apps, schema_editor) -> None:
    Profile = apps.get_model("authz", "Profile")
    for name, actions in _PATCH.items():
        profile = Profile.objects.filter(name=name).first()
        if profile is None:
            continue
        permissions = dict(profile.permissions or {})
        existing = list(permissions.get(MODULE_SYSTEM_SETTINGS, []))
        merged = existing + [a for a in actions if a not in existing]
        if merged != existing:
            permissions[MODULE_SYSTEM_SETTINGS] = merged
            profile.permissions = permissions
            profile.save(update_fields=["permissions", "updated_at"])


def unpatch(apps, schema_editor) -> None:
    Profile = apps.get_model("authz", "Profile")
    for name in _PATCH:
        profile = Profile.objects.filter(name=name).first()
        if profile is None:
            continue
        permissions = dict(profile.permissions or {})
        if MODULE_SYSTEM_SETTINGS in permissions:
            del permissions[MODULE_SYSTEM_SETTINGS]
            profile.permissions = permissions
            profile.save(update_fields=["permissions", "updated_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("authz", "0002_seed_system_profiles"),
    ]

    operations = [
        migrations.RunPython(patch, unpatch),
    ]
