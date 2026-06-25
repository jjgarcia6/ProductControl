"""Serializers de términos de crédito (capability credit, F4).

Delgados: tipan el contrato (DecimalField para `credit_limit`, nunca FloatField) y
delegan las reglas de integridad (faceta↔rol, unicidad) al service. Cada campo lleva
`help_text` para el OpenAPI y el Diccionario de Datos Vivo.
"""

from __future__ import annotations

from rest_framework import serializers

from .models import CreditTerms


class CreditTermsReadSerializer(serializers.ModelSerializer[CreditTerms]):
    """Contrato de lectura de los términos de crédito."""

    class Meta:
        model = CreditTerms
        fields = [
            "id",
            "ficha",
            "facet",
            "credit_limit",
            "term_days",
            "notice_days",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class CreditTermsWriteSerializer(serializers.ModelSerializer[CreditTerms]):
    """Entrada de creación/edición de términos. La integridad faceta↔rol la valida el service."""

    credit_limit = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, help_text="Límite de crédito (≥0)."
    )

    class Meta:
        model = CreditTerms
        fields = ["ficha", "facet", "credit_limit", "term_days", "notice_days"]
        # La unicidad por (ficha, faceta) la resuelve el service y se emite como 409
        # (no como el 400 del UniqueTogetherValidator que DRF infiere del constraint).
        validators: list[object] = []
