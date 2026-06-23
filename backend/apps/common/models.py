"""Modelos base transversales (apps.common).

El bootstrap deja la INFRAESTRUCTURA preparada, SIN lógica de negocio:
- TimeStampedModel: marcas de tiempo.
- Soft delete de la CLASE 2 (catálogos / datos maestros sin máquina de estado):
  `deleted_at` + manager por defecto que filtra. Los índices únicos parciales
  (WHERE deleted_at IS NULL) se declaran en cada modelo concreto en su change.
- AuditLog + mecanismo de auditoría (el decorador `@audit` vive en audit.py).

La política de soft delete tiene TRES clases (config.yaml). El bootstrap solo provee
el mixin de la clase 2; las otras dos son convenciones que cada change respeta:
  1. Documentos con máquina de estados / Kardex -> append-only / inmutables
     (no se borran; se reversan por estado). No usan este mixin.
  2. Catálogos y maestros sin máquina de estado -> este mixin (SoftDeleteModel).
  3. Fichas de Directorio -> estado INACTIVO (no borrado). No usan este mixin.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """Marca `created_at` / `updated_at` en cada fila."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet["SoftDeleteModel"]):
    """QuerySet que distingue filas vivas de borradas lógicamente."""

    def alive(self) -> SoftDeleteQuerySet:
        return self.filter(deleted_at__isnull=True)

    def dead(self) -> SoftDeleteQuerySet:
        return self.filter(deleted_at__isnull=False)

    def delete(self) -> int:  # type: ignore[override]
        """Borrado lógico en bloque: marca `deleted_at`, no elimina filas."""
        return self.update(deleted_at=timezone.now())


class SoftDeleteManager(models.Manager["SoftDeleteModel"]):
    """Manager por defecto: SOLO devuelve filas vivas (deleted_at IS NULL)."""

    def get_queryset(self) -> SoftDeleteQuerySet:
        return SoftDeleteQuerySet(self.model, using=self._db).alive()


class SoftDeleteModel(TimeStampedModel):
    """Soft delete de la clase 2 (catálogos / datos maestros sin máquina de estado).

    `objects` filtra los borrados; `all_objects` los incluye. `delete()` es lógico;
    `hard_delete()` elimina de verdad (uso administrativo).

    Cada modelo concreto declara sus índices únicos parciales en su propia migración,
    p. ej.: UniqueConstraint(fields=[...], condition=Q(deleted_at__isnull=True)).
    """

    deleted_at = models.DateTimeField(null=True, blank=True, default=None, db_index=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager.from_queryset(SoftDeleteQuerySet)()

    class Meta:
        abstract = True

    def delete(  # type: ignore[override]
        self, using: Any = None, keep_parents: bool = False
    ) -> None:
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])

    def hard_delete(
        self, using: Any = None, keep_parents: bool = False
    ) -> tuple[int, dict[str, int]]:
        return super().delete(using=using, keep_parents=keep_parents)

    def restore(self) -> None:
        self.deleted_at = None
        self.save(update_fields=["deleted_at", "updated_at"])


class AuditLog(TimeStampedModel):
    """Registro de auditoría. Qué se audita (las reglas) llega en `add-audit-rules`.

    El bootstrap solo provee el MODELO y el mecanismo. Guarda quién, qué acción, sobre
    qué entidad, y opcionalmente el cambio campo/valor anterior/valor nuevo.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=64)
    entity = models.CharField(max_length=128)
    object_id = models.CharField(max_length=64, blank=True, default="")
    field = models.CharField(max_length=128, blank=True, default="")
    old_value = models.TextField(blank=True, default="")
    new_value = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["entity", "object_id"]),
            models.Index(fields=["action"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} {self.entity}#{self.object_id}"
