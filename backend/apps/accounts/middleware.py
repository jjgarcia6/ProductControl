"""Middleware de cambio de contraseña forzado (F3 user-management).

Mientras un usuario tenga `must_change_password` activo (tras un reset administrativo),
solo puede consultar su identidad, cambiar su contraseña o cerrar sesión; cualquier otra
operación responde 403 con `{detail}` del contrato de errores.

Se implementa como middleware (no como permission class por vista) para que el bloqueo sea
GLOBAL: las vistas declaran su propio `permission_classes`, que reemplazaría a cualquier
permiso por defecto de DRF. El middleware resuelve el usuario con la misma autenticación
JWT que DRF (Authorization: Bearer), por lo que no depende de la sesión de Django.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from django.http import HttpRequest, HttpResponse, JsonResponse
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError

# Rutas permitidas mientras el cambio está pendiente (identidad, cambio propio, logout).
EXEMPT_PATHS = frozenset({"/auth/me", "/auth/change-password", "/auth/logout"})

_BLOCKED_MESSAGE = "Debe cambiar su contraseña antes de continuar."


class ForcePasswordChangeMiddleware:
    """Bloquea toda operación distinta del cambio de contraseña si el flag está activo."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.path not in EXEMPT_PATHS and self._must_change_password(request):
            return JsonResponse({"detail": _BLOCKED_MESSAGE}, status=403)
        return self.get_response(request)

    def _must_change_password(self, request: HttpRequest) -> bool:
        """¿El portador del token tiene el cambio forzado pendiente? Sin token válido, no."""
        try:
            # JWTAuthentication lee la cabecera Authorization del HttpRequest (runtime ok);
            # el cast satisface el tipo Request esperado por la firma de DRF.
            result = JWTAuthentication().authenticate(cast(Request, cast(Any, request)))
        except (AuthenticationFailed, TokenError):
            return False
        if result is None:
            return False
        user, _ = result
        return bool(getattr(user, "must_change_password", False))
