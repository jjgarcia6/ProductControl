"""Fixtures de los tests del maestro de precios (F6)."""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.authz.catalog import MODULE_PRICING
from apps.authz.models import Profile
from apps.products.models import Category, IntakeType, Product, UnitOfMeasure

PASSWORD = "Str0ng-Pass!2024"  # noqa: S105 — credencial de prueba, no secreto real


@pytest.fixture
def gestor(db):
    """Usuario con un perfil que permite gestionar precios (read/create/update)."""
    profile = Profile.objects.create(
        name="Gestor Precios",
        permissions={MODULE_PRICING: ["read", "create", "update"]},
    )
    user = User.objects.create_user(username="gestor", password=PASSWORD, role=Role.SUPERVISOR)
    user.profile = profile
    user.save(update_fields=["profile"])
    return user


@pytest.fixture
def sin_permiso(db):
    """Usuario cuyo perfil NO permite gestionar precios."""
    profile = Profile.objects.create(name="Sin Precios", permissions={})
    user = User.objects.create_user(username="otro", password=PASSWORD, role=Role.USUARIO)
    user.profile = profile
    user.save(update_fields=["profile"])
    return user


@pytest.fixture
def producto(db):
    """Un producto existente para tarifar."""
    unit = UnitOfMeasure.objects.create(
        name="Libras F6", symbol="lbf", conversion_factor=Decimal("1")
    )
    category = Category.objects.create(name="Categoría F6", intake_type=IntakeType.PESO)
    return Product.objects.create(name="Producto F6", category=category, unit_of_measure=unit)


@pytest.fixture
def client():
    return APIClient()
