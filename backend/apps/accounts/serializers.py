"""Serializers de la capability auth (F1).

Entrada (write) y salida (read) separadas. Cada campo lleva `help_text` para que el
OpenAPI (drf-spectacular) y el Diccionario de Datos Vivo lo expongan.

`UserIdentitySerializer` es el punto de extensión de la identidad: F2 le añade
`profile` y F3 el flag `must_change_password`. Ambas fases DEBEN extender este
serializer, no crear uno paralelo (DRY).
"""

from __future__ import annotations

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.authz.serializers import ProfileReadSerializer

from .models import User


class LoginSerializer(serializers.Serializer[dict[str, str]]):
    """Credenciales de entrada del login."""

    username = serializers.CharField(help_text="Identificador de login.")
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        help_text="Contraseña del usuario.",
    )


class UserIdentitySerializer(serializers.ModelSerializer[User]):
    """Identidad del usuario autenticado (respuesta de `login` y de `me`).

    F2 añade `profile` (perfil de permisos, fuente de verdad de la autorización). El
    frontend lo usa para el gating; puede ser `null` mientras un usuario no tenga perfil.
    """

    profile = ProfileReadSerializer(read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "profile",
            "must_change_password",
        ]
        read_only_fields = fields


class ChangePasswordSerializer(serializers.Serializer[dict[str, str]]):
    """Cambio de la contraseña propia: actual + nueva (valida política de Django)."""

    current_password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        help_text="Contraseña actual.",
    )
    new_password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        help_text="Nueva contraseña. Debe cumplir la política de contraseñas de Django.",
    )

    def validate_new_password(self, value: str) -> str:
        # Valida longitud, similitud y contraseñas comunes (AUTH_PASSWORD_VALIDATORS).
        # El usuario autenticado está en el contexto para la validación por similitud.
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else None
        validate_password(value, user=user)
        return value


class TokenResponseSerializer(serializers.Serializer[dict[str, object]]):
    """Respuesta del login: access en el cuerpo + identidad embebida.

    El refresh NO aparece aquí: viaja solo en la cookie httpOnly.
    """

    access = serializers.CharField(
        read_only=True,
        help_text="Access JWT (vida 15 min). El cliente lo mantiene en memoria.",
    )
    user = UserIdentitySerializer(read_only=True)


class AccessTokenSerializer(serializers.Serializer[dict[str, str]]):
    """Respuesta de la renovación: solo el nuevo access (el refresh rota en la cookie)."""

    access = serializers.CharField(
        read_only=True,
        help_text="Nuevo access JWT (vida 15 min).",
    )


class DetailSerializer(serializers.Serializer[dict[str, str]]):
    """Mensaje único en español. Forma del contrato de errores y de los avisos 200."""

    detail = serializers.CharField(read_only=True, help_text="Mensaje para el usuario.")


# --- Administración de usuarios (F3 user-management) --------------------------


class UserAdminReadSerializer(serializers.ModelSerializer[User]):
    """Contrato de lectura de un usuario en la consola de administración."""

    profile = ProfileReadSerializer(read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "profile",
            "must_change_password",
        ]
        read_only_fields = fields


class UserAdminWriteSerializer(serializers.ModelSerializer[User]):
    """Entrada de creación de un usuario. El `role` se sincroniza del perfil (no se envía)."""

    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        help_text="Contraseña inicial. Debe cumplir la política de contraseñas de Django.",
    )
    profile_id = serializers.UUIDField(help_text="Perfil activo a asignar al usuario.")

    class Meta:
        model = User
        fields = ["username", "password", "profile_id", "first_name", "last_name"]
        extra_kwargs = {
            "first_name": {"required": False},
            "last_name": {"required": False},
        }

    def validate_username(self, value: str) -> str:
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con este identificador.")
        return value

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value


class UserAdminUpdateSerializer(serializers.ModelSerializer[User]):
    """Edición de los datos básicos de un usuario (no toca perfil ni contraseña)."""

    class Meta:
        model = User
        fields = ["first_name", "last_name"]


class ResetPasswordWriteSerializer(serializers.Serializer[dict[str, object]]):
    """Reset administrativo: contraseña temporal dada por el admin XOR generada por el sistema."""

    temporary_password = serializers.CharField(
        write_only=True,
        required=False,
        style={"input_type": "password"},
        help_text="Contraseña temporal definida por el admin. Omitir si `generate` es true.",
    )
    generate = serializers.BooleanField(
        default=False,
        help_text="Si es true, el sistema genera la contraseña temporal.",
    )

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        provided = attrs.get("temporary_password")
        generate = attrs.get("generate")
        if bool(provided) == bool(generate):
            raise serializers.ValidationError(
                "Indique una contraseña temporal o active la generación automática, no ambas."
            )
        if provided:
            validate_password(str(provided))
        return attrs


class ResetPasswordReadSerializer(serializers.Serializer[dict[str, str]]):
    """Respuesta del reset: la contraseña temporal, devuelta una sola vez."""

    temporary_password = serializers.CharField(
        read_only=True,
        help_text="Contraseña temporal. Se comunica una sola vez; el usuario deberá cambiarla.",
    )
