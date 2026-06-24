"""Permission classes de DRF que resuelven por el perfil del usuario (F2).

El view declara qué `(módulo, acción)` exige por método HTTP en `required_permissions`;
la clase delega la decisión en `services.resolve_permission`. Al denegar devuelve 403
con un mensaje genérico (no revela qué permiso faltó: contrato de errores + seguridad).
"""

from __future__ import annotations

from typing import cast

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from .models import Profile
from .services import resolve_permission


class HasModulePermission(BasePermission):
    """Autoriza según el perfil del usuario y el requisito (módulo, acción) del view."""

    message = "No tiene permiso para realizar esta acción."

    def has_permission(self, request: Request, view: APIView) -> bool:
        requirements: dict[str, tuple[str, str]] = getattr(view, "required_permissions", {})
        requirement = requirements.get(request.method or "")
        if requirement is None:
            return True  # método sin requisito explícito de módulo/acción
        module, action = requirement
        profile = cast(Profile | None, getattr(request.user, "profile", None))
        return resolve_permission(profile, module, action)
