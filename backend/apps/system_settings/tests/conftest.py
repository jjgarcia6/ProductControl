"""Fixtures de los tests de la configuración global (F8)."""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.authz.catalog import MODULE_SYSTEM_SETTINGS
from apps.authz.models import Profile

PASSWORD = "Str0ng-Pass!2024"  # noqa: S105 — credencial de prueba, no secreto real


@pytest.fixture
def jefe(db):
    """Usuario con perfil que permite leer y editar la configuración (read + update)."""
    profile = Profile.objects.create(
        name="Jefe F8",
        permissions={MODULE_SYSTEM_SETTINGS: ["read", "update"]},
    )
    user = User.objects.create_user(username="jefe", password=PASSWORD, role=Role.JEFE)
    user.profile = profile
    user.save(update_fields=["profile"])
    return user


@pytest.fixture
def supervisor(db):
    """Usuario con perfil que solo permite leer la configuración (read, sin update)."""
    profile = Profile.objects.create(
        name="Supervisor F8",
        permissions={MODULE_SYSTEM_SETTINGS: ["read"]},
    )
    user = User.objects.create_user(username="supervisor", password=PASSWORD, role=Role.SUPERVISOR)
    user.profile = profile
    user.save(update_fields=["profile"])
    return user


@pytest.fixture
def sin_permiso(db):
    """Usuario cuyo perfil NO permite leer ni editar la configuración."""
    profile = Profile.objects.create(name="Sin Config F8", permissions={})
    user = User.objects.create_user(username="otro", password=PASSWORD, role=Role.USUARIO)
    user.profile = profile
    user.save(update_fields=["profile"])
    return user


@pytest.fixture
def client():
    return APIClient()
