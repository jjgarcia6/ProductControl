"""Lógica de negocio del maestro de inventario (capability products, F5).

Los ViewSets/views son delgados y delegan aquí. Toda escritura va en
`transaction.atomic()` y se audita con `@audit`. Las reglas que dependen del estado de
la BD —unicidad de nombre entre registros vivos y baja bloqueada por dependencias— viven
aquí y se emiten por el contrato de errores uniforme: `Conflict` (409). El formato
(choices, existencia de FK) ya lo validó el serializer; aquí se asume `data` validado.

La unicidad se resuelve por service (no por `UniqueValidator`) para respetar la clase 2:
el nombre se reutiliza tras una baja (el índice único es PARCIAL entre vivos).
"""

from __future__ import annotations

from typing import Any

from django.db import transaction

from apps.accounts.models import User
from apps.common.audit import audit
from apps.common.audit_rules import AuditAction
from apps.common.exceptions import Conflict

from .models import Category, Product, UnitOfMeasure


def _ensure_unique_category_name(name: str, *, exclude_pk: Any = None) -> None:
    qs = Category.objects.filter(name=name)
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    if qs.exists():
        raise Conflict("Ya existe una categoría con este nombre.")


def _ensure_unique_product_name(name: str, *, exclude_pk: Any = None) -> None:
    qs = Product.objects.filter(name=name)
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    if qs.exists():
        raise Conflict("Ya existe un producto con este nombre.")


def _ensure_unique_unit_name(name: str, *, exclude_pk: Any = None) -> None:
    qs = UnitOfMeasure.objects.filter(name=name)
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    if qs.exists():
        raise Conflict("Ya existe una unidad de medida con este nombre.")


# --- Categoría ---------------------------------------------------------------


@audit(action=AuditAction.CREATE, entity="Category")
def create_category(*, user: User, data: dict[str, Any]) -> Category:
    """Crea una categoría con nombre único entre las vivas (409 si choca)."""
    with transaction.atomic():
        _ensure_unique_category_name(data["name"])
        category = Category.objects.create(**data)
    return category


@audit(action=AuditAction.UPDATE, entity="Category")
def update_category(*, user: User, category: Category, data: dict[str, Any]) -> Category:
    """Edita una categoría revalidando la unicidad de nombre (excluye su propio pk)."""
    with transaction.atomic():
        new_name = data.get("name", category.name)
        _ensure_unique_category_name(new_name, exclude_pk=category.pk)
        for field, value in data.items():
            setattr(category, field, value)
        category.save()
    return category


@audit(action=AuditAction.SOFT_DELETE, entity="Category")
def deactivate_category(*, user: User, category: Category) -> Category:
    """Baja lógica de una categoría (409 si tiene productos vivos asociados)."""
    with transaction.atomic():
        if category.products.exists():
            raise Conflict("No se puede dar de baja: la categoría tiene productos asociados.")
        category.delete()
    return category


# --- Producto ----------------------------------------------------------------


@audit(action=AuditAction.CREATE, entity="Product")
def create_product(*, user: User, data: dict[str, Any]) -> Product:
    """Crea un producto con nombre único entre los vivos (409 si choca)."""
    with transaction.atomic():
        _ensure_unique_product_name(data["name"])
        product = Product.objects.create(**data)
    return product


@audit(action=AuditAction.UPDATE, entity="Product")
def update_product(*, user: User, product: Product, data: dict[str, Any]) -> Product:
    """Edita un producto revalidando la unicidad de nombre (excluye su propio pk)."""
    with transaction.atomic():
        new_name = data.get("name", product.name)
        _ensure_unique_product_name(new_name, exclude_pk=product.pk)
        for field, value in data.items():
            setattr(product, field, value)
        product.save()
    return product


@audit(action=AuditAction.SOFT_DELETE, entity="Product")
def deactivate_product(*, user: User, product: Product) -> Product:
    """Baja lógica de un producto."""
    with transaction.atomic():
        product.delete()
    return product


# --- Unidad de medida --------------------------------------------------------


@audit(action=AuditAction.CREATE, entity="UnitOfMeasure")
def create_unit(*, user: User, data: dict[str, Any]) -> UnitOfMeasure:
    """Crea una unidad de medida con nombre único entre las vivas (409 si choca)."""
    with transaction.atomic():
        _ensure_unique_unit_name(data["name"])
        unit = UnitOfMeasure.objects.create(**data)
    return unit


@audit(action=AuditAction.UPDATE, entity="UnitOfMeasure")
def update_unit(*, user: User, unit: UnitOfMeasure, data: dict[str, Any]) -> UnitOfMeasure:
    """Edita una unidad revalidando la unicidad de nombre (excluye su propio pk)."""
    with transaction.atomic():
        new_name = data.get("name", unit.name)
        _ensure_unique_unit_name(new_name, exclude_pk=unit.pk)
        for field, value in data.items():
            setattr(unit, field, value)
        unit.save()
    return unit


@audit(action=AuditAction.SOFT_DELETE, entity="UnitOfMeasure")
def deactivate_unit(*, user: User, unit: UnitOfMeasure) -> UnitOfMeasure:
    """Baja lógica de una unidad (409 si tiene productos vivos asociados)."""
    with transaction.atomic():
        if unit.products.exists():
            raise Conflict("No se puede dar de baja: la unidad tiene productos asociados.")
        unit.delete()
    return unit
