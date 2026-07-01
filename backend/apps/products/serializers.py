"""Serializers del maestro de inventario (capability products, F5).

Write/read separados por entidad. Los serializers son delgados: validan FORMATO
(tipos, choices de `intake_type`, existencia de las FK) y delegan la persistencia y las
reglas de negocio al `service`. La UNICIDAD de nombre NO se valida aquí (la gobierna el
service con `Conflict` 409): por eso `name` se declara explícito para NO heredar el
`UniqueValidator` que DRF infiere del `UniqueConstraint` parcial —igual que en F4—, lo
que rechazaría con 400 nombres reutilizables tras una baja. Cada campo lleva `help_text`
para el OpenAPI y el Diccionario de Datos Vivo.
"""

from __future__ import annotations

from rest_framework import serializers

from .models import Category, IntakeType, Product, UnitOfMeasure


class UnitOfMeasureReadSerializer(serializers.ModelSerializer[UnitOfMeasure]):
    """Contrato de lectura de una unidad de medida."""

    class Meta:
        model = UnitOfMeasure
        fields = ["id", "name", "symbol", "conversion_factor", "created_at", "updated_at"]
        read_only_fields = fields


class UnitOfMeasureWriteSerializer(serializers.ModelSerializer[UnitOfMeasure]):
    """Entrada de alta/edición de unidad de medida."""

    name = serializers.CharField(
        max_length=64,
        help_text="Nombre de la unidad (único entre vivas; la unicidad la da el service).",
    )

    class Meta:
        model = UnitOfMeasure
        fields = ["name", "symbol", "conversion_factor"]


class CategoryReadSerializer(serializers.ModelSerializer[Category]):
    """Contrato de lectura de una categoría."""

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "shelf_life_days",
            "intake_type",
            "merma_min",
            "merma_max",
            "reference_qty",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class CategoryWriteSerializer(serializers.ModelSerializer[Category]):
    """Entrada de alta/edición de categoría. `merma_min`/`merma_max` opcionales (nullable)."""

    name = serializers.CharField(
        max_length=128,
        help_text="Nombre de la categoría (único entre vivas; la unicidad la da el service).",
    )
    intake_type = serializers.ChoiceField(
        choices=IntakeType.choices, help_text="Tipo de ingreso: GAVETA o PESO."
    )

    class Meta:
        model = Category
        fields = [
            "name",
            "shelf_life_days",
            "intake_type",
            "merma_min",
            "merma_max",
            "reference_qty",
        ]


class ProductReadSerializer(serializers.ModelSerializer[Product]):
    """Contrato de lectura de un producto; anida nombres de categoría y unidad."""

    category_name = serializers.CharField(source="category.name", read_only=True)
    unit_of_measure_name = serializers.CharField(source="unit_of_measure.name", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "category",
            "category_name",
            "unit_of_measure",
            "unit_of_measure_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ProductWriteSerializer(serializers.ModelSerializer[Product]):
    """Entrada de alta/edición de producto. Las FK inexistentes se rechazan con 400."""

    name = serializers.CharField(
        max_length=128,
        help_text="Nombre del producto (único entre vivos; la unicidad la da el service).",
    )
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), help_text="Id de una categoría existente."
    )
    unit_of_measure = serializers.PrimaryKeyRelatedField(
        queryset=UnitOfMeasure.objects.all(), help_text="Id de una unidad de medida existente."
    )

    class Meta:
        model = Product
        fields = ["name", "category", "unit_of_measure"]
