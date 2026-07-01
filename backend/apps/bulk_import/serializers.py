"""Serializers de SALIDA de la importación masiva (capability bulk-import, F7).

No hay serializer de escritura propio: cada fila se valida instanciando el serializer de
dominio existente (`ProductWriteSerializer` de F5, `FichaWriteSerializer` de F4) — DRY. El
contrato nuevo es solo la FORMA del reporte por fila y el resumen de la operación, que el
frontend consume como tipos generados del OpenAPI. Cada campo lleva `help_text`.
"""

from __future__ import annotations

from rest_framework import serializers

from .constants import STATUS_ERROR, STATUS_SKIPPED, STATUS_VALID


class ImportUploadSerializer(serializers.Serializer[dict[str, object]]):
    """Cuerpo multipart de una importación: el archivo a procesar (documenta el OpenAPI)."""

    file = serializers.FileField(help_text="Archivo CSV o Excel (.xlsx) a importar.")


class RowReportSerializer(serializers.Serializer[dict[str, object]]):
    """Reporte de una fila del archivo tras validarla."""

    row_number = serializers.IntegerField(
        help_text="Número de fila en el archivo (la cabecera es la fila 1)."
    )
    status = serializers.ChoiceField(
        choices=[
            (STATUS_VALID, "Válida"),
            (STATUS_SKIPPED, "Omitida por duplicado"),
            (STATUS_ERROR, "Con error de validación"),
        ],
        help_text="Estado de la fila: valid | skipped | error.",
    )
    # `errors` sombrea la propiedad `Serializer.errors` (solo salida, nunca llamamos
    # is_valid sobre este serializer): se ignora el override estático.
    errors = serializers.DictField(  # type: ignore[assignment]
        child=serializers.ListField(child=serializers.CharField()),
        required=False,
        help_text="Errores por campo (contrato uniforme). Solo presente si status = error.",
    )


class ImportResultSerializer(serializers.Serializer[dict[str, object]]):
    """Resumen de una operación de importación (previsualización o commit)."""

    dry_run = serializers.BooleanField(
        help_text="True si fue previsualización (no persiste); False si fue commit."
    )
    inserted = serializers.IntegerField(help_text="Filas insertadas (0 en dry-run).")
    skipped = serializers.IntegerField(help_text="Filas omitidas por duplicado.")
    rows = RowReportSerializer(many=True, help_text="Reporte fila por fila.")
