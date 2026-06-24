"""Rutas de access-control (F2), bajo el prefijo `/authz` (se monta en config/urls.py)."""

from django.urls import path

from .views import AssignProfileView, ProfileDetailView, ProfileListCreateView

app_name = "authz"

urlpatterns = [
    path("profiles", ProfileListCreateView.as_view(), name="profile-list"),
    path("profiles/<uuid:profile_id>", ProfileDetailView.as_view(), name="profile-detail"),
    path("users/<int:user_id>/assign-profile", AssignProfileView.as_view(), name="assign-profile"),
]
