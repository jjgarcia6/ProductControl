"""Serializers de la configuración global (capability system-settings, F8).

Read/write separados. Los serializers son delgados: el de escritura valida FORMATO
(tipos booleanos) y la regla cruzada de FORMATO "no ambas bases en False" en `validate()`
(→ `non_field_errors`, 400); la persistencia y la auditoría las hace el `service`. El
centinela `lock` es interno y NUNCA se expone. Cada campo lleva `help_text` para el
OpenAPI y el Diccionario de Datos Vivo.

La validación cruzada aquí es sobre el ESTADO RESULTANTE del `PATCH` parcial: se combina
lo enviado con lo ya persistido en la instancia para no permitir que un parcial deje
ambas bases desactivadas.
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from .models import SystemSettings


class SystemSettingsReadSerializer(serializers.ModelSerializer[SystemSettings]):
    """Contrato de lectura del singleton; nunca expone `lock`."""

    class Meta:
        model = SystemSettings
        fields = [
            "costing_nominal_enabled",
            "costing_effective_enabled",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class SystemSettingsUpdateSerializer(serializers.ModelSerializer[SystemSettings]):
    """Entrada del `PATCH` parcial de los toggles; rechaza dejar ambas bases en False."""

    costing_nominal_enabled = serializers.BooleanField(
        required=False,
        help_text="Mostrar la base de costo nominal (peso de factura) en reportes/dashboards.",
    )
    costing_effective_enabled = serializers.BooleanField(
        required=False,
        help_text="Mostrar la base de costo efectivo (peso real) en reportes/dashboards.",
    )

    class Meta:
        model = SystemSettings
        fields = ["costing_nominal_enabled", "costing_effective_enabled"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Al menos una base MUST permanecer activa tras aplicar el parcial."""
        instance = self.instance
        nominal = attrs.get(
            "costing_nominal_enabled",
            getattr(instance, "costing_nominal_enabled", True),
        )
        effective = attrs.get(
            "costing_effective_enabled",
            getattr(instance, "costing_effective_enabled", True),
        )
        if not nominal and not effective:
            raise serializers.ValidationError(
                "Al menos una base de costeo (nominal o efectiva) MUST permanecer activa."
            )
        return attrs
