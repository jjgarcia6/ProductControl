"""Rutas de la importación masiva (F7), bajo el prefijo `/bulk-import` (montado en config/urls)."""

from django.urls import path

from .views import (
    FichaImportView,
    FichaTemplateView,
    ProductImportView,
    ProductTemplateView,
)

app_name = "bulk_import"

urlpatterns = [
    path("products", ProductImportView.as_view(), name="products-import"),
    path("products/template", ProductTemplateView.as_view(), name="products-template"),
    path("fichas", FichaImportView.as_view(), name="fichas-import"),
    path("fichas/template", FichaTemplateView.as_view(), name="fichas-template"),
]
