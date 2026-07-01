"""Vistas delgadas del maestro de precios (capability pricing, F6).

CRUD acotado de listas de precios y de sus ítems (precio por producto). No hay máquina
de estado: el `DELETE` de una lista es baja lógica (soft delete clase 2) y se autoriza
con la acción `update` del módulo (el catálogo de F2 no expone `delete`, igual que
products/directory); el `DELETE` de un ítem lo quita de la lista. Cada view declara su
requisito `(módulo, acción)` por método en `required_permissions`; la autorización la
resuelve `HasModulePermission` (F2) por perfil. La lógica vive en `services`.
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
from apps.authz.catalog import ACTION_CREATE, ACTION_READ, ACTION_UPDATE, MODULE_PRICING
from apps.authz.permissions import HasModulePermission

from . import services
from .models import PriceList, PriceListItem
from .serializers import (
    PriceListItemReadSerializer,
    PriceListItemWriteSerializer,
    PriceListReadSerializer,
    PriceListWriteSerializer,
)

# --- Lista de precios --------------------------------------------------------


class PriceListListCreateView(APIView):
    """`GET /pricing/price-lists` (listado) y `POST /pricing/price-lists` (alta)."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    required_permissions = {
        "GET": (MODULE_PRICING, ACTION_READ),
        "POST": (MODULE_PRICING, ACTION_CREATE),
    }

    @extend_schema(responses={200: PriceListReadSerializer(many=True), 403: DetailSerializer})
    def get(self, request: Request) -> Response:
        price_lists = PriceList.objects.order_by("name")
        return Response(PriceListReadSerializer(price_lists, many=True).data, status=200)

    @extend_schema(
        request=PriceListWriteSerializer,
        responses={
            201: PriceListReadSerializer,
            400: DetailSerializer,
            403: DetailSerializer,
            409: DetailSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        serializer = PriceListWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        price_list = services.create_price_list(
            user=cast(User, request.user), data=serializer.validated_data
        )
        return Response(PriceListReadSerializer(price_list).data, status=201)


class PriceListDetailView(APIView):
    """`GET` (lectura), `PATCH` (edición) y `DELETE` (baja lógica) de una lista."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    required_permissions = {
        "GET": (MODULE_PRICING, ACTION_READ),
        "PATCH": (MODULE_PRICING, ACTION_UPDATE),
        "DELETE": (MODULE_PRICING, ACTION_UPDATE),
    }

    @extend_schema(
        responses={200: PriceListReadSerializer, 403: DetailSerializer, 404: DetailSerializer}
    )
    def get(self, request: Request, price_list_id: str) -> Response:
        price_list = get_object_or_404(PriceList, pk=price_list_id)
        return Response(PriceListReadSerializer(price_list).data, status=200)

    @extend_schema(
        request=PriceListWriteSerializer,
        responses={
            200: PriceListReadSerializer,
            400: DetailSerializer,
            403: DetailSerializer,
            404: DetailSerializer,
            409: DetailSerializer,
        },
    )
    def patch(self, request: Request, price_list_id: str) -> Response:
        price_list = get_object_or_404(PriceList, pk=price_list_id)
        serializer = PriceListWriteSerializer(instance=price_list, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = services.update_price_list(
            user=cast(User, request.user),
            price_list=price_list,
            data=serializer.validated_data,
        )
        return Response(PriceListReadSerializer(updated).data, status=200)

    @extend_schema(
        responses={
            204: None,
            403: DetailSerializer,
            404: DetailSerializer,
            409: DetailSerializer,
        }
    )
    def delete(self, request: Request, price_list_id: str) -> Response:
        price_list = get_object_or_404(PriceList, pk=price_list_id)
        services.soft_delete_price_list(user=cast(User, request.user), price_list=price_list)
        return Response(status=204)


# --- Ítem de precio ----------------------------------------------------------


class PriceListItemListCreateView(APIView):
    """`GET /pricing/price-lists/{id}/items` (listado) y `POST` (agregar precio)."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    required_permissions = {
        "GET": (MODULE_PRICING, ACTION_READ),
        "POST": (MODULE_PRICING, ACTION_UPDATE),
    }

    @extend_schema(responses={200: PriceListItemReadSerializer(many=True), 403: DetailSerializer})
    def get(self, request: Request, price_list_id: str) -> Response:
        price_list = get_object_or_404(PriceList, pk=price_list_id)
        items = (
            PriceListItem.objects.select_related("product")
            .filter(price_list=price_list)
            .order_by("product__name")
        )
        return Response(PriceListItemReadSerializer(items, many=True).data, status=200)

    @extend_schema(
        request=PriceListItemWriteSerializer,
        responses={
            201: PriceListItemReadSerializer,
            400: DetailSerializer,
            403: DetailSerializer,
            404: DetailSerializer,
            409: DetailSerializer,
        },
    )
    def post(self, request: Request, price_list_id: str) -> Response:
        price_list = get_object_or_404(PriceList, pk=price_list_id)
        serializer = PriceListItemWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = services.set_price_list_item(
            user=cast(User, request.user),
            price_list=price_list,
            data=serializer.validated_data,
        )
        return Response(PriceListItemReadSerializer(item).data, status=201)


class PriceListItemDetailView(APIView):
    """`PATCH` (edición del precio) y `DELETE` (quitar de la lista) de un ítem."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    required_permissions = {
        "PATCH": (MODULE_PRICING, ACTION_UPDATE),
        "DELETE": (MODULE_PRICING, ACTION_UPDATE),
    }

    @extend_schema(
        request=PriceListItemWriteSerializer,
        responses={
            200: PriceListItemReadSerializer,
            400: DetailSerializer,
            403: DetailSerializer,
            404: DetailSerializer,
            409: DetailSerializer,
        },
    )
    def patch(self, request: Request, item_id: str) -> Response:
        item = get_object_or_404(PriceListItem.objects.select_related("product"), pk=item_id)
        serializer = PriceListItemWriteSerializer(instance=item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = services.update_price_list_item(
            user=cast(User, request.user), item=item, data=serializer.validated_data
        )
        return Response(PriceListItemReadSerializer(updated).data, status=200)

    @extend_schema(responses={204: None, 403: DetailSerializer, 404: DetailSerializer})
    def delete(self, request: Request, item_id: str) -> Response:
        item = get_object_or_404(PriceListItem, pk=item_id)
        services.delete_price_list_item(user=cast(User, request.user), item=item)
        return Response(status=204)
