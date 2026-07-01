"""Rutas del maestro de inventario (F5), bajo el prefijo `/products` (montado en config/urls)."""

from django.urls import path

from .views import (
    CategoryDetailView,
    CategoryListCreateView,
    ProductDetailView,
    ProductListCreateView,
    UnitDetailView,
    UnitListCreateView,
)

app_name = "products"

urlpatterns = [
    path("categories", CategoryListCreateView.as_view(), name="category-list"),
    path("categories/<uuid:category_id>", CategoryDetailView.as_view(), name="category-detail"),
    path("products", ProductListCreateView.as_view(), name="product-list"),
    path("products/<uuid:product_id>", ProductDetailView.as_view(), name="product-detail"),
    path("units", UnitListCreateView.as_view(), name="unit-list"),
    path("units/<uuid:unit_id>", UnitDetailView.as_view(), name="unit-detail"),
]
