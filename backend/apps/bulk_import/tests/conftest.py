"""Fixtures de los tests de la importación masiva (F7)."""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.authz.catalog import MODULE_BULK_IMPORT
from apps.authz.models import Profile
from apps.products.models import Category, IntakeType, UnitOfMeasure

PASSWORD = "Str0ng-Pass!2024"  # noqa: S105 — credencial de prueba, no secreto real


@pytest.fixture
def importer(db):
    """Usuario con un perfil que permite importar (módulo bulk-import, acción create)."""
    profile = Profile.objects.create(
        name="Importador", permissions={MODULE_BULK_IMPORT: ["create"]}
    )
    user = User.objects.create_user(username="importador", password=PASSWORD, role=Role.SUPERVISOR)
    user.profile = profile
    user.save(update_fields=["profile"])
    return user


@pytest.fixture
def sin_permiso(db):
    """Usuario cuyo perfil NO incluye el módulo bulk-import."""
    profile = Profile.objects.create(name="Sin Import", permissions={})
    user = User.objects.create_user(username="otro", password=PASSWORD, role=Role.USUARIO)
    user.profile = profile
    user.save(update_fields=["profile"])
    return user


@pytest.fixture
def catalogo(db):
    """Categoría y unidad base a las que referencian las filas de producto importadas."""
    category = Category.objects.create(name="Lácteos", intake_type=IntakeType.GAVETA)
    unit = UnitOfMeasure.objects.create(name="Unidad", symbol="u", conversion_factor=Decimal("1"))
    return category, unit


@pytest.fixture
def client():
    return APIClient()
