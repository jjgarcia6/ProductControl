"""Serializers de access-control (F2).

`permissions` y `visible_sensitive_fields` se declaran explícitos (DictField/ListField)
para que el OpenAPI tipe el contrato con precisión (no un JSON opaco) y el codegen del
frontend genere tipos/Zod útiles. La validación contra el catálogo vive en el write.

`SensitiveFieldsMixin` es el mecanismo de campos invisibles: OMITE del output (clave +
valor) los campos sensibles que el perfil del usuario no puede ver — no los enmascara
ni los marca read-only.
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from .catalog import SENSITIVE_FIELDS, is_valid_permission
from .models import Profile
from .services import visible_fields_for


class SensitiveFieldsMixin:
    """Elimina del `representation` los campos sensibles no visibles para el perfil.

    Cada serializer concreto declara `sensitive_fields = {campo_serializer: "recurso.campo"}`.
    """

    sensitive_fields: dict[str, str] = {}

    def to_representation(self, instance: Any) -> dict[str, Any]:
        data: dict[str, Any] = super().to_representation(instance)  # type: ignore[misc]
        if not self.sensitive_fields:
            return data
        request = self.context.get("request")  # type: ignore[attr-defined]
        profile = getattr(getattr(request, "user", None), "profile", None)
        visible = visible_fields_for(profile)
        for field_name, registry_key in self.sensitive_fields.items():
            if registry_key not in visible:
                data.pop(field_name, None)
        return data


class ProfileReadSerializer(serializers.ModelSerializer[Profile]):
    """Contrato de lectura de un perfil."""

    permissions = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()),
        help_text="Permisos por módulo: {módulo: [acción, ...]}.",
    )
    visible_sensitive_fields = serializers.ListField(
        child=serializers.CharField(),
        help_text="Campos sensibles visibles ('recurso.campo').",
    )

    class Meta:
        model = Profile
        fields = [
            "id",
            "name",
            "description",
            "permissions",
            "visible_sensitive_fields",
            "auto_approval",
        ]
        read_only_fields = fields


class ProfileWriteSerializer(serializers.ModelSerializer[Profile]):
    """Entrada de creación de un perfil: valida unicidad y catálogo."""

    permissions = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()),
        required=False,
        default=dict,
        help_text="Permisos por módulo: {módulo: [acción, ...]} del catálogo.",
    )
    visible_sensitive_fields = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text="Campos sensibles visibles ('recurso.campo') del registro.",
    )

    class Meta:
        model = Profile
        fields = [
            "name",
            "description",
            "permissions",
            "visible_sensitive_fields",
            "auto_approval",
        ]

    def validate_name(self, value: str) -> str:
        if Profile.objects.filter(name=value).exists():
            raise serializers.ValidationError("Ya existe un perfil con este nombre.")
        return value

    def validate_permissions(self, value: dict[str, list[str]]) -> dict[str, list[str]]:
        for module, actions in value.items():
            for action in actions:
                if not is_valid_permission(module, action):
                    raise serializers.ValidationError(
                        f"El permiso '{module}:{action}' no existe en el catálogo."
                    )
        return value

    def validate_visible_sensitive_fields(self, value: list[str]) -> list[str]:
        for field_key in value:
            if field_key not in SENSITIVE_FIELDS:
                raise serializers.ValidationError(
                    f"El campo sensible '{field_key}' no está registrado."
                )
        return value


class AssignProfileSerializer(serializers.Serializer[dict[str, Any]]):
    """Entrada del endpoint de asignación perfil↔usuario."""

    profile_id = serializers.UUIDField(help_text="Perfil activo a asignar al usuario.")


class ProfileAdminWriteSerializer(serializers.ModelSerializer[Profile]):
    """Edición de un perfil (F3): permisos, campos visibles, descripción y flags.

    No edita `name` (la identidad del perfil es estable); valida contra el catálogo igual
    que la creación (DRY de reglas con `ProfileWriteSerializer`).
    """

    permissions = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()),
        required=False,
        help_text="Permisos por módulo: {módulo: [acción, ...]} del catálogo.",
    )
    visible_sensitive_fields = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Campos sensibles visibles ('recurso.campo') del registro.",
    )

    class Meta:
        model = Profile
        fields = ["description", "permissions", "visible_sensitive_fields", "auto_approval"]

    def validate_permissions(self, value: dict[str, list[str]]) -> dict[str, list[str]]:
        for module, actions in value.items():
            for action in actions:
                if not is_valid_permission(module, action):
                    raise serializers.ValidationError(
                        f"El permiso '{module}:{action}' no existe en el catálogo."
                    )
        return value

    def validate_visible_sensitive_fields(self, value: list[str]) -> list[str]:
        for field_key in value:
            if field_key not in SENSITIVE_FIELDS:
                raise serializers.ValidationError(
                    f"El campo sensible '{field_key}' no está registrado."
                )
        return value
