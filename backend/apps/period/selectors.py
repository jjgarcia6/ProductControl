"""Selectores de lectura de la capability period (F9)."""

from __future__ import annotations

from .models import Period


def get_period(year: int, month: int) -> Period | None:
    """Resuelve el período de un `(year, month)` o `None` si no existe.

    `None` significa mes implícitamente abierto (no hay fila para ese mes contable).
    """
    return Period.objects.filter(year=year, month=month).first()
