"""Tests de la API del Directorio (F4) — cubre los Scenarios del spec delta.

Identificación válida/inválida(400)/duplicada(409); roles múltiples/sin rol(400); email
inválido(400); estados block/unblock/deactivate/reactivate y exclusión de INACTIVO;
vínculo usuario y duplicado(409); 401/403 sin autorización; auditoría.
"""

import pytest

from apps.accounts.models import Role, User
from apps.common.models import AuditLog
from apps.directory.models import Ficha, FichaStatus

VALID_CEDULA = "1710034065"
PASSWORD = "Str0ng-Pass!2024"  # noqa: S105 — credencial de prueba, no secreto real


def _ficha_payload(**overrides):
    payload = {
        "name": "Distribuidora Andina",
        "identification_type": "CEDULA",
        "identification_number": VALID_CEDULA,
        "email": "ventas@andina.ec",
        "phone": "0991234567",
        "roles": ["CLIENTE"],
    }
    payload.update(overrides)
    return payload


# --- Alta de ficha -----------------------------------------------------------


def test_crea_ficha_con_identificacion_valida(client, gestor):
    client.force_authenticate(gestor)

    response = client.post("/directory/fichas", _ficha_payload(), format="json")

    assert response.status_code == 201
    assert response.data["status"] == FichaStatus.ACTIVO
    assert Ficha.objects.filter(identification_number=VALID_CEDULA).exists()
    assert AuditLog.objects.filter(action="CREATE", entity="Ficha").exists()


def test_crea_ficha_con_digito_verificador_invalido(client, gestor):
    client.force_authenticate(gestor)

    response = client.post(
        "/directory/fichas", _ficha_payload(identification_number="1710034060"), format="json"
    )

    assert response.status_code == 400
    assert "identification_number" in response.data
    assert not Ficha.objects.exists()


def test_crea_ficha_con_numero_duplicado(client, gestor):
    client.force_authenticate(gestor)
    client.post("/directory/fichas", _ficha_payload(), format="json")

    response = client.post("/directory/fichas", _ficha_payload(name="Otra"), format="json")

    assert response.status_code == 409
    assert "detail" in response.data
    assert Ficha.objects.count() == 1


def test_crea_ficha_con_multiples_roles(client, gestor):
    client.force_authenticate(gestor)

    response = client.post(
        "/directory/fichas", _ficha_payload(roles=["CLIENTE", "PROVEEDOR"]), format="json"
    )

    assert response.status_code == 201
    assert set(response.data["roles"]) == {"CLIENTE", "PROVEEDOR"}


def test_crea_ficha_sin_rol(client, gestor):
    client.force_authenticate(gestor)

    response = client.post("/directory/fichas", _ficha_payload(roles=[]), format="json")

    assert response.status_code == 400
    assert "roles" in response.data


def test_crea_ficha_con_email_invalido(client, gestor):
    client.force_authenticate(gestor)

    response = client.post(
        "/directory/fichas", _ficha_payload(email="no-es-un-email"), format="json"
    )

    assert response.status_code == 400
    assert "email" in response.data


# --- Autorización ------------------------------------------------------------


def test_anonimo_no_puede_crear_ficha(client):
    response = client.post("/directory/fichas", _ficha_payload(), format="json")
    assert response.status_code == 401


def test_sin_permiso_no_puede_crear_ficha(client, sin_permiso):
    client.force_authenticate(sin_permiso)

    response = client.post("/directory/fichas", _ficha_payload(), format="json")

    assert response.status_code == 403
    assert not Ficha.objects.exists()


# --- Estados -----------------------------------------------------------------


@pytest.fixture
def ficha(gestor):
    return Ficha.objects.create(
        name="Distribuidora Andina",
        identification_type="CEDULA",
        identification_number=VALID_CEDULA,
        roles=["CLIENTE"],
    )


def test_bloquea_y_desbloquea_ficha(client, gestor, ficha):
    client.force_authenticate(gestor)

    block = client.post(f"/directory/fichas/{ficha.id}/block")
    assert block.status_code == 200
    assert block.data["status"] == FichaStatus.BLOQUEADO
    assert AuditLog.objects.filter(action="STATE_CHANGE", entity="Ficha").exists()

    unblock = client.post(f"/directory/fichas/{ficha.id}/unblock")
    assert unblock.status_code == 200
    assert unblock.data["status"] == FichaStatus.ACTIVO


def test_da_de_baja_y_reactiva_ficha(client, gestor, ficha):
    client.force_authenticate(gestor)

    deactivate = client.post(f"/directory/fichas/{ficha.id}/deactivate")
    assert deactivate.status_code == 200
    assert deactivate.data["status"] == FichaStatus.INACTIVO

    # Excluida de los listados operativos por defecto.
    listing = client.get("/directory/fichas")
    assert all(item["id"] != str(ficha.id) for item in listing.data)

    # Visible con include_inactive.
    listing_all = client.get("/directory/fichas?include_inactive=true")
    assert any(item["id"] == str(ficha.id) for item in listing_all.data)

    reactivate = client.post(f"/directory/fichas/{ficha.id}/reactivate")
    assert reactivate.status_code == 200
    assert reactivate.data["status"] == FichaStatus.ACTIVO


def test_transicion_invalida_es_conflicto(client, gestor, ficha):
    client.force_authenticate(gestor)
    # unblock sobre una ficha ACTIVO no es válido.
    response = client.post(f"/directory/fichas/{ficha.id}/unblock")
    assert response.status_code == 409


def test_numero_reusable_tras_inactivar(client, gestor, ficha):
    client.force_authenticate(gestor)
    client.post(f"/directory/fichas/{ficha.id}/deactivate")

    # Con la primera INACTIVO, el número queda disponible para otra ficha.
    response = client.post("/directory/fichas", _ficha_payload(name="Nueva"), format="json")
    assert response.status_code == 201


def test_sin_permiso_no_puede_cambiar_estado(client, sin_permiso, ficha):
    client.force_authenticate(sin_permiso)
    response = client.post(f"/directory/fichas/{ficha.id}/block")
    assert response.status_code == 403
    ficha.refresh_from_db()
    assert ficha.status == FichaStatus.ACTIVO


# --- Vínculo con usuario -----------------------------------------------------


def test_vincula_ficha_a_usuario(client, gestor, ficha):
    client.force_authenticate(gestor)
    target = User.objects.create_user(username="chofer", password=PASSWORD, role=Role.USUARIO)

    response = client.post(
        f"/directory/fichas/{ficha.id}/link-user", {"user": target.id}, format="json"
    )

    assert response.status_code == 200
    ficha.refresh_from_db()
    assert ficha.user_id == target.id


def test_vincula_usuario_que_ya_tiene_ficha(client, gestor, ficha):
    client.force_authenticate(gestor)
    target = User.objects.create_user(username="chofer", password=PASSWORD, role=Role.USUARIO)
    otra = Ficha.objects.create(
        name="Otra",
        identification_type="CEDULA",
        identification_number="0926687856",
        roles=["CHOFER"],
        user=target,
    )

    response = client.post(
        f"/directory/fichas/{ficha.id}/link-user", {"user": target.id}, format="json"
    )

    assert response.status_code == 409
    assert otra.user_id == target.id
