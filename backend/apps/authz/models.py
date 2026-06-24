"""Modelo de perfil de permisos (capability access-control, F2).

`Profile` es la fuente de verdad de la autorización (no el `role` nominal de F1).
Agrupa permisos por (módulo, acción) tomados del catálogo, el registro de campos
sensibles visibles y el flag de capacidad `auto_approval`.

Es catálogo configurable -> soft delete de la CLASE 2 (`SoftDeleteModel`): se da de
baja con `deleted_at`; el nombre es único SOLO entre perfiles vivos (índice parcial).
"""

from __future__ import annotations

import uuid

from django.db import models

from apps.common.models import SoftDeleteModel


class Profile(SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text="Nombre único del perfil.")
    description = models.CharField(
        max_length=255, blank=True, default="", help_text="Descripción opcional del perfil."
    )
    permissions = models.JSONField(
        default=dict,
        blank=True,
        help_text="Permisos por (módulo, acción): {módulo: [acción, ...]} del catálogo.",
    )
    visible_sensitive_fields = models.JSONField(
        default=list,
        blank=True,
        help_text="Campos sensibles que el perfil puede ver ('recurso.campo').",
    )
    auto_approval = models.BooleanField(
        default=False, help_text="Capacidad de auto-aprobación (estructural en F2)."
    )

    class Meta:
        db_table = "profiles"
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                condition=models.Q(deleted_at__isnull=True),
                name="uq_profile_name_active",
            )
        ]

    def __str__(self) -> str:
        return self.name
