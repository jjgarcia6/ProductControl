"""Test del mecanismo de campos invisibles (F2).

Verifica que `SensitiveFieldsMixin` OMITE del JSON el campo sensible (clave ausente)
para un perfil sin acceso, y lo incluye para uno con acceso. No basta read-only.
"""

from types import SimpleNamespace
from typing import Any

import pytest
from rest_framework import serializers

from apps.authz.models import Profile
from apps.authz.serializers import SensitiveFieldsMixin


class _DocSerializer(SensitiveFieldsMixin, serializers.Serializer[Any]):
    name = serializers.CharField()
    cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    sensitive_fields = {"cost": "intake.cost"}


def _serialize_for(profile: Profile | None) -> dict[str, Any]:
    instance = SimpleNamespace(name="Pollo", cost="12.50")
    request = SimpleNamespace(user=SimpleNamespace(profile=profile))
    return _DocSerializer(instance, context={"request": request}).data


@pytest.mark.django_db
def test_campo_sensible_omitido_para_perfil_sin_acceso():
    profile = Profile.objects.create(name="SinCosto", visible_sensitive_fields=[])

    data = _serialize_for(profile)

    assert "name" in data
    assert "cost" not in data  # clave ausente, no enmascarada


@pytest.mark.django_db
def test_campo_sensible_visible_para_perfil_con_acceso():
    profile = Profile.objects.create(name="ConCosto", visible_sensitive_fields=["intake.cost"])

    data = _serialize_for(profile)

    assert data["cost"] == "12.50"


def test_sin_perfil_el_campo_sensible_se_omite():
    data = _serialize_for(None)

    assert "cost" not in data
