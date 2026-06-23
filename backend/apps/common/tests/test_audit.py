"""Tests del mecanismo de auditoría (apps.common.audit)."""

import pytest
from django.contrib.auth import get_user_model

from apps.common.audit import audit
from apps.common.models import AuditLog

User = get_user_model()


@pytest.mark.django_db
def test_audit_registra_log_con_usuario_y_objeto():
    user = User.objects.create_user(username="operador", password="x")  # noqa: S106

    @audit(action="create", entity="supplier")
    def create_thing(*, user):
        return user  # objeto con pk

    result = create_thing(user=user)

    assert result == user
    log = AuditLog.objects.get()
    assert log.action == "create"
    assert log.entity == "supplier"
    assert log.user == user
    assert log.object_id == str(user.pk)


@pytest.mark.django_db
def test_audit_sin_usuario_ni_resultado_con_pk():
    @audit(action="noop", entity="thing")
    def do_nothing():
        return None

    do_nothing()

    log = AuditLog.objects.get()
    assert log.user is None
    assert log.object_id == ""
    assert str(log) == "noop thing#"
