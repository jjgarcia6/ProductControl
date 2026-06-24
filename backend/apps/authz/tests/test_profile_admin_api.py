"""Tests de la administración de perfiles (F3) y la extensión de assign-profile.

Editar permisos (200); baja sin usuarios (204); baja en uso (409); sin autorización (403);
y la asignación de perfil extendida: sincroniza el `role` e invalida la sesión (blacklist).
"""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.authz.models import Profile
from apps.common.models import AuditLog

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


# --- Administración de perfiles ----------------------------------------------


def test_jefe_edita_permisos_de_un_perfil(client, jefe):
    client.force_authenticate(jefe)
    profile = Profile.objects.create(name="Auditor", permissions={})

    response = client.patch(
        f"/authz/profiles/{profile.id}",
        {"permissions": {"access-control": ["read"]}},
        format="json",
    )

    assert response.status_code == 200
    profile.refresh_from_db()
    assert profile.permissions == {"access-control": ["read"]}
    assert AuditLog.objects.filter(
        action="UPDATE", entity="Profile", object_id=str(profile.id)
    ).exists()


def test_editar_permiso_fuera_de_catalogo_400(client, jefe):
    client.force_authenticate(jefe)
    profile = Profile.objects.create(name="Auditor", permissions={})

    response = client.patch(
        f"/authz/profiles/{profile.id}",
        {"permissions": {"inexistente": ["read"]}},
        format="json",
    )

    assert response.status_code == 400
    assert "permissions" in response.data


def test_jefe_da_de_baja_perfil_sin_usuarios(client, jefe):
    client.force_authenticate(jefe)
    profile = Profile.objects.create(name="Auditor", permissions={})

    response = client.delete(f"/authz/profiles/{profile.id}")

    assert response.status_code == 204
    # Soft delete: deja de aparecer en el manager por defecto, la fila sigue.
    assert not Profile.objects.filter(pk=profile.id).exists()
    assert Profile.all_objects.filter(pk=profile.id).exists()
    assert AuditLog.objects.filter(action="SOFT_DELETE", entity="Profile").exists()


def test_baja_de_perfil_en_uso_409(client, jefe, usuario):
    client.force_authenticate(jefe)
    profile = Profile.objects.get(name="Usuario")  # 'usuario' lo tiene asignado

    response = client.delete(f"/authz/profiles/{profile.id}")

    assert response.status_code == 409
    assert set(response.data.keys()) == {"detail"}
    assert Profile.objects.filter(pk=profile.id).exists()  # sigue vivo


def test_administrar_perfiles_sin_autorizacion_403(client, supervisor):
    client.force_authenticate(supervisor)
    profile = Profile.objects.get(name="Usuario")

    edit = client.patch(f"/authz/profiles/{profile.id}", {"permissions": {}}, format="json")
    delete = client.delete(f"/authz/profiles/{profile.id}")

    assert edit.status_code == 403
    assert delete.status_code == 403


# --- Asignación de perfil extendida (sync role + blacklist) ------------------


def test_cambiar_perfil_sincroniza_rol_e_invalida_sesion(client, jefe, usuario):
    login = APIClient()
    refresh_cookie = login.post(
        "/auth/login", {"username": usuario.username, "password": PASSWORD}, format="json"
    ).cookies.get("refresh_token")
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
    assert usuario.role == Role.SUPERVISOR  # role sincronizado
    # Refresh vigente invalidado: renovar falla con 401.
    assert refresh_cookie is not None
    renew = APIClient()
    renew.cookies["refresh_token"] = refresh_cookie.value
    assert renew.post("/auth/refresh").status_code == 401
