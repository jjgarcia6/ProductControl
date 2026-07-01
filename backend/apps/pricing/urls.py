"""Rutas del maestro de precios (F6), bajo el prefijo `/pricing` (montado en config/urls)."""

from django.urls import path

from .views import (
    PriceListDetailView,
    PriceListItemDetailView,
    PriceListItemListCreateView,
    PriceListListCreateView,
)

app_name = "pricing"

urlpatterns = [
    path("price-lists", PriceListListCreateView.as_view(), name="price-list-list"),
    path(
        "price-lists/<uuid:price_list_id>",
        PriceListDetailView.as_view(),
        name="price-list-detail",
    ),
    path(
        "price-lists/<uuid:price_list_id>/items",
        PriceListItemListCreateView.as_view(),
        name="price-list-item-list",
    ),
    path(
        "price-list-items/<uuid:item_id>",
        PriceListItemDetailView.as_view(),
        name="price-list-item-detail",
    ),
]
