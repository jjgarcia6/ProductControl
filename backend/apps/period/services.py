"""Validador transversal de período cerrado (capability period, F9).

Regla de dominio reutilizable que las capas de service de las fases consumidoras (F11+)
invocarán antes de crear o modificar un documento fechado.

Precondición para fases consumidoras (F11+):
- La fecha contable de los documentos DEBE modelarse como `DateField` (no
  `DateTimeField`), interpretada en zona local America/Guayaquil (UTC-5, sin DST). De
  `doc_date` se extraen `(year, month)`.
- Cada service de documento DEBE invocar `assert_date_operable` tanto en create como en
  update. En update, si la fecha cambia, se valida la NUEVA fecha (y, según la regla del
  documento, también la actual). Cada fase consumidora incluye su propio Scenario de
  "fecha en período cerrado → 400 non_field_errors".

El rechazo se emite con el contrato de errores uniforme: `ValidationError` con una lista
de mensajes, que el `EXCEPTION_HANDLER` de `apps.common` mapea a
`{"non_field_errors": [...]}` con HTTP 400.
"""

from __future__ import annotations

from datetime import date

from rest_framework.exceptions import ValidationError

from .models import Period
from .selectors import get_period

CLOSED_PERIOD_MESSAGE = "La fecha pertenece a un período cerrado."


def is_period_closed(doc_date: date) -> bool:
    """Devuelve `True` solo si existe un período `CLOSED` para el `(año, mes)` de la fecha.

    Ausencia de período (implícita-abierta) o período `OPEN` -> `False` (operable).
    """
    period = get_period(doc_date.year, doc_date.month)
    return period is not None and period.status == Period.Status.CLOSED


def assert_date_operable(doc_date: date) -> None:
    """Levanta `ValidationError` (400 `non_field_errors`) si `doc_date` cae en período cerrado.

    No hace nada si la fecha es operable (mes sin período o período abierto).
    """
    if is_period_closed(doc_date):
        raise ValidationError([CLOSED_PERIOD_MESSAGE])
