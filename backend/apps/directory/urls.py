"""Rutas del Directorio (F4), bajo el prefijo `/directory` (se monta en config/urls.py)."""

from django.urls import path

from .views import (
    FichaAssignPriceListView,
    FichaDetailView,
    FichaLinkUserView,
    FichaListCreateView,
    FichaTransitionView,
)

app_name = "directory"

urlpatterns = [
    path("fichas", FichaListCreateView.as_view(), name="ficha-list"),
    path("fichas/<uuid:ficha_id>", FichaDetailView.as_view(), name="ficha-detail"),
    path(
        "fichas/<uuid:ficha_id>/block",
        FichaTransitionView.as_view(action="block"),
        name="ficha-block",
    ),
    path(
        "fichas/<uuid:ficha_id>/unblock",
        FichaTransitionView.as_view(action="unblock"),
        name="ficha-unblock",
    ),
    path(
        "fichas/<uuid:ficha_id>/deactivate",
        FichaTransitionView.as_view(action="deactivate"),
        name="ficha-deactivate",
    ),
    path(
        "fichas/<uuid:ficha_id>/reactivate",
        FichaTransitionView.as_view(action="reactivate"),
        name="ficha-reactivate",
    ),
    path(
        "fichas/<uuid:ficha_id>/link-user",
        FichaLinkUserView.as_view(),
        name="ficha-link-user",
    ),
    path(
        "fichas/<uuid:ficha_id>/assign-price-list",
        FichaAssignPriceListView.as_view(),
        name="ficha-assign-price-list",
    ),
]
