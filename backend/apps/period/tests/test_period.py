"""Tests de la capability period (F9).

Cubren los Scenarios del delta `specs/period/spec.md`. Como F9 no expone endpoints, los
Scenarios se prueban al nivel de la regla de dominio (el validador `assert_date_operable`
y la unicidad del modelo). Los períodos `CLOSED` se establecen creando la fila
directamente (no hay proceso de cierre hasta F25). El mapeo al contrato de errores
(`{"non_field_errors": [...]}`, HTTP 400) se verifica pasando el `ValidationError` por el
`custom_exception_handler` de `apps.common`.
"""

from __future__ import annotations

from datetime import date

import pytest
from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from apps.common.exceptions import custom_exception_handler
from apps.period.models import Period
from apps.period.selectors import get_period
from apps.period.services import (
    CLOSED_PERIOD_MESSAGE,
    assert_date_operable,
    is_period_closed,
)

pytestmark = pytest.mark.django_db


def _closed(year: int, month: int) -> Period:
    return Period.objects.create(year=year, month=month, status=Period.Status.CLOSED)


def _open(year: int, month: int) -> Period:
    return Period.objects.create(year=year, month=month, status=Period.Status.OPEN)


# --- Requirement: Período contable mensual con estado ---


def test_unicidad_periodo_rechaza_duplicado():
    """Scenario: Unicidad del período — mismo (año, mes) viola la unicidad."""
    _open(2026, 5)
    with pytest.raises(IntegrityError), transaction.atomic():
        Period.objects.create(year=2026, month=5, status=Period.Status.OPEN)


def test_check_constraint_rechaza_mes_fuera_de_rango():
    """El mes fuera de 1–12 lo rechaza la BD (integridad a nivel de constraint)."""
    with pytest.raises(IntegrityError), transaction.atomic():
        Period.objects.create(year=2026, month=13, status=Period.Status.OPEN)


# --- Requirement: Validación de período cerrado antes de escribir ---


def test_fecha_sin_periodo_es_operable():
    """Scenario: Fecha en mes sin período registrado (implícita-abierta) -> operable."""
    assert get_period(2026, 4) is None
    assert is_period_closed(date(2026, 4, 15)) is False
    # No levanta.
    assert_date_operable(date(2026, 4, 15))


def test_fecha_en_periodo_abierto_es_operable():
    """Scenario: Fecha en período abierto -> operable."""
    _open(2026, 6)
    assert is_period_closed(date(2026, 6, 30)) is False
    assert_date_operable(date(2026, 6, 30))


def test_crear_con_fecha_en_periodo_cerrado_rechaza_400_non_field_errors():
    """Scenario: Crear documento con fecha en período cerrado -> 400 non_field_errors."""
    _closed(2026, 3)
    with pytest.raises(ValidationError) as excinfo:
        assert_date_operable(date(2026, 3, 10))

    # El contrato de errores mapea el ValidationError a {"non_field_errors": [...]} / 400.
    response = custom_exception_handler(excinfo.value, {})
    assert response.status_code == 400
    assert response.data == {"non_field_errors": [CLOSED_PERIOD_MESSAGE]}


def test_modificar_documento_con_fecha_en_periodo_cerrado_bloqueada():
    """Scenario: Modificar un documento cuya fecha está en período cerrado -> bloqueada."""
    _closed(2026, 2)
    # La fecha actual del documento cae en el período cerrado: la modificación se rechaza.
    with pytest.raises(ValidationError) as excinfo:
        assert_date_operable(date(2026, 2, 20))
    assert excinfo.value.detail == [CLOSED_PERIOD_MESSAGE]


def test_mover_fecha_hacia_periodo_cerrado_bloqueada():
    """Scenario: Mover la fecha de un documento hacia un período cerrado -> bloqueada."""
    _open(2026, 7)  # período origen abierto
    _closed(2026, 1)  # período destino cerrado
    # La fecha origen es operable; el destino no.
    assert_date_operable(date(2026, 7, 5))
    with pytest.raises(ValidationError) as excinfo:
        assert_date_operable(date(2026, 1, 5))
    assert excinfo.value.detail == [CLOSED_PERIOD_MESSAGE]
