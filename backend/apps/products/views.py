"""Vistas delgadas del maestro de inventario (capability products, F5).

CRUD acotado de categorías, productos y unidades de medida. No hay máquina de estado: el
`DELETE` es baja lógica (soft delete clase 2) y se autoriza con la acción `update` del
módulo (el catálogo de F2 no expone `delete`, igual que directory). Cada view declara su
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
from apps.authz.catalog import ACTION_CREATE, ACTION_READ, ACTION_UPDATE, MODULE_PRODUCTS
from apps.authz.permissions import HasModulePermission

from . import services
from .models import Category, Product, UnitOfMeasure
from .serializers import (
    CategoryReadSerializer,
    CategoryWriteSerializer,
    ProductReadSerializer,
    ProductWriteSerializer,
    UnitOfMeasureReadSerializer,
    UnitOfMeasureWriteSerializer,
)

# --- Categoría ---------------------------------------------------------------


class CategoryListCreateView(APIView):
    """`GET /products/categories` (listado) y `POST /products/categories` (alta)."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    required_permissions = {
        "GET": (MODULE_PRODUCTS, ACTION_READ),
        "POST": (MODULE_PRODUCTS, ACTION_CREATE),
    }

    @extend_schema(responses={200: CategoryReadSerializer(many=True), 403: DetailSerializer})
    def get(self, request: Request) -> Response:
        categories = Category.objects.order_by("name")
        return Response(CategoryReadSerializer(categories, many=True).data, status=200)

    @extend_schema(
        request=CategoryWriteSerializer,
        responses={
            201: CategoryReadSerializer,
            400: DetailSerializer,
            403: DetailSerializer,
            409: DetailSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        serializer = CategoryWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = services.create_category(
            user=cast(User, request.user), data=serializer.validated_data
        )
        return Response(CategoryReadSerializer(category).data, status=201)


class CategoryDetailView(APIView):
    """`GET` (lectura), `PATCH` (edición) y `DELETE` (baja lógica) de una categoría."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    required_permissions = {
        "GET": (MODULE_PRODUCTS, ACTION_READ),
        "PATCH": (MODULE_PRODUCTS, ACTION_UPDATE),
        "DELETE": (MODULE_PRODUCTS, ACTION_UPDATE),
    }

    @extend_schema(
        responses={200: CategoryReadSerializer, 403: DetailSerializer, 404: DetailSerializer}
    )
    def get(self, request: Request, category_id: str) -> Response:
        category = get_object_or_404(Category, pk=category_id)
        return Response(CategoryReadSerializer(category).data, status=200)

    @extend_schema(
        request=CategoryWriteSerializer,
        responses={
            200: CategoryReadSerializer,
            400: DetailSerializer,
            403: DetailSerializer,
            404: DetailSerializer,
            409: DetailSerializer,
        },
    )
    def patch(self, request: Request, category_id: str) -> Response:
        category = get_object_or_404(Category, pk=category_id)
        serializer = CategoryWriteSerializer(instance=category, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = services.update_category(
            user=cast(User, request.user), category=category, data=serializer.validated_data
        )
        return Response(CategoryReadSerializer(updated).data, status=200)

    @extend_schema(
        responses={
            204: None,
            403: DetailSerializer,
            404: DetailSerializer,
            409: DetailSerializer,
        }
    )
    def delete(self, request: Request, category_id: str) -> Response:
        category = get_object_or_404(Category, pk=category_id)
        services.deactivate_category(user=cast(User, request.user), category=category)
        return Response(status=204)


# --- Producto ----------------------------------------------------------------


class ProductListCreateView(APIView):
    """`GET /products/products` (listado) y `POST /products/products` (alta)."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    required_permissions = {
        "GET": (MODULE_PRODUCTS, ACTION_READ),
        "POST": (MODULE_PRODUCTS, ACTION_CREATE),
    }

    @extend_schema(responses={200: ProductReadSerializer(many=True), 403: DetailSerializer})
    def get(self, request: Request) -> Response:
        products = Product.objects.select_related("category", "unit_of_measure").order_by("name")
        return Response(ProductReadSerializer(products, many=True).data, status=200)

    @extend_schema(
        request=ProductWriteSerializer,
        responses={
            201: ProductReadSerializer,
            400: DetailSerializer,
            403: DetailSerializer,
            409: DetailSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        serializer = ProductWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = services.create_product(
            user=cast(User, request.user), data=serializer.validated_data
        )
        return Response(ProductReadSerializer(product).data, status=201)


class ProductDetailView(APIView):
    """`GET` (lectura), `PATCH` (edición) y `DELETE` (baja lógica) de un producto."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    required_permissions = {
        "GET": (MODULE_PRODUCTS, ACTION_READ),
        "PATCH": (MODULE_PRODUCTS, ACTION_UPDATE),
        "DELETE": (MODULE_PRODUCTS, ACTION_UPDATE),
    }

    @extend_schema(
        responses={200: ProductReadSerializer, 403: DetailSerializer, 404: DetailSerializer}
    )
    def get(self, request: Request, product_id: str) -> Response:
        product = get_object_or_404(
            Product.objects.select_related("category", "unit_of_measure"), pk=product_id
        )
        return Response(ProductReadSerializer(product).data, status=200)

    @extend_schema(
        request=ProductWriteSerializer,
        responses={
            200: ProductReadSerializer,
            400: DetailSerializer,
            403: DetailSerializer,
            404: DetailSerializer,
            409: DetailSerializer,
        },
    )
    def patch(self, request: Request, product_id: str) -> Response:
        product = get_object_or_404(Product, pk=product_id)
        serializer = ProductWriteSerializer(instance=product, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = services.update_product(
            user=cast(User, request.user), product=product, data=serializer.validated_data
        )
        return Response(ProductReadSerializer(updated).data, status=200)

    @extend_schema(responses={204: None, 403: DetailSerializer, 404: DetailSerializer})
    def delete(self, request: Request, product_id: str) -> Response:
        product = get_object_or_404(Product, pk=product_id)
        services.deactivate_product(user=cast(User, request.user), product=product)
        return Response(status=204)


# --- Unidad de medida --------------------------------------------------------


class UnitListCreateView(APIView):
    """`GET /products/units` (listado) y `POST /products/units` (alta)."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    required_permissions = {
        "GET": (MODULE_PRODUCTS, ACTION_READ),
        "POST": (MODULE_PRODUCTS, ACTION_CREATE),
    }

    @extend_schema(responses={200: UnitOfMeasureReadSerializer(many=True), 403: DetailSerializer})
    def get(self, request: Request) -> Response:
        units = UnitOfMeasure.objects.order_by("name")
        return Response(UnitOfMeasureReadSerializer(units, many=True).data, status=200)

    @extend_schema(
        request=UnitOfMeasureWriteSerializer,
        responses={
            201: UnitOfMeasureReadSerializer,
            400: DetailSerializer,
            403: DetailSerializer,
            409: DetailSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        serializer = UnitOfMeasureWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        unit = services.create_unit(user=cast(User, request.user), data=serializer.validated_data)
        return Response(UnitOfMeasureReadSerializer(unit).data, status=201)


class UnitDetailView(APIView):
    """`GET` (lectura), `PATCH` (edición) y `DELETE` (baja lógica) de una unidad."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    required_permissions = {
        "GET": (MODULE_PRODUCTS, ACTION_READ),
        "PATCH": (MODULE_PRODUCTS, ACTION_UPDATE),
        "DELETE": (MODULE_PRODUCTS, ACTION_UPDATE),
    }

    @extend_schema(
        responses={200: UnitOfMeasureReadSerializer, 403: DetailSerializer, 404: DetailSerializer}
    )
    def get(self, request: Request, unit_id: str) -> Response:
        unit = get_object_or_404(UnitOfMeasure, pk=unit_id)
        return Response(UnitOfMeasureReadSerializer(unit).data, status=200)

    @extend_schema(
        request=UnitOfMeasureWriteSerializer,
        responses={
            200: UnitOfMeasureReadSerializer,
            400: DetailSerializer,
            403: DetailSerializer,
            404: DetailSerializer,
            409: DetailSerializer,
        },
    )
    def patch(self, request: Request, unit_id: str) -> Response:
        unit = get_object_or_404(UnitOfMeasure, pk=unit_id)
        serializer = UnitOfMeasureWriteSerializer(instance=unit, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = services.update_unit(
            user=cast(User, request.user), unit=unit, data=serializer.validated_data
        )
        return Response(UnitOfMeasureReadSerializer(updated).data, status=200)

    @extend_schema(
        responses={
            204: None,
            403: DetailSerializer,
            404: DetailSerializer,
            409: DetailSerializer,
        }
    )
    def delete(self, request: Request, unit_id: str) -> Response:
        unit = get_object_or_404(UnitOfMeasure, pk=unit_id)
        services.deactivate_unit(user=cast(User, request.user), unit=unit)
        return Response(status=204)
