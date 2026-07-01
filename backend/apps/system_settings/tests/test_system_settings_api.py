"""Tests de la API de configuración global (F8) — cubre los Scenarios del spec delta.

Singleton: recuperar (200), una sola fila tras re-seed. Toggles: desactivar una base
(+audit), reactivar; ambas en false → 400 en `non_field_errors`. Autorización: Jefe edita
→ 200, Supervisor lee → 200, Supervisor edita → 403, sin sesión → 401. Auditoría:
registra campo/valor anterior/valor nuevo/usuario.
"""

from apps.common.models import AuditLog
from apps.system_settings.models import SystemSettings
from apps.system_settings.services import get_settings

URL = "/system-settings/"


# --- Singleton ---------------------------------------------------------------


def test_recupera_configuracion_global(client, jefe):
    client.force_authenticate(jefe)

    response = client.get(URL)

    assert response.status_code == 200
    assert response.data["costing_nominal_enabled"] is True
    assert response.data["costing_effective_enabled"] is True
    assert "lock" not in response.data  # el centinela nunca se expone


def test_siembra_conserva_una_sola_fila(db):
    # get_settings es idempotente: invocarlo varias veces NO crea filas nuevas.
    first = get_settings()
    second = get_settings()

    assert first.pk == second.pk
    assert SystemSettings.objects.count() == 1


# --- Toggles -----------------------------------------------------------------


def test_jefe_desactiva_solo_la_base_efectiva(client, jefe):
    client.force_authenticate(jefe)

    response = client.patch(URL, {"costing_effective_enabled": False}, format="json")

    assert response.status_code == 200
    assert response.data["costing_effective_enabled"] is False
    assert response.data["costing_nominal_enabled"] is True
    settings = SystemSettings.objects.get()
    assert settings.costing_effective_enabled is False
    assert settings.costing_nominal_enabled is True


def test_jefe_reactiva_la_base_nominal(client, jefe):
    client.force_authenticate(jefe)
    settings = get_settings()
    settings.costing_nominal_enabled = False
    settings.save(update_fields=["costing_nominal_enabled"])

    response = client.patch(URL, {"costing_nominal_enabled": True}, format="json")

    assert response.status_code == 200
    assert response.data["costing_nominal_enabled"] is True
    assert response.data["costing_effective_enabled"] is True


def test_jefe_intenta_desactivar_ambas_bases(client, jefe):
    client.force_authenticate(jefe)
    settings = get_settings()
    settings.costing_nominal_enabled = False
    settings.save(update_fields=["costing_nominal_enabled"])

    response = client.patch(URL, {"costing_effective_enabled": False}, format="json")

    assert response.status_code == 400
    assert "non_field_errors" in response.data
    # No se persiste: la base efectiva sigue activa.
    assert SystemSettings.objects.get().costing_effective_enabled is True


def test_patch_de_ambas_bases_false_en_una_sola_peticion(client, jefe):
    client.force_authenticate(jefe)

    response = client.patch(
        URL,
        {"costing_nominal_enabled": False, "costing_effective_enabled": False},
        format="json",
    )

    assert response.status_code == 400
    assert "non_field_errors" in response.data


# --- Autorización ------------------------------------------------------------


def test_jefe_edita_la_configuracion(client, jefe):
    client.force_authenticate(jefe)

    response = client.patch(URL, {"costing_nominal_enabled": False}, format="json")

    assert response.status_code == 200
    assert response.data["costing_nominal_enabled"] is False


def test_supervisor_consulta_la_configuracion(client, supervisor):
    client.force_authenticate(supervisor)

    response = client.get(URL)

    assert response.status_code == 200
    assert response.data["costing_nominal_enabled"] is True


def test_supervisor_no_puede_editar(client, supervisor):
    client.force_authenticate(supervisor)

    response = client.patch(URL, {"costing_nominal_enabled": False}, format="json")

    assert response.status_code == 403
    assert "detail" in response.data
    # No hubo cambios.
    assert SystemSettings.objects.get().costing_nominal_enabled is True


def test_sin_permiso_no_puede_leer(client, sin_permiso):
    client.force_authenticate(sin_permiso)

    response = client.get(URL)

    assert response.status_code == 403
    assert "detail" in response.data


def test_sin_sesion_es_rechazado(client):
    assert client.get(URL).status_code == 401
    assert client.patch(URL, {"costing_nominal_enabled": False}, format="json").status_code == 401


# --- Auditoría ---------------------------------------------------------------


def test_cambiar_un_toggle_deja_rastro_de_auditoria(client, jefe):
    client.force_authenticate(jefe)

    response = client.patch(URL, {"costing_effective_enabled": False}, format="json")

    assert response.status_code == 200
    log = AuditLog.objects.get(entity="SystemSettings", field="costing_effective_enabled")
    assert log.action == "UPDATE"
    assert log.old_value == "True"
    assert log.new_value == "False"
    assert log.user_id == jefe.pk


def test_patch_sin_cambio_efectivo_no_audita(client, jefe):
    client.force_authenticate(jefe)

    # El valor enviado coincide con el actual: no hay diff, no hay auditoría.
    response = client.patch(URL, {"costing_nominal_enabled": True}, format="json")

    assert response.status_code == 200
    assert AuditLog.objects.filter(entity="SystemSettings").count() == 0
