"""Lógica de negocio de la importación masiva (capability bulk-import, F7).

El proceso es stateless: `preview_import` (dry-run) y `commit_import` reciben las filas ya
parseadas; el commit re-valida y persiste en una única transacción atómica (all-or-nothing).

La validación NO se reimplementa: cada fila se valida instanciando el serializer de dominio
existente (`ProductWriteSerializer` de F5, `FichaWriteSerializer` de F4) y la persistencia
reusa los services de dominio (`create_product`, `create_ficha`), que ya auditan con `@audit`
y aplican su propia unicidad. La deduplicación omite (skip) las filas cuya clave natural ya
existe entre los registros vivos; una omisión NO es un error y no aborta el commit.
"""

from __future__ import annotations

import csv
import io
from abc import ABC, abstractmethod
from typing import Any, cast

from django.db import transaction
from rest_framework.serializers import BaseSerializer

from apps.accounts.models import User
from apps.directory import services as directory_services
from apps.directory.models import Ficha, FichaStatus
from apps.directory.serializers import FichaWriteSerializer
from apps.products import services as products_services
from apps.products.models import Category, Product, UnitOfMeasure
from apps.products.serializers import ProductWriteSerializer

from .constants import STATUS_ERROR, STATUS_SKIPPED, STATUS_VALID

# Claves de entidad importable (coinciden con el segmento de la ruta).
ENTITY_PRODUCTS = "products"
ENTITY_FICHAS = "fichas"

FieldErrors = dict[str, list[str]]


# --- Importadores por entidad -------------------------------------------------


class _Importer(ABC):
    """Contrato de un importador: normaliza, deduplica y persiste una entidad."""

    entity: str
    columns: list[str]
    example_row: list[str]

    @abstractmethod
    def build_serializer(
        self, raw: dict[str, str]
    ) -> tuple[BaseSerializer[Any] | None, FieldErrors]:
        """Normaliza la fila cruda a un serializer de dominio y sus pre-errores.

        Devuelve `(serializer, pre_errors)`. Si `pre_errors` no está vacío, el serializer
        es `None` (la fila ya es error por referencias inexistentes) y no se valida más.
        """

    @abstractmethod
    def natural_key(self, validated: dict[str, Any]) -> str:
        """Clave natural para deduplicar (nombre / número de identificación)."""

    @abstractmethod
    def duplicate_exists(self, key: str) -> bool:
        """¿Ya existe un registro VIVO con esa clave natural?"""

    @abstractmethod
    def create(self, *, user: User, validated: dict[str, Any]) -> None:
        """Persiste una fila válida reusando el service de dominio (que audita)."""


class _ProductImporter(_Importer):
    entity = ENTITY_PRODUCTS
    columns = ["name", "category", "unit"]
    example_row = ["Leche entera 1L", "Lácteos", "Unidad"]

    def build_serializer(
        self, raw: dict[str, str]
    ) -> tuple[BaseSerializer[Any] | None, FieldErrors]:
        pre_errors: FieldErrors = {}
        category_name = raw.get("category", "").strip()
        unit_name = raw.get("unit", "").strip()
        category = Category.objects.filter(name=category_name).first()
        unit = UnitOfMeasure.objects.filter(name=unit_name).first()
        if category is None:
            pre_errors["category"] = [f"No existe la categoría '{category_name}'."]
        if unit is None:
            pre_errors["unit"] = [f"No existe la unidad de medida '{unit_name}'."]
        if pre_errors:
            return None, pre_errors
        data = {
            "name": raw.get("name", "").strip(),
            "category": cast(Category, category).pk,
            "unit_of_measure": cast(UnitOfMeasure, unit).pk,
        }
        return ProductWriteSerializer(data=data), {}

    def natural_key(self, validated: dict[str, Any]) -> str:
        return cast(str, validated["name"])

    def duplicate_exists(self, key: str) -> bool:
        return Product.objects.filter(name=key).exists()

    def create(self, *, user: User, validated: dict[str, Any]) -> None:
        products_services.create_product(user=user, data=dict(validated))


class _FichaImporter(_Importer):
    entity = ENTITY_FICHAS
    columns = ["identification_type", "identification_number", "name", "email", "phone", "roles"]
    example_row = ["CEDULA", "1710034065", "Juan Pérez", "juan@example.com", "099", "CLIENTE"]

    def build_serializer(
        self, raw: dict[str, str]
    ) -> tuple[BaseSerializer[Any] | None, FieldErrors]:
        roles = [part.strip().upper() for part in raw.get("roles", "").replace(";", ",").split(",")]
        data = {
            "name": raw.get("name", "").strip(),
            "identification_type": raw.get("identification_type", "").strip().upper(),
            "identification_number": raw.get("identification_number", "").strip(),
            "email": raw.get("email", "").strip(),
            "phone": raw.get("phone", "").strip(),
            "roles": [role for role in roles if role],
        }
        return FichaWriteSerializer(data=data), {}

    def natural_key(self, validated: dict[str, Any]) -> str:
        return cast(str, validated["identification_number"])

    def duplicate_exists(self, key: str) -> bool:
        return (
            Ficha.objects.exclude(status=FichaStatus.INACTIVO)
            .filter(identification_number=key)
            .exists()
        )

    def create(self, *, user: User, validated: dict[str, Any]) -> None:
        directory_services.create_ficha(user=user, data=dict(validated))


_IMPORTERS: dict[str, _Importer] = {
    ENTITY_PRODUCTS: _ProductImporter(),
    ENTITY_FICHAS: _FichaImporter(),
}


def _get_importer(entity: str) -> _Importer:
    return _IMPORTERS[entity]


# --- Validación y persistencia -----------------------------------------------


def _flatten(value: Any) -> list[str]:
    """Aplana cualquier estructura de errores de DRF a una lista de mensajes."""
    if isinstance(value, dict):
        messages: list[str] = []
        for item in value.values():
            messages.extend(_flatten(item))
        return messages
    if isinstance(value, (list, tuple)):
        messages = []
        for item in value:
            messages.extend(_flatten(item))
        return messages
    return [str(value)]


def _flatten_errors(errors: Any) -> FieldErrors:
    return {str(key): _flatten(value) for key, value in errors.items()}


def _process(
    importer: _Importer, rows: list[tuple[int, dict[str, str]]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Valida y deduplica cada fila. Devuelve (reportes, payloads de filas válidas)."""
    reports: list[dict[str, Any]] = []
    valid_payloads: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    for row_number, raw in rows:
        serializer, pre_errors = importer.build_serializer(raw)
        if serializer is None:
            # Referencias inexistentes (categoría/unidad): la fila ya es error, no se valida más.
            reports.append({"row_number": row_number, "status": STATUS_ERROR, "errors": pre_errors})
            continue
        if not serializer.is_valid():
            reports.append(
                {
                    "row_number": row_number,
                    "status": STATUS_ERROR,
                    "errors": _flatten_errors(serializer.errors),
                }
            )
            continue

        validated = cast(dict[str, Any], serializer.validated_data)
        key = importer.natural_key(validated)
        if key in seen_keys or importer.duplicate_exists(key):
            reports.append({"row_number": row_number, "status": STATUS_SKIPPED, "errors": {}})
            continue

        seen_keys.add(key)
        reports.append({"row_number": row_number, "status": STATUS_VALID, "errors": {}})
        valid_payloads.append(validated)

    return reports, valid_payloads


def _summary(*, dry_run: bool, inserted: int, reports: list[dict[str, Any]]) -> dict[str, Any]:
    skipped = sum(1 for report in reports if report["status"] == STATUS_SKIPPED)
    has_errors = any(report["status"] == STATUS_ERROR for report in reports)
    return {
        "dry_run": dry_run,
        "inserted": inserted,
        "skipped": skipped,
        "rows": reports,
        "has_errors": has_errors,
    }


def preview_import(entity: str, rows: list[tuple[int, dict[str, str]]]) -> dict[str, Any]:
    """Previsualiza (dry-run): valida sin persistir y devuelve el reporte por fila."""
    reports, _ = _process(_get_importer(entity), rows)
    return _summary(dry_run=True, inserted=0, reports=reports)


def commit_import(
    entity: str, rows: list[tuple[int, dict[str, str]]], *, user: User
) -> dict[str, Any]:
    """Confirma la importación. Persiste all-or-nothing solo si ninguna fila tiene error.

    Re-valida (barato, garantiza consistencia si el catálogo cambió). Si hay errores, no
    persiste nada (`has_errors=True`, la view responde 400). Reusa los services de dominio
    por fila dentro de una transacción atómica: cada alta se audita con su `@audit`.
    """
    importer = _get_importer(entity)
    reports, valid_payloads = _process(importer, rows)
    if any(report["status"] == STATUS_ERROR for report in reports):
        return _summary(dry_run=False, inserted=0, reports=reports)

    with transaction.atomic():
        for payload in valid_payloads:
            importer.create(user=user, validated=payload)
    return _summary(dry_run=False, inserted=len(valid_payloads), reports=reports)


def build_template_csv(entity: str) -> str:
    """Genera el CSV de plantilla (cabecera + una fila de ejemplo) de una entidad."""
    importer = _get_importer(entity)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(importer.columns)
    writer.writerow(importer.example_row)
    return buffer.getvalue()
