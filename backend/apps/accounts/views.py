"""Vistas delgadas de auth (F1).

Cada vista valida con su serializer y delega TODA la lógica en `services`. Las
transiciones (login/refresh/logout/change-password) son explícitas, no CRUD genérico.
Anotadas con drf-spectacular para que el schema OpenAPI refleje el cuerpo real (access
en el cuerpo, refresh en cookie) — el frontend genera sus tipos/Zod desde ese schema.
"""

from __future__ import annotations

from typing import cast

from django.conf import settings
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import AuthenticationFailed, Throttled
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authz.catalog import (
    ACTION_CREATE,
    ACTION_READ,
    ACTION_UPDATE,
    MODULE_ACCESS_CONTROL,
)
from apps.authz.models import Profile
from apps.authz.permissions import HasModulePermission

from . import services
from .models import User
from .serializers import (
    AccessTokenSerializer,
    ChangePasswordSerializer,
    DetailSerializer,
    LoginSerializer,
    ResetPasswordReadSerializer,
    ResetPasswordWriteSerializer,
    TokenResponseSerializer,
    UserAdminReadSerializer,
    UserAdminUpdateSerializer,
    UserAdminWriteSerializer,
    UserIdentitySerializer,
)


class _UnauthenticatedAPIView(APIView):
    """Vistas sin autenticador (login/refresh por cookie).

    Sin authenticators, DRF respondería 403 a `AuthenticationFailed`; este header fuerza
    el 401 correcto del contrato (credenciales/sesión inválidas).
    """

    authentication_classes: list[type] = []
    permission_classes = [AllowAny]

    def get_authenticate_header(self, request: Request) -> str:
        return "Bearer"


@method_decorator(
    ratelimit(key="ip", rate=settings.LOGIN_RATELIMIT, method="POST", block=False),
    name="post",
)
class LoginView(_UnauthenticatedAPIView):
    """`POST /auth/login` — autentica y emite tokens. Público, con rate limit por IP."""

    @extend_schema(
        request=LoginSerializer,
        responses={200: TokenResponseSerializer, 401: DetailSerializer},
    )
    def post(self, request: Request) -> Response:
        if getattr(request, "limited", False):
            raise Throttled(detail="Demasiados intentos de inicio de sesión. Intente más tarde.")
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            # Cubre credenciales inválidas Y usuarios inactivos (ModelBackend).
            raise AuthenticationFailed("Credenciales inválidas.")

        response = Response(status=200)
        access = services.issue_tokens(user, response)
        response.data = {
            "access": access,
            "user": UserIdentitySerializer(user).data,
        }
        return response


class RefreshView(_UnauthenticatedAPIView):
    """`POST /auth/refresh` — renueva el access desde el refresh de la cookie."""

    @extend_schema(
        request=None,
        responses={200: AccessTokenSerializer, 401: DetailSerializer},
    )
    def post(self, request: Request) -> Response:
        raw_refresh = request.COOKIES.get(settings.AUTH_COOKIE_NAME)
        response = Response(status=200)
        access = services.rotate_refresh(raw_refresh, response)
        response.data = {"access": access}
        return response


class LogoutView(APIView):
    """`POST /auth/logout` — invalida el refresh y limpia la cookie."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: DetailSerializer})
    def post(self, request: Request) -> Response:
        raw_refresh = request.COOKIES.get(settings.AUTH_COOKIE_NAME)
        response = Response({"detail": "Sesión cerrada."}, status=200)
        services.revoke_refresh(raw_refresh, response)
        return response


class MeView(APIView):
    """`GET /auth/me` — identidad del usuario autenticado."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserIdentitySerializer, 401: DetailSerializer})
    def get(self, request: Request) -> Response:
        return Response(UserIdentitySerializer(cast(User, request.user)).data, status=200)


class ChangePasswordView(APIView):
    """`POST /auth/change-password` — cambio de la contraseña propia."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ChangePasswordSerializer,
        responses={200: DetailSerializer, 400: DetailSerializer, 401: DetailSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        services.change_own_password(
            cast(User, request.user),
            serializer.validated_data["current_password"],
            serializer.validated_data["new_password"],
        )
        return Response({"detail": "Contraseña actualizada. Vuelva a iniciar sesión."}, status=200)


# --- Administración de usuarios (F3 user-management) --------------------------
# Vistas delgadas: validan con su serializer y delegan en `services`. La autorización la
# resuelve `HasModulePermission` por el perfil del usuario (solo el Jefe administra).


class UserAdminListCreateView(APIView):
    """`GET /auth/users` (listado) y `POST /auth/users` (alta)."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    required_permissions = {
        "GET": (MODULE_ACCESS_CONTROL, ACTION_READ),
        "POST": (MODULE_ACCESS_CONTROL, ACTION_CREATE),
    }

    @extend_schema(responses={200: UserAdminReadSerializer(many=True), 403: DetailSerializer})
    def get(self, request: Request) -> Response:
        users = User.objects.all().order_by("username")
        return Response(UserAdminReadSerializer(users, many=True).data, status=200)

    @extend_schema(
        request=UserAdminWriteSerializer,
        responses={201: UserAdminReadSerializer, 400: DetailSerializer, 403: DetailSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = UserAdminWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = get_object_or_404(Profile, pk=serializer.validated_data["profile_id"])
        created = services.create_user(
            user=cast(User, request.user),
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
            profile=profile,
            first_name=serializer.validated_data.get("first_name", ""),
            last_name=serializer.validated_data.get("last_name", ""),
        )
        return Response(UserAdminReadSerializer(created).data, status=201)


class UserAdminDetailView(APIView):
    """`PATCH /auth/users/{id}` — edita los datos básicos del usuario."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    required_permissions = {"PATCH": (MODULE_ACCESS_CONTROL, ACTION_UPDATE)}

    @extend_schema(
        request=UserAdminUpdateSerializer,
        responses={
            200: UserAdminReadSerializer,
            400: DetailSerializer,
            403: DetailSerializer,
            404: DetailSerializer,
        },
    )
    def patch(self, request: Request, user_id: int) -> Response:
        target = get_object_or_404(User, pk=user_id)
        serializer = UserAdminUpdateSerializer(instance=target, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = services.update_user(
            user=cast(User, request.user),
            target=target,
            first_name=serializer.validated_data.get("first_name", target.first_name),
            last_name=serializer.validated_data.get("last_name", target.last_name),
        )
        return Response(UserAdminReadSerializer(updated).data, status=200)


class DeactivateUserView(APIView):
    """`POST /auth/users/{id}/deactivate` — desactiva al usuario e invalida su sesión."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    required_permissions = {"POST": (MODULE_ACCESS_CONTROL, ACTION_UPDATE)}

    @extend_schema(
        request=None,
        responses={200: UserAdminReadSerializer, 403: DetailSerializer, 404: DetailSerializer},
    )
    def post(self, request: Request, user_id: int) -> Response:
        target = get_object_or_404(User, pk=user_id)
        updated = services.deactivate_user(user=cast(User, request.user), target=target)
        return Response(UserAdminReadSerializer(updated).data, status=200)


class ReactivateUserView(APIView):
    """`POST /auth/users/{id}/reactivate` — reactiva al usuario."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    required_permissions = {"POST": (MODULE_ACCESS_CONTROL, ACTION_UPDATE)}

    @extend_schema(
        request=None,
        responses={200: UserAdminReadSerializer, 403: DetailSerializer, 404: DetailSerializer},
    )
    def post(self, request: Request, user_id: int) -> Response:
        target = get_object_or_404(User, pk=user_id)
        updated = services.reactivate_user(user=cast(User, request.user), target=target)
        return Response(UserAdminReadSerializer(updated).data, status=200)


class ResetPasswordView(APIView):
    """`POST /auth/users/{id}/reset-password` — reset administrativo con cambio forzado."""

    permission_classes = [IsAuthenticated, HasModulePermission]
    required_permissions = {"POST": (MODULE_ACCESS_CONTROL, ACTION_UPDATE)}

    @extend_schema(
        request=ResetPasswordWriteSerializer,
        responses={
            200: ResetPasswordReadSerializer,
            400: DetailSerializer,
            403: DetailSerializer,
            404: DetailSerializer,
        },
    )
    def post(self, request: Request, user_id: int) -> Response:
        target = get_object_or_404(User, pk=user_id)
        serializer = ResetPasswordWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data["generate"]:
            raw_password = services.generate_temporary_password()
        else:
            raw_password = cast(str, serializer.validated_data["temporary_password"])
        services.reset_password(
            user=cast(User, request.user), target=target, raw_password=raw_password
        )
        return Response({"temporary_password": raw_password}, status=200)
