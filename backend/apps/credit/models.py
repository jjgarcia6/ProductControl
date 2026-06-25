"""Modelo de términos de crédito por faceta (capability credit, F4).

En F4 los términos de crédito son **solo datos**: límite, plazo y días de aviso por
faceta (CLIENTE o PROVEEDOR) de una ficha. El comportamiento de vencimiento, alerta y
bloqueo automático se define en `credit-control` (F21).

`CreditTerms` es dato dependiente de `Ficha`: sin máquina de estado ni soft delete
propio (se elimina/edita con su ficha). Hereda `TimeStampedModel`. A lo sumo un juego
de términos por (ficha, faceta).
"""

from __future__ import annotations

import uuid

from django.db import models

from apps.common.models import TimeStampedModel


class CreditFacet(models.TextChoices):
    CLIENTE = "CLIENTE", "Cliente"
    PROVEEDOR = "PROVEEDOR", "Proveedor"


class CreditTerms(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ficha = models.ForeignKey(
        "directory.Ficha",
        on_delete=models.CASCADE,
        related_name="credit_terms",
        help_text="Ficha a la que aplican los términos.",
    )
    facet = models.CharField(
        max_length=10,
        choices=CreditFacet.choices,
        help_text="Faceta a la que aplican los términos: CLIENTE o PROVEEDOR.",
    )
    credit_limit = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, help_text="Límite de crédito (≥0)."
    )
    term_days = models.PositiveIntegerField(default=0, help_text="Plazo de crédito en días (≥0).")
    notice_days = models.PositiveIntegerField(
        default=2, help_text="Días de aviso previo al vencimiento (≥0)."
    )

    class Meta:
        db_table = "credit_terms"
        constraints = [
            models.UniqueConstraint(fields=["ficha", "facet"], name="uq_credit_terms_ficha_facet"),
        ]

    def __str__(self) -> str:
        return f"{self.facet} · {self.ficha_id}"
