"""Vistas delgadas del Directorio (capability directory, F4).

CRUD acotado de ficha + transiciones de estado como acciones explícitas (no PUT) +
vínculo con usuario. Cada view declara su requisito (módulo, acción) por método en
`required_permissions`; la autorización la resuelve `HasModulePermission` (F2) por
perfil. La lógica vive en `services`; aquí solo se recibe, valida y delega.
"""

from __future__ import annotations

from typing import cast

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.serializers import DetailSerializer
from apps.authz.catalog import (
    ACTION_CREATE,
    ACTION_READ,
    ACTION_UPDATE,
    MODULE_DIRECTORY,
)
from apps.authz.permissions import HasModulePermission

from . import services
from .models import Ficha, FichaStatus
from .serializers import (
    AssignPriceListSerializer,
    FichaReadSerializer,
    FichaWriteSerializer,
    LinkUserWriteSerializer,
)


def _filtered_fichas(params: dict[str, str]) -> list[Ficha]:
    """Aplica los filtros de listado: rol, estado y exclusión de INACTIVO por defecto."""
    qs = Ficha.objects.all()
    role = params.get("role")
    if role:
        qs = qs.filter(roles__contains=[role])
    status_filter = params.get("status")
    if status_filter:
        qs = qs.filter(status=status_filter)
    elif params.get("include_inactive", "").lower() not in {"1", "true", "yes"}:
        qs = qs.exclude(status=FichaStatus.INACTIVO)
    return list(qs.order_by("name"))


class FichaListCreateView(APIView):
    """`GET /directory/fichas` (listado con filtros) y `POST /directory/fichas` (alta)."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    required_permissions = {
        "GET": (MODULE_DIRECTORY, ACTION_READ),
        "POST": (MODULE_DIRECTORY, ACTION_CREATE),
    }

    @extend_schema(responses={200: FichaReadSerializer(many=True), 403: DetailSerializer})
    def get(self, request: Request) -> Response:
        fichas = _filtered_fichas(request.query_params)
        return Response(FichaReadSerializer(fichas, many=True).data, status=200)

    @extend_schema(
        request=FichaWriteSerializer,
        responses={
            201: FichaReadSerializer,
            400: DetailSerializer,
            403: DetailSerializer,
            409: DetailSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        serializer = FichaWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ficha = services.create_ficha(user=cast(User, request.user), data=serializer.validated_data)
        return Response(FichaReadSerializer(ficha).data, status=201)


class FichaDetailView(APIView):
    """`GET` (lectura) y `PATCH` (edición de datos no-estado) de una ficha por id."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    required_permissions = {
        "GET": (MODULE_DIRECTORY, ACTION_READ),
        "PATCH": (MODULE_DIRECTORY, ACTION_UPDATE),
    }

    @extend_schema(
        responses={200: FichaReadSerializer, 403: DetailSerializer, 404: DetailSerializer}
    )
    def get(self, request: Request, ficha_id: str) -> Response:
        ficha = get_object_or_404(Ficha, pk=ficha_id)
        return Response(FichaReadSerializer(ficha).data, status=200)

    @extend_schema(
        request=FichaWriteSerializer,
        responses={
            200: FichaReadSerializer,
            400: DetailSerializer,
            403: DetailSerializer,
            404: DetailSerializer,
            409: DetailSerializer,
        },
    )
    def patch(self, request: Request, ficha_id: str) -> Response:
        ficha = get_object_or_404(Ficha, pk=ficha_id)
        serializer = FichaWriteSerializer(instance=ficha, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = services.update_ficha(
            user=cast(User, request.user), ficha=ficha, data=serializer.validated_data
        )
        return Response(FichaReadSerializer(updated).data, status=200)


class FichaTransitionView(APIView):
    """Transición de estado de una ficha. La acción concreta llega por `as_view(action=...)`."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    required_permissions = {"POST": (MODULE_DIRECTORY, ACTION_UPDATE)}
    action: str = ""

    @extend_schema(
        request=None,
        responses={
            200: FichaReadSerializer,
            403: DetailSerializer,
            404: DetailSerializer,
            409: DetailSerializer,
        },
    )
    def post(self, request: Request, ficha_id: str) -> Response:
        ficha = get_object_or_404(Ficha, pk=ficha_id)
        updated = services.change_status(
            user=cast(User, request.user), ficha=ficha, action=self.action
        )
        return Response(FichaReadSerializer(updated).data, status=200)


class FichaLinkUserView(APIView):
    """`POST /directory/fichas/{id}/link-user` — vincula la ficha a un usuario (1:1)."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    required_permissions = {"POST": (MODULE_DIRECTORY, ACTION_UPDATE)}

    @extend_schema(
        request=LinkUserWriteSerializer,
        responses={
            200: FichaReadSerializer,
            400: DetailSerializer,
            403: DetailSerializer,
            404: DetailSerializer,
            409: DetailSerializer,
        },
    )
    def post(self, request: Request, ficha_id: str) -> Response:
        ficha = get_object_or_404(Ficha, pk=ficha_id)
        serializer = LinkUserWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target = get_object_or_404(User, pk=serializer.validated_data["user"])
        updated = services.link_user(user=cast(User, request.user), ficha=ficha, target=target)
        return Response(FichaReadSerializer(updated).data, status=200)


class FichaAssignPriceListView(APIView):
    """`PATCH /directory/fichas/{id}/assign-price-list` — asigna una lista de precios (F6)."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    required_permissions = {"PATCH": (MODULE_DIRECTORY, ACTION_UPDATE)}

    @extend_schema(
        request=AssignPriceListSerializer,
        responses={
            200: FichaReadSerializer,
            400: DetailSerializer,
            403: DetailSerializer,
            404: DetailSerializer,
        },
    )
    def patch(self, request: Request, ficha_id: str) -> Response:
        ficha = get_object_or_404(Ficha, pk=ficha_id)
        serializer = AssignPriceListSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = services.assign_price_list(
            user=cast(User, request.user),
            ficha=ficha,
            price_list=serializer.validated_data["price_list"],
        )
        return Response(FichaReadSerializer(updated).data, status=200)
