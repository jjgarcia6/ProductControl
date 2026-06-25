"""Fixtures de los tests del Directorio (F4)."""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.authz.catalog import MODULE_DIRECTORY
from apps.authz.models import Profile

PASSWORD = "Str0ng-Pass!2024"  # noqa: S105 — credencial de prueba, no secreto real


@pytest.fixture
def gestor(db):
    """Usuario con un perfil que permite gestionar el Directorio (read/create/update)."""
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
    """Usuario cuyo perfil NO permite gestionar el Directorio."""
    profile = Profile.objects.create(name="Sin Directorio", permissions={})
    user = User.objects.create_user(username="otro", password=PASSWORD, role=Role.USUARIO)
    user.profile = profile
    user.save(update_fields=["profile"])
    return user


@pytest.fixture
def client():
    return APIClient()
