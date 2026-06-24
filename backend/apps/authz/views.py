"""Vistas delgadas de access-control (F2).

Lectura de perfiles y asignación perfil↔usuario. La administración completa (editar/
baja desde UI) es F3. Cada view declara su requisito (módulo, acción) por método en
`required_permissions`; la autorización la resuelve `HasModulePermission` por perfil.
La lógica vive en `services`.
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
from apps.accounts.serializers import DetailSerializer, UserIdentitySerializer

from . import services
from .catalog import ACTION_CREATE, ACTION_READ, ACTION_UPDATE, MODULE_ACCESS_CONTROL
from .models import Profile
from .permissions import HasModulePermission
from .serializers import (
    AssignProfileSerializer,
    ProfileAdminWriteSerializer,
    ProfileReadSerializer,
    ProfileWriteSerializer,
)


class ProfileListCreateView(APIView):
    """`GET /authz/profiles` (lectura) y `POST /authz/profiles` (creación)."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    required_permissions = {
        "GET": (MODULE_ACCESS_CONTROL, ACTION_READ),
        "POST": (MODULE_ACCESS_CONTROL, ACTION_CREATE),
    }

    @extend_schema(responses={200: ProfileReadSerializer(many=True), 403: DetailSerializer})
    def get(self, request: Request) -> Response:
        profiles = Profile.objects.all()
        return Response(ProfileReadSerializer(profiles, many=True).data, status=200)

    @extend_schema(
        request=ProfileWriteSerializer,
        responses={201: ProfileReadSerializer, 400: DetailSerializer, 403: DetailSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = ProfileWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        return Response(ProfileReadSerializer(profile).data, status=201)


class ProfileDetailView(APIView):
    """`GET` (lectura), `PATCH` (editar permisos) y `DELETE` (baja) de un perfil por id.

    La edición y la baja (F3) completan la administración que F2 dejó en modelo + seed.
    """

    permission_classes = [IsAuthenticated, HasModulePermission]
    required_permissions = {
        "GET": (MODULE_ACCESS_CONTROL, ACTION_READ),
        "PATCH": (MODULE_ACCESS_CONTROL, ACTION_UPDATE),
        "DELETE": (MODULE_ACCESS_CONTROL, ACTION_UPDATE),
    }

    @extend_schema(
        responses={200: ProfileReadSerializer, 403: DetailSerializer, 404: DetailSerializer}
    )
    def get(self, request: Request, profile_id: str) -> Response:
        profile = get_object_or_404(Profile, pk=profile_id)
        return Response(ProfileReadSerializer(profile).data, status=200)

    @extend_schema(
        request=ProfileAdminWriteSerializer,
        responses={
            200: ProfileReadSerializer,
            400: DetailSerializer,
            403: DetailSerializer,
            404: DetailSerializer,
        },
    )
    def patch(self, request: Request, profile_id: str) -> Response:
        profile = get_object_or_404(Profile, pk=profile_id)
        serializer = ProfileAdminWriteSerializer(instance=profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = services.update_profile_permissions(
            user=cast(User, request.user),
            profile=profile,
            data=serializer.validated_data,
        )
        return Response(ProfileReadSerializer(updated).data, status=200)

    @extend_schema(
        request=None,
        responses={204: None, 403: DetailSerializer, 404: DetailSerializer, 409: DetailSerializer},
    )
    def delete(self, request: Request, profile_id: str) -> Response:
        profile = get_object_or_404(Profile, pk=profile_id)
        services.deactivate_profile(user=cast(User, request.user), profile=profile)
        return Response(status=204)


class AssignProfileView(APIView):
    """`POST /authz/users/{id}/assign-profile` — asigna un perfil a un usuario."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    required_permissions = {"POST": (MODULE_ACCESS_CONTROL, ACTION_UPDATE)}

    @extend_schema(
        request=AssignProfileSerializer,
        responses={
            200: UserIdentitySerializer,
            400: DetailSerializer,
            403: DetailSerializer,
            404: DetailSerializer,
        },
    )
    def post(self, request: Request, user_id: int) -> Response:
        serializer = AssignProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target = get_object_or_404(User, pk=user_id)
        profile = get_object_or_404(Profile, pk=serializer.validated_data["profile_id"])
        updated = services.assign_profile(
            user=cast(User, request.user), target=target, profile=profile
        )
        return Response(UserIdentitySerializer(updated).data, status=200)
