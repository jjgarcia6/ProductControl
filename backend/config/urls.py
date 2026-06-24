"""URL configuration for config project.

El bootstrap solo expone admin y los endpoints de OpenAPI (drf-spectacular).
Las rutas de negocio (auth, directorio, kardex, etc.) viven en sus changes.
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # Auth (F1): el prefijo /auth coincide con el Path de la cookie de refresh.
    path("auth/", include("apps.accounts.urls")),
    # Access-control (F2): perfiles y asignación de perfil.
    path("authz/", include("apps.authz.urls")),
    # OpenAPI: el schema es la fuente de tipos del frontend.
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
