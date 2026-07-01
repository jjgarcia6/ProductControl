"""Serializers del maestro de precios (capability pricing, F6).

Write/read separados por entidad. Los serializers son delgados: validan FORMATO
(tipos, choices de `type`, existencia de la FK `product`, `price >= 0`) y delegan la
persistencia y las reglas de negocio al `service`. La UNICIDAD de nombre y la unicidad
(lista, producto) NO se validan aquí (las gobierna el service con `Conflict` 409): por
eso `name` se declara explícito para NO heredar el `UniqueValidator` que DRF infiere del
`UniqueConstraint` parcial —igual que en F4/F5—, y el par (lista, producto) se resuelve
en el service, no con `UniqueTogetherValidator`. Cada campo lleva `help_text` para el
OpenAPI y el Diccionario de Datos Vivo.
"""

from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from apps.products.models import Product

from .models import PriceList, PriceListItem, PriceListType


class PriceListReadSerializer(serializers.ModelSerializer[PriceList]):
    """Contrato de lectura de una lista de precios."""

    class Meta:
        model = PriceList
        fields = ["id", "name", "type", "created_at", "updated_at"]
        read_only_fields = fields


class PriceListWriteSerializer(serializers.ModelSerializer[PriceList]):
    """Entrada de alta/edición de lista de precios."""

    name = serializers.CharField(
        max_length=120,
        help_text="Nombre de la lista (único entre vivas; la unicidad la da el service).",
    )
    type = serializers.ChoiceField(
        choices=PriceListType.choices, help_text="Naturaleza de la lista: NORMAL o DESCARTE."
    )

    class Meta:
        model = PriceList
        fields = ["name", "type"]


class PriceListItemReadSerializer(serializers.ModelSerializer[PriceListItem]):
    """Contrato de lectura de un ítem de precio; anida el nombre del producto."""

    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = PriceListItem
        fields = [
            "id",
            "price_list",
            "product",
            "product_name",
            "price",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class PriceListItemWriteSerializer(serializers.ModelSerializer[PriceListItem]):
    """Entrada de alta/edición de un ítem de precio. La FK inexistente se rechaza con 400."""

    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), help_text="Id de un producto existente."
    )
    price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0"),
        help_text="Precio de venta en USD (>= 0).",
    )

    class Meta:
        model = PriceListItem
        fields = ["product", "price"]
