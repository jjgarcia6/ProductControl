"""Modelo de usuario del sistema (capability auth, F1).

`User` extiende `AbstractUser`: hereda `username`, `password`, `is_active`,
`first_name`, `last_name`, etc. Añade `role` (clasificación nominal del sistema).

Decisiones (ver design.md):
- PK entera autoincremental de `AbstractUser` (no UUID): compatibilidad con
  SimpleJWT/Django auth y simplicidad (KISS).
- NO hereda `SoftDeleteMixin`: el usuario NO es catálogo. Su baja administrativa
  se modela con `is_active` (F3 user-management), nunca con `deleted_at`.
- La autorización fina por rol se define en access-control (F2); aquí `role` es
  solo estructura.
"""

from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    JEFE = "JEFE", "Jefe"
    SUPERVISOR = "SUPERVISOR", "Supervisor"
    RUTA = "RUTA", "Responsable de ruta"
    USUARIO = "USUARIO", "Usuario"


class User(AbstractUser):
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.USUARIO,
        db_index=True,
        help_text=(
            "Rol del sistema. La autorización fina por rol se define en access-control (F2)."
        ),
    )

    class Meta:
        db_table = "accounts_user"

    def __str__(self) -> str:
        return self.username
