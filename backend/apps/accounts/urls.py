"""Rutas de auth (F1), bajo el prefijo `/auth` (se monta en config/urls.py)."""

from django.urls import path

from .views import (
    ChangePasswordView,
    DeactivateUserView,
    LoginView,
    LogoutView,
    MeView,
    ReactivateUserView,
    RefreshView,
    ResetPasswordView,
    UserAdminDetailView,
    UserAdminListCreateView,
)

app_name = "accounts"

urlpatterns = [
    path("login", LoginView.as_view(), name="login"),
    path("refresh", RefreshView.as_view(), name="refresh"),
    path("logout", LogoutView.as_view(), name="logout"),
    path("me", MeView.as_view(), name="me"),
    path("change-password", ChangePasswordView.as_view(), name="change-password"),
    # Administración de usuarios (F3) — solo el Jefe (HasModulePermission).
    path("users", UserAdminListCreateView.as_view(), name="user-list"),
    path("users/<int:user_id>", UserAdminDetailView.as_view(), name="user-detail"),
    path("users/<int:user_id>/deactivate", DeactivateUserView.as_view(), name="user-deactivate"),
    path("users/<int:user_id>/reactivate", ReactivateUserView.as_view(), name="user-reactivate"),
    path(
        "users/<int:user_id>/reset-password",
        ResetPasswordView.as_view(),
        name="user-reset-password",
    ),
]
