"""Maestro de inventario (capability products, F5).

Tres catálogos: `UnitOfMeasure`, `Category` y `Product`. Son datos maestros SIN máquina
de estado → soft delete de la CLASE 2 (config.yaml): heredan `SoftDeleteModel`
(`deleted_at` + manager que filtra) y declaran un índice único PARCIAL sobre `name`
(WHERE deleted_at IS NULL), de modo que el nombre se reutiliza tras una baja lógica.

Los pesos y el factor de conversión se modelan con `DecimalField` (NUNCA `FloatField`).
Los códigos de enum van en español MAYÚSCULAS, consistentes con `directory.FichaStatus`
y `accounts.Role`. La unicidad de nombre y la baja bloqueada por dependencias las
gobierna el `service` (409); aquí solo se declaran la estructura y los constraints.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from django.db import models
from django.db.models import Q

from apps.common.models import SoftDeleteModel


class IntakeType(models.TextChoices):
    GAVETA = "GAVETA", "Gaveta"
    PESO = "PESO", "Peso"


class UnitOfMeasure(SoftDeleteModel):
    """Unidad de medida con factor de conversión a la base (libras = 1)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=64, help_text="Nombre de la unidad (p. ej. Libras).")
    symbol = models.CharField(max_length=16, help_text="Símbolo corto (p. ej. lb, kg).")
    conversion_factor = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        help_text="Libras equivalentes a 1 unidad (base = 1). No se aplica en F5.",
    )

    class Meta:
        db_table = "products_units_of_measure"
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                condition=Q(deleted_at__isnull=True),
                name="uniq_unit_name_alive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.symbol})"


class Category(SoftDeleteModel):
    """Categoría: caducidad, tipo de ingreso y estructura del rango de merma proporcional."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128, help_text="Nombre visible de la categoría.")
    shelf_life_days = models.PositiveIntegerField(
        default=7, help_text="Días de caducidad desde el ingreso."
    )
    intake_type = models.CharField(
        max_length=8,
        choices=IntakeType.choices,
        help_text="Cómo ingresa el producto al inventario: GAVETA o PESO.",
    )
    # Estructura del rango de merma proporcional. Los valores numéricos quedan pendientes
    # del cliente → nullable; la estructura no se bloquea. La aplicación/costeo vive en F13.
    merma_min = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Mínimo del rango de merma proporcional (lb). Nullable hasta definirse.",
    )
    merma_max = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Máximo del rango de merma proporcional (lb). Nullable hasta definirse.",
    )
    reference_qty = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("100"),
        help_text="Cantidad de referencia del rango de merma (lb).",
    )

    class Meta:
        db_table = "products_categories"
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                condition=Q(deleted_at__isnull=True),
                name="uniq_category_name_alive",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Product(SoftDeleteModel):
    """Producto: nombre único entre vivos, categoría y unidad de medida existentes."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128, help_text="Nombre visible del producto.")
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        help_text="Categoría a la que pertenece el producto.",
    )
    unit_of_measure = models.ForeignKey(
        UnitOfMeasure,
        on_delete=models.PROTECT,
        related_name="products",
        help_text="Unidad de medida del producto.",
    )

    class Meta:
        db_table = "products_products"
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                condition=Q(deleted_at__isnull=True),
                name="uniq_product_name_alive",
            ),
        ]

    def __str__(self) -> str:
        return self.name
