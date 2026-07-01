"""Ruta de la configuración global (F8), bajo el prefijo `/system-settings`.

Singleton: una sola ruta sin `id`, montada en la raíz del prefijo (ver config/urls).
"""

from django.urls import path

from .views import SystemSettingsView

app_name = "system_settings"

urlpatterns = [
    path("", SystemSettingsView.as_view(), name="system-settings"),
]
