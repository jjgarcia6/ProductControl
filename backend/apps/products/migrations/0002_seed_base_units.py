"""Data migration: siembra las unidades de medida base (F5).

`seed` deja disponibles libras (base, factor 1) y kilogramos (≈2.204623 lb) usando
`get_or_create` por nombre → idempotente (re-ejecutarla no duplica filas). `unseed`
(reverse) hace `hard_delete` SOLO de esas dos filas para no dejar el reverse en noop.
La conversión NO se aplica en F5: el factor se almacena para uso futuro.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import migrations

_BASE_UNITS = [
    {"name": "Libras", "symbol": "lb", "conversion_factor": Decimal("1")},
    {"name": "Kilogramos", "symbol": "kg", "conversion_factor": Decimal("2.204623")},
]


def seed_base_units(apps, schema_editor):
    UnitOfMeasure = apps.get_model("products", "UnitOfMeasure")
    for unit in _BASE_UNITS:
        UnitOfMeasure.objects.get_or_create(
            name=unit["name"],
            defaults={
                "symbol": unit["symbol"],
                "conversion_factor": unit["conversion_factor"],
            },
        )


def unseed_base_units(apps, schema_editor):
    UnitOfMeasure = apps.get_model("products", "UnitOfMeasure")
    UnitOfMeasure.objects.filter(name__in=[u["name"] for u in _BASE_UNITS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_base_units, unseed_base_units),
    ]
