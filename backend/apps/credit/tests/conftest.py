"""Fixtures de los tests de términos de crédito (F4)."""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.authz.catalog import MODULE_DIRECTORY
from apps.authz.models import Profile
from apps.directory.models import Ficha

PASSWORD = "Str0ng-Pass!2024"  # noqa: S105 — credencial de prueba, no secreto real


@pytest.fixture
def gestor(db):
    profile = Profile.objects.create(
        name="Gestor Directorio",
        permissions={MODULE_DIRECTORY: ["read", "create", "update"]},
    )
    user = User.objects.create_user(username="gestor", password=PASSWORD, role=Role.SUPERVISOR)
    user.profile = profile
    user.save(update_fields=["profile"])
    return user


@pytest.fixture
def sin_permiso(db):
    profile = Profile.objects.create(name="Sin Directorio", permissions={})
    user = User.objects.create_user(username="otro", password=PASSWORD, role=Role.USUARIO)
    user.profile = profile
    user.save(update_fields=["profile"])
    return user


@pytest.fixture
def ficha_cliente(db):
    return Ficha.objects.create(
        name="Cliente Norte",
        identification_type="CEDULA",
        identification_number="1710034065",
        roles=["CLIENTE"],
    )


@pytest.fixture
def ficha_proveedor(db):
    return Ficha.objects.create(
        name="Proveedor Sur",
        identification_type="RUC",
        identification_number="1790011674001",
        roles=["PROVEEDOR"],
    )


@pytest.fixture
def client():
    return APIClient()
