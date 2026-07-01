"""Vistas delgadas de la importación masiva (capability bulk-import, F7).

Un par de endpoints por entidad: `POST` (validar con `dry_run=true` o confirmar) y `GET
…/template` (descargar la plantilla). Reciben, delegan en `services` y traducen el
resultado a códigos HTTP. Protegidas por `HasModulePermission` con el módulo `bulk-import`
(solo acción `create`): un perfil sin ese módulo recibe 403; sin sesión, 401.

`dry_run=true` → 200 (con el reporte, aunque haya filas en error). Sin `dry_run` = commit:
201 si ninguna fila tiene error; 400 con el reporte si alguna fila es inválida.
"""

from __future__ import annotations

from typing import cast

from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.serializers import DetailSerializer
from apps.authz.catalog import ACTION_CREATE, MODULE_BULK_IMPORT
from apps.authz.permissions import HasModulePermission

from . import services
from .parsers import parse_file
from .serializers import ImportResultSerializer, ImportUploadSerializer


def _is_dry_run(request: Request) -> bool:
    return (request.query_params.get("dry_run", "") or "").lower() in ("true", "1", "yes")


class _BaseImportView(APIView):
    """Base de los endpoints de importación por entidad (`entity` la fija la subclase)."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    parser_classes = [MultiPartParser, FormParser]
    required_permissions = {"POST": (MODULE_BULK_IMPORT, ACTION_CREATE)}
    entity: str

    @extend_schema(
        request={"multipart/form-data": ImportUploadSerializer},
        parameters=[
            OpenApiParameter(
                name="dry_run",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="true = previsualizar sin persistir; ausente/false = confirmar.",
            )
        ],
        responses={
            200: ImportResultSerializer,
            201: ImportResultSerializer,
            400: ImportResultSerializer,
            401: DetailSerializer,
            403: DetailSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        uploaded = request.FILES.get("file")
        if uploaded is None:
            raise ValidationError({"file": ["Debe adjuntar un archivo en el campo 'file'."]})
        rows = parse_file(uploaded)

        if _is_dry_run(request):
            result = services.preview_import(self.entity, rows)
            return Response(ImportResultSerializer(result).data, status=200)

        result = services.commit_import(self.entity, rows, user=cast(User, request.user))
        status_code = 400 if result["has_errors"] else 201
        return Response(ImportResultSerializer(result).data, status=status_code)


class ProductImportView(_BaseImportView):
    """`POST /bulk-import/products` — importa productos (dry-run o commit)."""

    entity = services.ENTITY_PRODUCTS


class FichaImportView(_BaseImportView):
    """`POST /bulk-import/fichas` — importa fichas del Directorio (dry-run o commit)."""

    entity = services.ENTITY_FICHAS


class _BaseTemplateView(APIView):
    """Base de la descarga de plantilla CSV por entidad."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    required_permissions = {"GET": (MODULE_BULK_IMPORT, ACTION_CREATE)}
    entity: str

    @extend_schema(responses={200: OpenApiTypes.STR, 401: DetailSerializer, 403: DetailSerializer})
    def get(self, request: Request) -> HttpResponse:
        content = services.build_template_csv(self.entity)
        response = HttpResponse(content, content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{self.entity}_template.csv"'
        return response


class ProductTemplateView(_BaseTemplateView):
    """`GET /bulk-import/products/template` — plantilla CSV de productos."""

    entity = services.ENTITY_PRODUCTS


class FichaTemplateView(_BaseTemplateView):
    """`GET /bulk-import/fichas/template` — plantilla CSV de fichas."""

    entity = services.ENTITY_FICHAS
