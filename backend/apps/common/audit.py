"""Mecanismo de auditoría transversal (apps.common).

El bootstrap provee SOLO el mecanismo: el decorador `@audit(action, entity)` que
registra un `AuditLog` cuando un service se ejecuta con éxito. Las REGLAS de qué se
audita (qué acciones, qué campos, valores anterior/nuevo) llegan en `add-audit-rules`;
aquí no se decide nada de eso.

Uso previsto (en services, no en views ni serializers):

    @audit(action="create", entity="supplier")
    def create_supplier(*, user, data): ...

La función decorada DEBE recibir `user` como keyword (o devolver un objeto con `.user`)
para poder atribuir el registro; si no hay usuario, se registra con user=None.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def audit(action: str, entity: str) -> Callable[[F], F]:
    """Registra un AuditLog tras la ejecución exitosa del callable decorado.

    No define reglas de negocio: solo deja el rastro (acción + entidad + usuario).
    El detalle campo/valor-anterior/valor-nuevo se completará en `add-audit-rules`.
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
                action=action,
                entity=entity,
                object_id=object_id,
            )
            return result

        return wrapper  # type: ignore[return-value]

    return decorator
