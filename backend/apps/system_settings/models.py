"""Parámetros globales del sistema (capability system-settings, F8).

Una ÚNICA fila de configuración global (singleton) con los dos toggles de costeo. El
singleton se garantiza a nivel de base de datos: el campo centinela `lock` es `unique`
y un `CheckConstraint` lo fija en `True`, de modo que es imposible crear una segunda
fila ni por el ORM ni por SQL directo.

Los toggles son un FILTRO DE PRESENTACIÓN, no de cálculo: ambas bases de costeo (nominal
y efectiva) se siguen calculando y persistiendo SIEMPRE en paralelo (invariante de doble
costeo); el flag solo decide qué base muestran reportes y dashboards. El sub-invariante
"al menos una base activa" lo gobierna el service (no se pueden desactivar ambas).

Excepción explícita a la política de soft delete (3 clases): un singleton de
configuración no es catálogo (clase 2), ni documento con estado (clase 1), ni ficha
(clase 3). No se borra nunca; hereda SOLO `TimeStampedModel`.
"""

from __future__ import annotations

from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


class SystemSettings(TimeStampedModel):
    """Configuración global: fila única con los toggles de costeo."""

    costing_nominal_enabled = models.BooleanField(
        default=True,
        help_text="Si los reportes/dashboards muestran la base de costo nominal (peso de factura).",
    )
    costing_effective_enabled = models.BooleanField(
        default=True,
        help_text="Si los reportes/dashboards muestran la base de costo efectivo (peso real).",
    )
    lock = models.BooleanField(
        default=True,
        unique=True,
        editable=False,
        help_text="Centinela interno del singleton; siempre True. No se expone en la API.",
    )

    class Meta:
        db_table = "system_settings"
        verbose_name = "system settings"
        verbose_name_plural = "system settings"
        constraints = [
            models.CheckConstraint(
                condition=Q(lock=True),
                name="system_settings_singleton_lock",
            ),
        ]

    def __str__(self) -> str:
        return "SystemSettings (singleton)"
