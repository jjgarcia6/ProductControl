"""Tests del mecanismo de reglas de auditoría (add-audit-rules, F10).

Cubre `record_field_changes`, `to_audit_str`, el vocabulario `AuditAction` y la
compatibilidad del retrofit del evento grueso (`@audit` con miembro del enum).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.common import audit_rules
from apps.common.audit import audit, record_field_changes, to_audit_str
from apps.common.audit_rules import AuditAction, is_audited
from apps.common.models import AuditLog

User = get_user_model()

ENTITY = "TestDoc"


@pytest.fixture
def audited_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """Registra `weight` y `cost` como auditables para `TestDoc` durante el test."""
    monkeypatch.setitem(audit_rules.AUDITED_FIELDS, ENTITY, frozenset({"weight", "cost"}))


# --- Vocabulario de acciones ------------------------------------------------


def test_correction_se_distingue_de_update():
    assert AuditAction.CORRECTION.value == "CORRECTION"
    assert AuditAction.UPDATE.value == "UPDATE"
    assert AuditAction.CORRECTION.value != AuditAction.UPDATE.value


@pytest.mark.django_db
def test_retrofit_preserva_valor_persistido():
    """El evento grueso con `AuditAction.UPDATE` persiste el literal `"UPDATE"`."""
    user = User.objects.create_user(username="op", password="x")  # noqa: S106

    @audit(action=AuditAction.UPDATE, entity="User")
    def touch(*, user):
        return user

    touch(user=user)

    log = AuditLog.objects.get()
    assert log.action == "UPDATE"
    assert isinstance(log.action, str)
    assert log.field == ""
    assert log.old_value == ""
    assert log.new_value == ""


# --- Registro declarativo ---------------------------------------------------


def test_is_audited_consulta_el_registro(audited_fields):
    assert is_audited(ENTITY, "weight") is True
    assert is_audited(ENTITY, "note") is False
    assert is_audited("Desconocida", "weight") is False


# --- record_field_changes ---------------------------------------------------


@pytest.mark.django_db
def test_una_fila_por_campo_corregido(audited_fields):
    user = User.objects.create_user(username="op", password="x")  # noqa: S106

    created = record_field_changes(
        user=user,
        entity=ENTITY,
        object_id=1,
        before={"weight": Decimal("10.00")},
        after={"weight": Decimal("12.50")},
    )

    assert len(created) == 1
    log = AuditLog.objects.get()
    assert log.action == AuditAction.CORRECTION
    assert log.field == "weight"
    assert log.old_value == "10.00"
    assert log.new_value == "12.50"
    assert log.user == user
    assert log.object_id == "1"


@pytest.mark.django_db
def test_multiples_campos_multiples_filas(audited_fields):
    created = record_field_changes(
        user=None,
        entity=ENTITY,
        object_id=7,
        before={"weight": Decimal("10"), "cost": Decimal("1")},
        after={"weight": Decimal("11"), "cost": Decimal("2")},
    )

    assert len(created) == 2
    assert AuditLog.objects.count() == 2
    assert set(AuditLog.objects.values_list("field", flat=True)) == {"weight", "cost"}


@pytest.mark.django_db
def test_campo_no_auditable_no_genera_fila(audited_fields):
    created = record_field_changes(
        user=None,
        entity=ENTITY,
        object_id=1,
        before={"note": "a"},
        after={"note": "b"},  # `note` no está en AUDITED_FIELDS
    )

    assert created == []
    assert AuditLog.objects.count() == 0


@pytest.mark.django_db
def test_sin_cambio_real_no_genera_fila(audited_fields):
    created = record_field_changes(
        user=None,
        entity=ENTITY,
        object_id=1,
        before={"weight": Decimal("12.50")},
        after={"weight": Decimal("12.50")},
    )

    assert created == []
    assert AuditLog.objects.count() == 0


@pytest.mark.django_db
def test_valor_nulo_a_no_nulo_genera_fila_con_vacio(audited_fields):
    created = record_field_changes(
        user=None,
        entity=ENTITY,
        object_id=1,
        before={"weight": None},
        after={"weight": Decimal("5")},
    )

    assert len(created) == 1
    log = AuditLog.objects.get()
    assert log.old_value == ""
    assert log.new_value == "5"


@pytest.mark.django_db
def test_accion_personalizada_se_respeta(audited_fields):
    record_field_changes(
        user=None,
        entity=ENTITY,
        object_id=1,
        before={"weight": Decimal("1")},
        after={"weight": Decimal("2")},
        action=AuditAction.UPDATE,
    )

    assert AuditLog.objects.get().action == "UPDATE"


# --- to_audit_str -----------------------------------------------------------


def test_to_audit_str_none_es_cadena_vacia():
    assert to_audit_str(None) == ""


def test_to_audit_str_decimal_notacion_simple():
    assert to_audit_str(Decimal("12.50")) == "12.50"
    # sin notación científica ni exponente
    assert to_audit_str(Decimal("1E+2")) == "100"


def test_to_audit_str_fecha_iso():
    assert to_audit_str(date(2026, 7, 2)) == "2026-07-02"


@pytest.mark.django_db
def test_to_audit_str_fk_es_pk():
    user = User.objects.create_user(username="op", password="x")  # noqa: S106
    assert to_audit_str(user) == str(user.pk)


def test_to_audit_str_resto_es_str():
    assert to_audit_str(42) == "42"
    assert to_audit_str("abc") == "abc"
