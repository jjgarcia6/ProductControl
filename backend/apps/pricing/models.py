"""Maestro de precios (capability pricing, F6).

Dos entidades: `PriceList` (lista de precios) y `PriceListItem` (precio de un producto
dentro de una lista). Son datos maestros SIN máquina de estado → soft delete de la
CLASE 2 (config.yaml): `PriceList` hereda `SoftDeleteModel` (`deleted_at` + manager que
filtra) y declara un índice único PARCIAL sobre `name` (WHERE deleted_at IS NULL), de
modo que el nombre se reutiliza tras una baja lógica.

El precio se modela con `DecimalField` (NUNCA `FloatField`). Los códigos de enum van en
español MAYÚSCULAS, consistentes con `products.IntakeType` y `directory.FichaStatus`. La
unicidad de nombre, la unicidad (lista, producto) y la baja bloqueada por uso las
gobierna el `service` (409); aquí solo se declaran la estructura y los constraints.

En F6 `type` es solo un atributo: su efecto en la venta de descarte y la inmutabilidad
del precio en la entrega (snapshot al pasar a GENERADO) se implementan en F16.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from apps.common.models import SoftDeleteModel, TimeStampedModel


class PriceListType(models.TextChoices):
    NORMAL = "NORMAL", "Normal"
    DESCARTE = "DESCARTE", "Descarte"


class PriceList(SoftDeleteModel):
    """Lista de precios: nombre único entre vivas y tipo (NORMAL/DESCARTE)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120, help_text="Nombre visible de la lista.")
    type = models.CharField(
        max_length=8,
        choices=PriceListType.choices,
        help_text="Naturaleza de la lista: NORMAL o DESCARTE.",
    )

    class Meta:
        db_table = "price_lists"
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                condition=Q(deleted_at__isnull=True),
                name="uq_price_list_name_alive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.type})"


class PriceListItem(TimeStampedModel):
    """Precio de un producto dentro de una lista: a lo sumo uno por (lista, producto)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    price_list = models.ForeignKey(
        PriceList,
        on_delete=models.CASCADE,
        related_name="items",
        help_text="Lista a la que pertenece el precio.",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Producto tarifado.",
    )
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Precio de venta en USD (>= 0).",
    )

    class Meta:
        db_table = "price_list_items"
        constraints = [
            models.UniqueConstraint(
                fields=["price_list", "product"],
                name="uq_price_list_product",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product_id} @ {self.price}"
