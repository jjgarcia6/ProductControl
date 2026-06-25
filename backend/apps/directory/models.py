"""Modelo de ficha de tercero (capability directory, F4).

`Ficha` es la base maestra de las entidades externas con las que opera el negocio
(clientes, proveedores, responsables de ruta, choferes). Registra identificación
validada por dígito verificador, contacto, roles múltiples y un estado.

Soft delete de la CLASE 3 (config.yaml): la baja es el estado INACTIVO, reversible.
NO hereda `SoftDeleteModel` ni usa `deleted_at`. El número de identificación es único
SOLO entre fichas no inactivas (índice parcial). Los códigos de enum van en español
MAYÚSCULAS, consistentes con `accounts.Role` (JEFE/SUPERVISOR/RUTA).
"""

from __future__ import annotations

import uuid

from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.db import models

from apps.common.models import TimeStampedModel


class IdentificationType(models.TextChoices):
    CEDULA = "CEDULA", "Cédula"
    RUC = "RUC", "RUC"
    PASAPORTE = "PASAPORTE", "Pasaporte"


class FichaRole(models.TextChoices):
    CLIENTE = "CLIENTE", "Cliente"
    PROVEEDOR = "PROVEEDOR", "Proveedor"
    RESPONSABLE_RUTA = "RESPONSABLE_RUTA", "Responsable de ruta"
    CHOFER = "CHOFER", "Chofer"


class FichaStatus(models.TextChoices):
    ACTIVO = "ACTIVO", "Activo"
    BLOQUEADO = "BLOQUEADO", "Bloqueado"
    INACTIVO = "INACTIVO", "Inactivo"


class Ficha(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="Nombre o razón social del tercero.")
    identification_type = models.CharField(
        max_length=10,
        choices=IdentificationType.choices,
        help_text="Tipo de identificación: CEDULA, RUC o PASAPORTE.",
    )
    identification_number = models.CharField(
        max_length=20,
        help_text="Número de identificación validado por dígito verificador (pasaporte sin checksum).",  # noqa: E501
    )
    email = models.EmailField(blank=True, help_text="Correo de contacto (opcional).")
    phone = models.CharField(
        max_length=20, blank=True, help_text="Teléfono o WhatsApp de contacto (opcional)."
    )
    roles = ArrayField(
        models.CharField(max_length=20, choices=FichaRole.choices),
        help_text="Roles del tercero: ≥1 de CLIENTE/PROVEEDOR/RESPONSABLE_RUTA/CHOFER.",
    )
    status = models.CharField(
        max_length=10,
        choices=FichaStatus.choices,
        default=FichaStatus.ACTIVO,
        db_index=True,
        help_text="Estado de la ficha. Cambia por acciones explícitas, no por edición directa.",
    )
    user = models.OneToOneField(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ficha",
        help_text="Usuario del sistema vinculado a la ficha (1:1, opcional).",
    )

    class Meta:
        db_table = "directory_fichas"
        constraints = [
            models.UniqueConstraint(
                fields=["identification_number"],
                condition=~models.Q(status="INACTIVO"),
                name="uq_ficha_identification_number_not_inactive",
            ),
        ]
        indexes = [GinIndex(fields=["roles"], name="ix_ficha_roles_gin")]

    def __str__(self) -> str:
        return f"{self.name} ({self.identification_number})"
