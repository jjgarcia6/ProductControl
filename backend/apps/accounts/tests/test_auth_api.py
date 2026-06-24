"""Tests de la API de auth (F1) — cubre TODOS los Scenarios del spec.

login válido/inválido/inactivo; refresh válido/rotado/revocado/ausente; logout + refresh
tras logout; me con/sin token; cambio de contraseña correcto/actual-incorrecta/política;
rol en la identidad; rate limit.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.accounts.models import Role

User = get_user_model()

PASSWORD = "Str0ng-Pass!2024"  # noqa: S105 — credencial de prueba, no secreto real
COOKIE = "refresh_token"


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="operador",
        password=PASSWORD,
        first_name="Ana",
        last_name="Pérez",
        role=Role.SUPERVISOR,
    )


@pytest.fixture
def client():
    return APIClient()


def _login(client, username="operador", password=PASSWORD):
    return client.post("/auth/login", {"username": username, "password": password}, format="json")


# --- Autenticación por credenciales -----------------------------------------


def test_login_valido_devuelve_access_y_setea_cookie(client, user):
    response = _login(client)

    assert response.status_code == 200
    assert response.data["access"]
    assert response.data["user"]["username"] == "operador"
    assert response.data["user"]["role"] == Role.SUPERVISOR
    cookie = response.cookies[COOKIE]
    assert cookie["httponly"]
    assert cookie["path"] == "/auth"


def test_login_credenciales_invalidas_401_sin_cookie(client, user):
    response = _login(client, password="incorrecta")

    assert response.status_code == 401
    assert set(response.data.keys()) == {"detail"}
    assert COOKIE not in response.cookies


def test_login_usuario_inactivo_401_sin_tokens(client, user):
    user.is_active = False
    user.save(update_fields=["is_active"])

    response = _login(client)

    assert response.status_code == 401
    assert set(response.data.keys()) == {"detail"}
    assert COOKIE not in response.cookies


# --- Renovación de access token ---------------------------------------------


def test_refresh_valido_rota_y_devuelve_nuevo_access(client, user):
    _login(client)

    response = client.post("/auth/refresh", format="json")

    assert response.status_code == 200
    assert response.data["access"]
    assert response.cookies[COOKIE].value  # cookie rotada


def test_refresh_con_token_rotado_anterior_es_revocado(client, user):
    _login(client)
    old_refresh = client.cookies[COOKIE].value
    client.post("/auth/refresh", format="json")  # rota: el anterior queda en blacklist

    client.cookies[COOKIE] = old_refresh
    response = client.post("/auth/refresh", format="json")

    assert response.status_code == 401
    assert set(response.data.keys()) == {"detail"}


def test_refresh_sin_cookie_401(client, user):
    response = client.post("/auth/refresh", format="json")

    assert response.status_code == 401
    assert set(response.data.keys()) == {"detail"}


# --- Cierre de sesión --------------------------------------------------------


def test_logout_invalida_refresh_y_limpia_cookie(client, user):
    login = _login(client)
    access = login.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.post("/auth/logout", format="json")

    assert response.status_code == 200
    # La cookie se limpia (max-age 0 / expirada).
    assert client.cookies[COOKIE].value == ""


def test_refresh_tras_logout_401(client, user):
    login = _login(client)
    access = login.data["access"]
    refresh = client.cookies[COOKIE].value
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    client.post("/auth/logout", format="json")

    client.credentials()
    client.cookies[COOKIE] = refresh
    response = client.post("/auth/refresh", format="json")

    assert response.status_code == 401


# --- Identidad del usuario autenticado --------------------------------------


def test_me_con_access_valido_devuelve_identidad(client, user):
    access = _login(client).data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.get("/auth/me")

    assert response.status_code == 200
    assert response.data["username"] == "operador"
    assert response.data["role"] == Role.SUPERVISOR
    assert response.data["id"] == user.id


def test_me_sin_token_401(client, user):
    response = client.get("/auth/me")

    assert response.status_code == 401
    assert set(response.data.keys()) == {"detail"}


# --- Roles del sistema -------------------------------------------------------


def test_identidad_expone_el_rol(client, user):
    access = _login(client).data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.get("/auth/me")

    assert response.data["role"] == Role.SUPERVISOR
    assert str(user) == "operador"


# --- Cambio de contraseña propio --------------------------------------------


def test_change_password_correcto_invalida_sesiones(client, user):
    access = _login(client).data["access"]
    refresh = client.cookies[COOKIE].value
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.post(
        "/auth/change-password",
        {"current_password": PASSWORD, "new_password": "Otr0-Cl4ve!2025"},
        format="json",
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.check_password("Otr0-Cl4ve!2025")

    # Los refresh previos quedaron invalidados.
    client.credentials()
    client.cookies[COOKIE] = refresh
    assert client.post("/auth/refresh", format="json").status_code == 401


def test_change_password_actual_incorrecta_400_en_campo(client, user):
    access = _login(client).data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.post(
        "/auth/change-password",
        {"current_password": "no-es-la-actual", "new_password": "Otr0-Cl4ve!2025"},
        format="json",
    )

    assert response.status_code == 400
    assert "current_password" in response.data


def test_change_password_nueva_no_cumple_politica_400_en_campo(client, user):
    access = _login(client).data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.post(
        "/auth/change-password",
        {"current_password": PASSWORD, "new_password": "123"},
        format="json",
    )

    assert response.status_code == 400
    assert "new_password" in response.data


# --- Limitación de intentos de login ----------------------------------------


def test_rate_limit_de_login_devuelve_429(client, user):
    # 5/m permitidos; el 6º intento (misma IP) excede el umbral.
    for _ in range(5):
        _login(client, password="incorrecta")
    last = _login(client, password="incorrecta")

    assert last.status_code == 429
    assert set(last.data.keys()) == {"detail"}
