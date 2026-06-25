"""Vistas delgadas de términos de crédito (capability credit, F4).

Crear/editar términos por faceta. La autorización REUTILIZA el módulo `directory` (F4):
gestionar condiciones comerciales es parte de la administración del Directorio. La
lógica (integridad faceta↔rol, unicidad) vive en `services`.
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
from apps.authz.catalog import ACTION_CREATE, ACTION_UPDATE, MODULE_DIRECTORY
from apps.authz.permissions import HasModulePermission

from . import services
from .models import CreditTerms
from .serializers import CreditTermsReadSerializer, CreditTermsWriteSerializer


class CreditTermsCreateView(APIView):
    """`POST /credit/terms` — crea términos de crédito para una (ficha, faceta)."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    required_permissions = {"POST": (MODULE_DIRECTORY, ACTION_CREATE)}

    @extend_schema(
        request=CreditTermsWriteSerializer,
        responses={
            201: CreditTermsReadSerializer,
            400: DetailSerializer,
            403: DetailSerializer,
            409: DetailSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        serializer = CreditTermsWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        terms = services.create_terms(user=cast(User, request.user), data=serializer.validated_data)
        return Response(CreditTermsReadSerializer(terms).data, status=201)


class CreditTermsDetailView(APIView):
    """`PATCH /credit/terms/{id}` — edita términos de crédito existentes."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    required_permissions = {"PATCH": (MODULE_DIRECTORY, ACTION_UPDATE)}

    @extend_schema(
        request=CreditTermsWriteSerializer,
        responses={
            200: CreditTermsReadSerializer,
            400: DetailSerializer,
            403: DetailSerializer,
            404: DetailSerializer,
            409: DetailSerializer,
        },
    )
    def patch(self, request: Request, terms_id: str) -> Response:
        terms = get_object_or_404(CreditTerms, pk=terms_id)
        serializer = CreditTermsWriteSerializer(instance=terms, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = services.update_terms(
            user=cast(User, request.user), terms=terms, data=serializer.validated_data
        )
        return Response(CreditTermsReadSerializer(updated).data, status=200)
