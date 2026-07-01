"""Serializers del Directorio (capability directory, F4).

Los serializers son delgados: validan FORMATO (tipos, roles ≥1, dígito verificador de
la identificación según el tipo) y delegan la persistencia y las reglas de negocio al
service. El dígito verificador se valida server-side con `apps.common.validations`
(funciones puras); el error se mapea al campo `identification_number`. Cada campo lleva
`help_text` para el OpenAPI y el Diccionario de Datos Vivo.
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.common.validations import is_valid_identification
from apps.pricing.models import PriceList

from .models import Ficha, FichaRole


class FichaReadSerializer(serializers.ModelSerializer[Ficha]):
    """Contrato de lectura de una ficha."""

    class Meta:
        model = Ficha
        fields = [
            "id",
            "name",
            "identification_type",
            "identification_number",
            "email",
            "phone",
            "roles",
            "status",
            "user",
            "price_list",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class FichaWriteSerializer(serializers.ModelSerializer[Ficha]):
    """Entrada de alta/edición de ficha. NO acepta `status` ni `user` (cambian por acciones)."""

    roles = serializers.ListField(
        child=serializers.ChoiceField(choices=FichaRole.choices),
        allow_empty=False,
        help_text="Roles del tercero: ≥1 de CLIENTE/PROVEEDOR/RESPONSABLE_RUTA/CHOFER.",
    )
    # Declarado explícito para NO heredar el UniqueValidator que DRF infiere del
    # UniqueConstraint parcial: la unicidad (solo entre fichas no inactivas) la resuelve
    # el service y se emite como 409, no como un 400 que rechazaría números reutilizables.
    identification_number = serializers.CharField(
        max_length=20,
        help_text="Número validado por dígito verificador (pasaporte sin checksum).",
    )

    class Meta:
        model = Ficha
        fields = [
            "name",
            "identification_type",
            "identification_number",
            "email",
            "phone",
            "roles",
        ]

    def validate_roles(self, value: list[str]) -> list[str]:
        # Sin duplicados; ≥1 ya lo garantiza allow_empty=False.
        if len(set(value)) != len(value):
            raise serializers.ValidationError("Los roles no pueden repetirse.")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        # El tipo/número pueden venir parciales en PATCH: se completan con la instancia.
        id_type = attrs.get(
            "identification_type", getattr(self.instance, "identification_type", None)
        )
        number = attrs.get(
            "identification_number", getattr(self.instance, "identification_number", None)
        )
        if id_type is not None and number is not None:
            if not is_valid_identification(id_type, number):
                raise serializers.ValidationError(
                    {"identification_number": [f"El número no es válido para el tipo {id_type}."]}
                )
        return attrs


class LinkUserWriteSerializer(serializers.Serializer[dict[str, Any]]):
    """Entrada de la acción link-user: el usuario a vincular (1:1)."""

    user = serializers.IntegerField(help_text="Id del usuario del sistema a vincular con la ficha.")


class AssignPriceListSerializer(serializers.Serializer[dict[str, Any]]):
    """Entrada de la acción assign-price-list: la lista a asignar (F6).

    Acepta `null` para desasignar. La integridad asignación↔rol cliente la valida el
    service (400 si la ficha no tiene rol CLIENTE); aquí solo se valida el formato y la
    existencia de la lista (FK inexistente -> 400).
    """

    price_list = serializers.PrimaryKeyRelatedField(
        queryset=PriceList.objects.all(),
        allow_null=True,
        help_text="Id de una lista de precios existente, o null para desasignar.",
    )
