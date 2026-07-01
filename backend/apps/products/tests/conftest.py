"""Fixtures de los tests del maestro de inventario (F5)."""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.authz.catalog import MODULE_PRODUCTS
from apps.authz.models import Profile

PASSWORD = "Str0ng-Pass!2024"  # noqa: S105 — credencial de prueba, no secreto real


@pytest.fixture
def gestor(db):
    """Usuario con un perfil que permite gestionar productos (read/create/update)."""
    profile = Profile.objects.create(
        name="Gestor Productos",
        permissions={MODULE_PRODUCTS: ["read", "create", "update"]},
    )
    user = User.objects.create_user(username="gestor", password=PASSWORD, role=Role.SUPERVISOR)
    user.profile = profile
    user.save(update_fields=["profile"])
    return user


@pytest.fixture
def sin_permiso(db):
    """Usuario cuyo perfil NO permite gestionar productos."""
    profile = Profile.objects.create(name="Sin Productos", permissions={})
    user = User.objects.create_user(username="otro", password=PASSWORD, role=Role.USUARIO)
    user.profile = profile
    user.save(update_fields=["profile"])
    return user


@pytest.fixture
def client():
    return APIClient()
