"""Backfill: asigna a cada usuario existente su perfil semilla homónimo (F2).

Garantiza que tras migrar todo usuario tenga exactamente un perfil. Depende de que los
perfiles semilla ya existan (authz.0002). Reversible: el reverse desvincula el perfil.
"""

from __future__ import annotations

from django.db import migrations

from apps.authz.catalog import SYSTEM_PROFILES


def backfill(apps, schema_editor) -> None:
    User = apps.get_model("accounts", "User")
    Profile = apps.get_model("authz", "Profile")
    by_name = {p.name: p for p in Profile.objects.all()}
    for user in User.objects.filter(profile__isnull=True):
        spec = SYSTEM_PROFILES.get(user.role)
        if spec is None:
            continue
        profile = by_name.get(spec["name"])
        if profile is not None:
            user.profile = profile
            user.save(update_fields=["profile"])


def unbackfill(apps, schema_editor) -> None:
    User = apps.get_model("accounts", "User")
    User.objects.update(profile=None)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_user_profile"),
        ("authz", "0002_seed_system_profiles"),
    ]

    operations = [
        migrations.RunPython(backfill, unbackfill),
    ]
