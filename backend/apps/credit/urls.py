"""Rutas de términos de crédito (F4), bajo el prefijo `/credit` (se monta en config/urls.py)."""

from django.urls import path

from .views import CreditTermsCreateView, CreditTermsDetailView

app_name = "credit"

urlpatterns = [
    path("terms", CreditTermsCreateView.as_view(), name="terms-create"),
    path("terms/<uuid:terms_id>", CreditTermsDetailView.as_view(), name="terms-detail"),
]
