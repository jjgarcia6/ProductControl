"""Siembra reversible de la fila única de configuración (F8).

Crea el singleton (`lock=True`, ambos toggles `True`) de forma idempotente; el reverse
elimina la fila. `get_or_create` evita duplicar si la fila ya existe (p. ej. porque un
`get_settings()` la creó antes de correr esta migración).
"""

from __future__ import annotations

from django.db import migrations


def seed(apps, schema_editor) -> None:
    SystemSettings = apps.get_model("system_settings", "SystemSettings")
    SystemSettings.objects.get_or_create(
        lock=True,
        defaults={"costing_nominal_enabled": True, "costing_effective_enabled": True},
    )


def unseed(apps, schema_editor) -> None:
    SystemSettings = apps.get_model("system_settings", "SystemSettings")
    SystemSettings.objects.filter(lock=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("system_settings", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
