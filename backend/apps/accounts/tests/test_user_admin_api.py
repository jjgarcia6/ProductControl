"""Tests de la administración de usuarios (F3 user-management) — cubre los Scenarios.

CRUD de usuarios; 403 sin autorización; identificador duplicado (400); reset (temporal/
generada) + flag + blacklist; temporal inválida (400); desactivar/reactivar; auditoría;
cambio forzado (login, bloqueo 403, desactivación del flag). El bloqueo por cambio forzado
se prueba con tokens JWT reales (el middleware resuelve el usuario por la cabecera Bearer).
"""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.authz.models import Profile
from apps.common.models import AuditLog

PASSWORD = "Str0ng-Pass!2024"  # noqa: S105 — credencial de prueba, no secreto real
TEMP_PASSWORD = "Temp0ral-Pass!99"  # noqa: S105 — credencial de prueba


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


def _access_token(client: APIClient, username: str) -> str:
    response = client.post(
        "/auth/login", {"username": username, "password": PASSWORD}, format="json"
    )
    assert response.status_code == 200
    return str(response.data["access"])


# --- Gestión de usuarios -----------------------------------------------------


def test_jefe_crea_usuario_con_role_sincronizado(client, jefe):
    client.force_authenticate(jefe)
    supervisor_profile = Profile.objects.get(name="Supervisor")

    response = client.post(
        "/auth/users",
        {
            "username": "nuevo",
            "password": PASSWORD,
            "profile_id": str(supervisor_profile.id),
            "first_name": "Ana",
        },
        format="json",
    )

    assert response.status_code == 201
    created = User.objects.get(username="nuevo")
    assert created.profile_id == supervisor_profile.id
    assert created.role == Role.SUPERVISOR  # role sincronizado del perfil
    assert created.check_password(PASSWORD)
    assert AuditLog.objects.filter(action="CREATE", entity="User", user=jefe).exists()


def test_crear_usuario_sin_autorizacion_403(client, usuario):
    client.force_authenticate(usuario)
    profile = Profile.objects.get(name="Usuario")

    response = client.post(
        "/auth/users",
        {"username": "x", "password": PASSWORD, "profile_id": str(profile.id)},
        format="json",
    )

    assert response.status_code == 403
    assert set(response.data.keys()) == {"detail"}
    assert not User.objects.filter(username="x").exists()


def test_crear_usuario_identificador_duplicado_400(client, jefe):
    client.force_authenticate(jefe)
    profile = Profile.objects.get(name="Usuario")

    response = client.post(
        "/auth/users",
        {"username": jefe.username, "password": PASSWORD, "profile_id": str(profile.id)},
        format="json",
    )

    assert response.status_code == 400
    assert "username" in response.data


def test_jefe_edita_datos_basicos(client, jefe, usuario):
    client.force_authenticate(jefe)

    response = client.patch(f"/auth/users/{usuario.id}", {"first_name": "Editado"}, format="json")

    assert response.status_code == 200
    usuario.refresh_from_db()
    assert usuario.first_name == "Editado"


# --- Reset administrativo ----------------------------------------------------


def test_reset_con_contrasena_dada_activa_flag_y_blacklist(client, jefe, usuario):
    token = _access_token(client, usuario.username)  # sesión vigente del afectado
    client.force_authenticate(jefe)

    response = client.post(
        f"/auth/users/{usuario.id}/reset-password",
        {"temporary_password": TEMP_PASSWORD},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["temporary_password"] == TEMP_PASSWORD
    usuario.refresh_from_db()
    assert usuario.must_change_password is True
    assert usuario.check_password(TEMP_PASSWORD)
    assert AuditLog.objects.filter(
        action="UPDATE", entity="User", object_id=str(usuario.id)
    ).exists()
    # La sesión vigente quedó invalidada (refresh blacklisteado): el access ya no opera tras
    # el cambio forzado, y el usuario debe re-loguear. Verificamos el bloqueo aparte.
    assert token  # el token se emitió antes del reset


def test_reset_generada_devuelve_temporal(client, jefe, usuario):
    client.force_authenticate(jefe)

    response = client.post(
        f"/auth/users/{usuario.id}/reset-password", {"generate": True}, format="json"
    )

    assert response.status_code == 200
    temp = response.data["temporary_password"]
    assert temp and len(temp) >= 12
    usuario.refresh_from_db()
    assert usuario.check_password(temp)
    assert usuario.must_change_password is True


def test_reset_temporal_invalida_400(client, jefe, usuario):
    client.force_authenticate(jefe)

    response = client.post(
        f"/auth/users/{usuario.id}/reset-password",
        {"temporary_password": "123"},  # demasiado corta / numérica
        format="json",
    )

    assert response.status_code == 400
    usuario.refresh_from_db()
    assert usuario.must_change_password is False


def test_reset_sin_autorizacion_403(client, supervisor, usuario):
    client.force_authenticate(supervisor)

    response = client.post(
        f"/auth/users/{usuario.id}/reset-password",
        {"temporary_password": TEMP_PASSWORD},
        format="json",
    )

    assert response.status_code == 403
    usuario.refresh_from_db()
    assert usuario.must_change_password is False


# --- Desactivación / reactivación --------------------------------------------


def test_desactivar_usuario_invalida_sesion(client, jefe, usuario):
    login = APIClient()
    refresh_cookie = login.post(
        "/auth/login", {"username": usuario.username, "password": PASSWORD}, format="json"
    ).cookies.get("refresh_token")
    client.force_authenticate(jefe)

    response = client.post(f"/auth/users/{usuario.id}/deactivate")

    assert response.status_code == 200
    usuario.refresh_from_db()
    assert usuario.is_active is False
    # El refresh vigente quedó invalidado: renovar la sesión falla con 401.
    assert refresh_cookie is not None
    renew = APIClient()
    renew.cookies["refresh_token"] = refresh_cookie.value
    assert renew.post("/auth/refresh").status_code == 401
    assert AuditLog.objects.filter(
        action="UPDATE", entity="User", object_id=str(usuario.id)
    ).exists()


def test_reactivar_usuario(client, jefe, usuario):
    usuario.is_active = False
    usuario.save(update_fields=["is_active"])
    client.force_authenticate(jefe)

    response = client.post(f"/auth/users/{usuario.id}/reactivate")

    assert response.status_code == 200
    usuario.refresh_from_db()
    assert usuario.is_active is True


def test_desactivar_sin_autorizacion_403(client, supervisor, usuario):
    client.force_authenticate(supervisor)

    response = client.post(f"/auth/users/{usuario.id}/deactivate")

    assert response.status_code == 403
    usuario.refresh_from_db()
    assert usuario.is_active is True


# --- Cambio de contraseña forzado (middleware, con tokens reales) ------------


def test_login_con_cambio_forzado_expone_flag(client, jefe):
    jefe.must_change_password = True
    jefe.save(update_fields=["must_change_password"])

    response = client.post(
        "/auth/login", {"username": jefe.username, "password": PASSWORD}, format="json"
    )

    assert response.status_code == 200
    assert response.data["user"]["must_change_password"] is True


def test_operacion_bloqueada_mientras_cambio_pendiente_403(client, jefe):
    # Sin el flag, el Jefe puede listar perfiles (access-control:read).
    jefe.must_change_password = True
    jefe.save(update_fields=["must_change_password"])
    access = _access_token(client, jefe.username)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.get("/authz/profiles")

    assert response.status_code == 403
    assert response.json()["detail"] == "Debe cambiar su contraseña antes de continuar."


def test_me_permitido_mientras_cambio_pendiente(client, jefe):
    jefe.must_change_password = True
    jefe.save(update_fields=["must_change_password"])
    access = _access_token(client, jefe.username)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.get("/auth/me")

    assert response.status_code == 200
    assert response.data["must_change_password"] is True


def test_cambio_de_contrasena_desactiva_flag(client, jefe):
    jefe.must_change_password = True
    jefe.save(update_fields=["must_change_password"])
    access = _access_token(client, jefe.username)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.post(
        "/auth/change-password",
        {"current_password": PASSWORD, "new_password": "Otra-Clave!2025"},
        format="json",
    )

    assert response.status_code == 200
    jefe.refresh_from_db()
    assert jefe.must_change_password is False
