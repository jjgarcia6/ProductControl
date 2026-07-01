"""Vista delgada de la configuración global (capability system-settings, F8).

El recurso es un SINGLETON: la ruta no lleva `id`. `GET` recupera el singleton y `PATCH`
actualiza los toggles de forma parcial; ambos resuelven la instancia con
`services.get_settings()`. Cada método declara su requisito `(módulo, acción)` en
`required_permissions`; la autorización la resuelve `HasModulePermission` (F2) por perfil
(`read` para leer, `update` para editar). La lógica de negocio vive en `services`.
"""

from __future__ import annotations

from typing import cast

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.serializers import DetailSerializer
from apps.authz.catalog import ACTION_READ, ACTION_UPDATE, MODULE_SYSTEM_SETTINGS
from apps.authz.permissions import HasModulePermission

from . import services
from .serializers import SystemSettingsReadSerializer, SystemSettingsUpdateSerializer


class SystemSettingsView(APIView):
    """`GET /system-settings` (lectura) y `PATCH /system-settings` (edición) del singleton."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    required_permissions = {
        "GET": (MODULE_SYSTEM_SETTINGS, ACTION_READ),
        "PATCH": (MODULE_SYSTEM_SETTINGS, ACTION_UPDATE),
    }

    @extend_schema(
        responses={200: SystemSettingsReadSerializer, 401: DetailSerializer, 403: DetailSerializer}
    )
    def get(self, request: Request) -> Response:
        settings = services.get_settings()
        return Response(SystemSettingsReadSerializer(settings).data, status=200)

    @extend_schema(
        request=SystemSettingsUpdateSerializer,
        responses={
            200: SystemSettingsReadSerializer,
            400: DetailSerializer,
            401: DetailSerializer,
            403: DetailSerializer,
        },
    )
    def patch(self, request: Request) -> Response:
        settings = services.get_settings()
        serializer = SystemSettingsUpdateSerializer(
            instance=settings, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        updated = services.update_settings(
            user=cast(User, request.user),
            settings=settings,
            data=serializer.validated_data,
        )
        return Response(SystemSettingsReadSerializer(updated).data, status=200)
