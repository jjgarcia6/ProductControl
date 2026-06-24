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
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import AuthenticationFailed, Throttled
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import User
from .serializers import (
    AccessTokenSerializer,
    ChangePasswordSerializer,
    DetailSerializer,
    LoginSerializer,
    TokenResponseSerializer,
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
