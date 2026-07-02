"""Período contable mensual (capability period, F9).

`Period` representa un mes contable identificado por `(year, month)` con estado
`OPEN`/`CLOSED`. Es el ancla del invariante de negocio "período cerrado": antes de crear
o modificar CUALQUIER documento, las capas de service de las fases consumidoras (F11+)
validan la fecha con `assert_date_operable` (ver `services.py`).

Semántica implícita-abierta: la ausencia de una fila para un `(year, month)` significa
que el mes está abierto; SOLO una fila `CLOSED` explícita bloquea la escritura. Por eso
NO hay data migration de seed.

Soft delete CLASE 1 (config.yaml): `Period` es una entidad con máquina de estado; NO se
borra ni hereda `SoftDeleteModel`. Su ciclo de vida se gobierna por transición de
`status` (el proceso de cierre/reversión llega en F25). Hereda SOLO `TimeStampedModel`.
"""

from __future__ import annotations

from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


class Period(TimeStampedModel):
    """Mes contable con estado abierto/cerrado; único por `(year, month)`."""

    class Status(models.TextChoices):
        OPEN = "OPEN", "Abierto"
        CLOSED = "CLOSED", "Cerrado"

    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField(
        help_text="Mes contable 1–12 (validado por CheckConstraint)."
    )
    status = models.CharField(
        max_length=6,
        choices=Status.choices,
        default=Status.OPEN,
        help_text="OPEN permite escrituras; CLOSED las bloquea.",
    )

    class Meta:
        db_table = "period"
        verbose_name = "period"
        verbose_name_plural = "periods"
        ordering = ["-year", "-month"]
        constraints = [
            models.UniqueConstraint(fields=["year", "month"], name="period_unique_year_month"),
            models.CheckConstraint(
                condition=Q(month__gte=1) & Q(month__lte=12),
                name="period_month_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.year}-{self.month:02d} ({self.status})"
