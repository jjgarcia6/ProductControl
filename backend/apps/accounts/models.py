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
    # F2 (access-control): el perfil es la FUENTE DE VERDAD de la autorización; el `role`
    # queda como clasificación nominal. Nullable en BD para no romper filas existentes; el
    # seed/backfill de F2 asigna a cada usuario su perfil homónimo. PROTECT: un perfil en
    # uso no puede borrarse.
    profile = models.ForeignKey(
        "authz.Profile",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="users",
        help_text="Perfil que gobierna la autorización del usuario (no el role).",
    )
    # F3 (user-management): tras un reset administrativo el usuario recibe una contraseña
    # temporal y este flag queda activo; mientras lo esté, solo puede cambiar su contraseña.
    # El cambio de contraseña propio (F1) lo desactiva.
    must_change_password = models.BooleanField(
        default=False,
        help_text=(
            "Obliga al usuario a cambiar su contraseña en el primer acceso tras un reset "
            "administrativo. Se desactiva al cambiarla con éxito."
        ),
    )

    class Meta:
        db_table = "accounts_user"

    def __str__(self) -> str:
        return self.username
