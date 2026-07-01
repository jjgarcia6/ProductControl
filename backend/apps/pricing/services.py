"""Lógica de negocio del maestro de precios (capability pricing, F6).

Las views son delgadas y delegan aquí. Toda escritura va en `transaction.atomic()` y se
audita con `@audit`. Las reglas que dependen del estado de la BD —unicidad de nombre
entre listas vivas, unicidad (lista, producto) y baja bloqueada por fichas asignadas—
viven aquí y se emiten por el contrato de errores uniforme: `Conflict` (409). El formato
(choices, existencia de FK, `price >= 0`) ya lo validó el serializer; aquí se asume
`data` validado.

La unicidad se resuelve por service (no por `UniqueValidator`/`UniqueTogetherValidator`)
para respetar la clase 2: el nombre se reutiliza tras una baja (índice único PARCIAL
entre vivas), consistente con F4/F5.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction

from apps.accounts.models import User
from apps.common.audit import audit
from apps.common.exceptions import Conflict

from .models import PriceList, PriceListItem


def _ensure_unique_price_list_name(name: str, *, exclude_pk: Any = None) -> None:
    """El nombre MUST ser único entre las listas vivas (409 si choca)."""
    qs = PriceList.objects.filter(name=name)
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    if qs.exists():
        raise Conflict("Ya existe una lista de precios con este nombre.")


# --- Lista de precios --------------------------------------------------------


@audit(action="CREATE", entity="PriceList")
def create_price_list(*, user: User, data: dict[str, Any]) -> PriceList:
    """Crea una lista con nombre único entre las vivas (409 si choca)."""
    with transaction.atomic():
        _ensure_unique_price_list_name(data["name"])
        price_list = PriceList.objects.create(**data)
    return price_list


@audit(action="UPDATE", entity="PriceList")
def update_price_list(*, user: User, price_list: PriceList, data: dict[str, Any]) -> PriceList:
    """Edita una lista revalidando la unicidad de nombre (excluye su propio pk)."""
    with transaction.atomic():
        new_name = data.get("name", price_list.name)
        _ensure_unique_price_list_name(new_name, exclude_pk=price_list.pk)
        for field, value in data.items():
            setattr(price_list, field, value)
        price_list.save()
    return price_list


@audit(action="SOFT_DELETE", entity="PriceList")
def soft_delete_price_list(*, user: User, price_list: PriceList) -> PriceList:
    """Baja lógica de una lista (409 si tiene fichas asignadas)."""
    with transaction.atomic():
        if price_list.fichas.exists():
            raise Conflict("No se puede dar de baja: la lista está asignada a una o más fichas.")
        price_list.delete()
    return price_list


# --- Ítem de precio ----------------------------------------------------------


@audit(action="CREATE", entity="PriceListItem")
def set_price_list_item(
    *, user: User, price_list: PriceList, data: dict[str, Any]
) -> PriceListItem:
    """Agrega un producto con su precio a la lista (409 si ese par ya existe)."""
    with transaction.atomic():
        if PriceListItem.objects.filter(price_list=price_list, product=data["product"]).exists():
            raise Conflict("El producto ya tiene un precio en esta lista.")
        item = PriceListItem.objects.create(price_list=price_list, **data)
    return item


@audit(action="UPDATE", entity="PriceListItem")
def update_price_list_item(
    *, user: User, item: PriceListItem, data: dict[str, Any]
) -> PriceListItem:
    """Edita un ítem de precio revalidando la unicidad (lista, producto)."""
    with transaction.atomic():
        new_product = data.get("product", item.product)
        if (
            PriceListItem.objects.filter(price_list=item.price_list, product=new_product)
            .exclude(pk=item.pk)
            .exists()
        ):
            raise Conflict("El producto ya tiene un precio en esta lista.")
        for field, value in data.items():
            setattr(item, field, value)
        item.save()
    return item


@audit(action="DELETE", entity="PriceListItem")
def delete_price_list_item(*, user: User, item: PriceListItem) -> PriceListItem:
    """Quita un ítem de precio de la lista (borrado físico: no es catálogo clase 2)."""
    with transaction.atomic():
        item.delete()
    return item
