"""Test del parche de perfiles semilla de F8 (data migration de `authz`).

Verifica el comportamiento de las funciones `patch`/`unpatch` de la migración
`authz.0003_patch_system_settings_perms`: fusiona `system-settings` en los perfiles
semilla EXISTENTES sin pisar otros permisos (idempotente) y el reverse retira SOLO esa
clave. Se ejerce la lógica real de la migración importándola directamente (no hay helper
de migraciones en el proyecto).

Los perfiles `Jefe`/`Supervisor` ya existen (los sembró `authz.0002`); aquí se los
retrotrae a un estado PRE-F8 (sin `system-settings`) para observar el efecto del parche.
"""

import importlib

from django.apps import apps as global_apps

from apps.authz.models import Profile

migration = importlib.import_module("apps.authz.migrations.0003_patch_system_settings_perms")


def _run(fn):
    fn(global_apps, None)


def _reset_to_pre_f8(name: str, permissions: dict[str, list[str]]) -> Profile:
    """Deja el perfil semilla en su estado previo a F8 (sin `system-settings`)."""
    profile = Profile.objects.get(name=name)
    profile.permissions = permissions
    profile.save(update_fields=["permissions"])
    return profile


def test_parche_no_pisa_permisos_previos(db):
    jefe = _reset_to_pre_f8("Jefe", {"access-control": ["read", "create", "update"]})
    supervisor = _reset_to_pre_f8("Supervisor", {"access-control": ["read"]})

    _run(migration.patch)

    jefe.refresh_from_db()
    supervisor.refresh_from_db()
    # Gana system-settings conservando lo previo.
    assert jefe.permissions["system-settings"] == ["read", "update"]
    assert jefe.permissions["access-control"] == ["read", "create", "update"]
    assert supervisor.permissions["system-settings"] == ["read"]
    assert supervisor.permissions["access-control"] == ["read"]


def test_parche_es_idempotente(db):
    _reset_to_pre_f8("Jefe", {"access-control": ["read"]})

    _run(migration.patch)
    _run(migration.patch)  # segunda pasada no duplica acciones

    jefe = Profile.objects.get(name="Jefe")
    assert jefe.permissions["system-settings"] == ["read", "update"]


def test_reverse_retira_solo_system_settings(db):
    _reset_to_pre_f8("Jefe", {"access-control": ["read", "create", "update"]})
    _run(migration.patch)

    _run(migration.unpatch)

    jefe = Profile.objects.get(name="Jefe")
    assert "system-settings" not in jefe.permissions
    assert jefe.permissions["access-control"] == ["read", "create", "update"]
