"""Tests de la API de access-control (F2) — cubre los Scenarios del spec.

crear perfil; nombre duplicado (400); permiso fuera de catálogo (400); asignación
(éxito); perfil inexistente (404); usuario inexistente (404); asignar sin permiso (403);
identidad con perfil; acción permitida/denegada (403).
"""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.authz.models import Profile

PASSWORD = "Str0ng-Pass!2024"  # noqa: S105 — credencial de prueba, no secreto real


def _user(role: Role, profile_name: str) -> User:
    user = User.objects.create_user(username=f"u_{role}", password=PASSWORD, role=role)
    user.profile = Profile.objects.get(name=profile_name)
    user.save(update_fields=["profile"])
    return user


@pytest.fixture
def jefe(db):
    return _user(Role.JEFE, "Jefe")


@pytest.fixture
def supervisor(db):
    return _user(Role.SUPERVISOR, "Supervisor")


@pytest.fixture
def usuario(db):
    return _user(Role.USUARIO, "Usuario")


@pytest.fixture
def client():
    return APIClient()


# --- Perfil de permisos ------------------------------------------------------


def test_jefe_crea_perfil_con_permisos_validos(client, jefe):
    client.force_authenticate(jefe)

    response = client.post(
        "/authz/profiles",
        {"name": "Auditor", "permissions": {"access-control": ["read"]}},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["name"] == "Auditor"
    assert Profile.objects.filter(name="Auditor").exists()


def test_crear_perfil_nombre_duplicado_400_en_campo(client, jefe):
    client.force_authenticate(jefe)

    response = client.post("/authz/profiles", {"name": "Jefe"}, format="json")

    assert response.status_code == 400
    assert "name" in response.data


def test_crear_perfil_permiso_fuera_de_catalogo_400(client, jefe):
    client.force_authenticate(jefe)

    response = client.post(
        "/authz/profiles",
        {"name": "Raro", "permissions": {"inexistente": ["read"]}},
        format="json",
    )

    assert response.status_code == 400
    assert "permissions" in response.data


# --- Asignación de perfil a usuario ------------------------------------------


def test_jefe_asigna_perfil_a_usuario(client, jefe, usuario):
    client.force_authenticate(jefe)
    supervisor_profile = Profile.objects.get(name="Supervisor")

    response = client.post(
        f"/authz/users/{usuario.id}/assign-profile",
        {"profile_id": str(supervisor_profile.id)},
        format="json",
    )

    assert response.status_code == 200
    usuario.refresh_from_db()
    assert usuario.profile_id == supervisor_profile.id
    assert response.data["profile"]["name"] == "Supervisor"


def test_asignar_perfil_inexistente_404(client, jefe, usuario):
    client.force_authenticate(jefe)

    response = client.post(
        f"/authz/users/{usuario.id}/assign-profile",
        {"profile_id": "00000000-0000-0000-0000-000000000000"},
        format="json",
    )

    assert response.status_code == 404
    assert set(response.data.keys()) == {"detail"}


def test_asignar_a_usuario_inexistente_404(client, jefe):
    client.force_authenticate(jefe)
    profile = Profile.objects.get(name="Usuario")

    response = client.post(
        "/authz/users/999999/assign-profile",
        {"profile_id": str(profile.id)},
        format="json",
    )

    assert response.status_code == 404


def test_no_jefe_no_puede_asignar_perfil_403(client, supervisor, usuario):
    client.force_authenticate(supervisor)
    profile = Profile.objects.get(name="Usuario")

    response = client.post(
        f"/authz/users/{usuario.id}/assign-profile",
        {"profile_id": str(profile.id)},
        format="json",
    )

    assert response.status_code == 403
    assert set(response.data.keys()) == {"detail"}
    usuario.refresh_from_db()
    assert usuario.profile.name == "Usuario"  # sin cambios


def test_identidad_incluye_el_perfil(client, jefe):
    client.force_authenticate(jefe)

    response = client.get("/auth/me")

    assert response.status_code == 200
    assert response.data["profile"]["name"] == "Jefe"
    assert response.data["role"] == Role.JEFE


# --- Autorización por módulo y acción ----------------------------------------


def test_accion_permitida_por_el_perfil(client, supervisor):
    # El perfil Supervisor tiene access-control:read -> puede listar perfiles.
    client.force_authenticate(supervisor)

    response = client.get("/authz/profiles")

    assert response.status_code == 200
    assert len(response.data) >= 4  # los cuatro perfiles semilla


def test_accion_denegada_por_el_perfil_403(client, usuario):
    # El perfil Usuario no tiene access-control:read -> 403 genérico.
    client.force_authenticate(usuario)

    response = client.get("/authz/profiles")

    assert response.status_code == 403
    assert set(response.data.keys()) == {"detail"}


def test_crear_perfil_sin_permiso_de_creacion_403(client, supervisor):
    # Supervisor tiene read pero no create.
    client.force_authenticate(supervisor)

    response = client.post("/authz/profiles", {"name": "X"}, format="json")

    assert response.status_code == 403
    assert not Profile.objects.filter(name="X").exists()
