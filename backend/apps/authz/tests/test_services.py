"""Tests de la lógica de autorización y del seed (F2)."""

import pytest

from apps.authz import services
from apps.authz.catalog import SYSTEM_PROFILES
from apps.authz.models import Profile

# --- Resolución de permisos (pura) -------------------------------------------


def test_resolve_permission_permitido():
    profile = Profile(permissions={"access-control": ["read", "create"]})
    assert services.resolve_permission(profile, "access-control", "read") is True


def test_resolve_permission_denegado():
    profile = Profile(permissions={"access-control": ["read"]})
    assert services.resolve_permission(profile, "access-control", "create") is False


def test_resolve_permission_sin_perfil_es_falso():
    assert services.resolve_permission(None, "access-control", "read") is False


def test_visible_fields_for_devuelve_conjunto():
    profile = Profile(visible_sensitive_fields=["intake.cost"])
    assert services.visible_fields_for(profile) == {"intake.cost"}


def test_visible_fields_for_sin_perfil_vacio():
    assert services.visible_fields_for(None) == set()


# --- Capacidad de auto-aprobación --------------------------------------------


@pytest.mark.django_db
def test_perfil_jefe_tiene_auto_aprobacion_habilitada():
    assert Profile.objects.get(name="Jefe").auto_approval is True


@pytest.mark.django_db
def test_perfil_usuario_tiene_auto_aprobacion_deshabilitada():
    assert Profile.objects.get(name="Usuario").auto_approval is False


# --- Perfiles semilla --------------------------------------------------------


@pytest.mark.django_db
def test_perfiles_semilla_disponibles():
    names = set(Profile.objects.values_list("name", flat=True))
    assert {"Jefe", "Supervisor", "Responsable de ruta", "Usuario"} <= names


@pytest.mark.django_db
def test_seed_es_idempotente():
    antes = Profile.objects.count()

    services.seed_system_profiles()

    assert Profile.objects.count() == antes == len(SYSTEM_PROFILES)
