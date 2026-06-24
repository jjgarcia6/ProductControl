"""Seed reversible de los cuatro perfiles semilla del sistema (F2).

Replica el loop de `services.seed_system_profiles` usando el modelo histórico (práctica
estándar en data migrations); los datos viven una sola vez en `catalog.SYSTEM_PROFILES`.
"""

from __future__ import annotations

from django.db import migrations

from apps.authz.catalog import SYSTEM_PROFILES


def seed(apps, schema_editor) -> None:
    Profile = apps.get_model("authz", "Profile")
    for spec in SYSTEM_PROFILES.values():
        Profile.objects.get_or_create(
            name=spec["name"],
            defaults={
                "permissions": spec["permissions"],
                "auto_approval": spec["auto_approval"],
            },
        )


def unseed(apps, schema_editor) -> None:
    Profile = apps.get_model("authz", "Profile")
    names = [spec["name"] for spec in SYSTEM_PROFILES.values()]
    Profile.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("authz", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
