"""Mecanismo de auditoría transversal (apps.common).

Dos piezas complementarias, ninguna repite la lógica de la otra:

- `@audit(action, entity)`: registra el EVENTO grueso (usuario/acción/entidad/object_id)
  cuando un service se ejecuta con éxito. No calcula diff campo-nivel.
- `record_field_changes(...)`: registra el DIFF a nivel de campo de una corrección —una
  fila `AuditLog` por campo auditado con cambio real, con valor anterior y nuevo.

El vocabulario de acciones y el registro de qué campos se auditan viven en
`apps.common.audit_rules` (`AuditAction`, `AUDITED_FIELDS`, `is_audited`).

Uso previsto (en services, no en views ni serializers):

    @audit(action=AuditAction.CREATE, entity="Supplier")
    def create_supplier(*, user, data): ...

La función decorada DEBE recibir `user` como keyword (o devolver un objeto con `.user`)
para poder atribuir el registro; si no hay usuario, se registra con user=None.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, TypeVar

from django.db.models import Model

if TYPE_CHECKING:
    from apps.common.models import AuditLog

F = TypeVar("F", bound=Callable[..., Any])


def audit(action: str, entity: str) -> Callable[[F], F]:
    """Registra un AuditLog tras la ejecución exitosa del callable decorado.

    Registra SOLO el evento grueso (acción + entidad + usuario + object_id); NO calcula
    el diff campo/valor-anterior/valor-nuevo —de eso se encarga `record_field_changes`.
    `action` acepta un miembro de `AuditAction` (subclase de `str`): el valor persistido
    es su `value` canónico.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = func(*args, **kwargs)
            # Import diferido para evitar dependencias circulares con apps cargando.
            from apps.common.models import AuditLog

            user = kwargs.get("user")
            object_id = ""
            if result is not None and hasattr(result, "pk") and result.pk is not None:
                object_id = str(result.pk)

            AuditLog.objects.create(
                user=user,
                action=str(action),
                entity=entity,
                object_id=object_id,
            )
            return result

        return wrapper  # type: ignore[return-value]

    return decorator


def to_audit_str(value: Any) -> str:
    """Normaliza un valor para el rastro de auditoría, de forma estable y comparable.

    - `None` -> `""` (cadena vacía).
    - `Decimal` -> notación simple sin exponente (`format(value, "f")`).
    - `date`/`datetime` -> ISO 8601.
    - `Model` (FK) -> su `pk` como cadena.
    - resto -> `str(value)`.
    """
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Model):
        return str(value.pk)
    return str(value)


def record_field_changes(
    *,
    user: Any,
    entity: str,
    object_id: Any,
    before: dict[str, Any],
    after: dict[str, Any],
    action: str = "",
) -> list[AuditLog]:
    """Registra el diff campo-nivel de una corrección: una fila por campo cambiado.

    Emite un `AuditLog` por cada campo de `after` que (a) esté registrado como auditable
    en `AUDITED_FIELDS` y (b) tenga un cambio real respecto a `before` (comparado sobre
    la forma normalizada por `to_audit_str`). Devuelve los registros creados.

    NO abre transacción propia: DEBE ejecutarse DENTRO del `transaction.atomic()` del
    service llamador, de modo que el diff se revierta junto con la corrección si esta falla.
    """
    from apps.common.audit_rules import AuditAction, is_audited
    from apps.common.models import AuditLog

    resolved_action = str(action) if action else str(AuditAction.CORRECTION)
    created: list[AuditLog] = []
    for field, new in after.items():
        if not is_audited(entity, field):
            continue
        old_str = to_audit_str(before.get(field))
        new_str = to_audit_str(new)
        if old_str == new_str:
            continue
        created.append(
            AuditLog.objects.create(
                user=user,
                action=resolved_action,
                entity=entity,
                object_id=str(object_id),
                field=field,
                old_value=old_str,
                new_value=new_str,
            )
        )
    return created
