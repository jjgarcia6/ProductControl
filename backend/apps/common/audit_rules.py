"""Reglas declarativas de auditoría (add-audit-rules, F10).

Este módulo NO toca el ORM: define el VOCABULARIO de acciones (`AuditAction`), la
convención de nombres de `entity` y el REGISTRO de qué campos se auditan a nivel de
campo (`AUDITED_FIELDS`). El mecanismo que consume estas reglas vive en
`apps.common.audit` (`record_field_changes`).

Convención de `entity`: el nombre del modelo en PascalCase (`User`, `Ficha`, `Product`,
`PriceListItem`, …), idéntico al literal que ya usan los `@audit` existentes.

`AUDITED_FIELDS` es un registro de CÓDIGO, extensible por cada fase consumidora (como el
catálogo de permisos de `authz`): NO es una tabla ni una entidad configurable. Cada fase
F11+ con documentos corregibles añade aquí su entrada `entity -> {campos auditables}` y
llama a `record_field_changes` en su service de corrección.
"""

from __future__ import annotations

from django.db import models


class AuditAction(models.TextChoices):
    """Vocabulario canónico de acciones de auditoría.

    Cada `value` COINCIDE con el literal que ya usan los `@audit` de F1–F7, de modo que
    el retrofit de constantes NO cambia ningún dato persistido en `AuditLog.action`.
    `CORRECTION` es nueva: distingue una corrección post-generación de un `UPDATE`.
    """

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    CORRECTION = "CORRECTION"  # nuevo — corrección post-generación de documentos
    DELETE = "DELETE"
    SOFT_DELETE = "SOFT_DELETE"
    STATE_CHANGE = "STATE_CHANGE"


# entity (PascalCase) -> campos auditados a nivel de campo. Vacío en F10: cada fase F11+
# registra aquí los campos corregibles de sus documentos (p. ej. "peso", "costo").
AUDITED_FIELDS: dict[str, frozenset[str]] = {}


def is_audited(entity: str, field: str) -> bool:
    """Indica si `field` de `entity` está registrado para auditoría a nivel de campo."""
    return field in AUDITED_FIELDS.get(entity, frozenset())
