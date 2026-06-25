"""Tests de la API de términos de crédito (F4) — cubre los Scenarios del spec delta.

Términos por faceta; faceta duplicada(409); integridad faceta↔rol(400); edición;
401/403 sin autorización; auditoría.
"""

from apps.common.models import AuditLog
from apps.credit.models import CreditTerms


def _terms_payload(ficha, **overrides):
    payload = {
        "ficha": str(ficha.id),
        "facet": "CLIENTE",
        "credit_limit": "1500.00",
        "term_days": 30,
        "notice_days": 2,
    }
    payload.update(overrides)
    return payload


def test_define_terminos_de_cliente(client, gestor, ficha_cliente):
    client.force_authenticate(gestor)

    response = client.post("/credit/terms", _terms_payload(ficha_cliente), format="json")

    assert response.status_code == 201
    assert response.data["facet"] == "CLIENTE"
    assert CreditTerms.objects.filter(ficha=ficha_cliente, facet="CLIENTE").exists()
    assert AuditLog.objects.filter(action="CREATE", entity="CreditTerms").exists()


def test_define_terminos_de_proveedor(client, gestor, ficha_proveedor):
    client.force_authenticate(gestor)

    response = client.post(
        "/credit/terms", _terms_payload(ficha_proveedor, facet="PROVEEDOR"), format="json"
    )

    assert response.status_code == 201
    assert response.data["facet"] == "PROVEEDOR"


def test_terminos_duplicados_para_la_misma_faceta(client, gestor, ficha_cliente):
    client.force_authenticate(gestor)
    client.post("/credit/terms", _terms_payload(ficha_cliente), format="json")

    response = client.post("/credit/terms", _terms_payload(ficha_cliente), format="json")

    assert response.status_code == 409
    assert "detail" in response.data
    assert CreditTerms.objects.filter(ficha=ficha_cliente).count() == 1


def test_faceta_cliente_sobre_ficha_sin_rol_cliente(client, gestor, ficha_proveedor):
    client.force_authenticate(gestor)

    response = client.post(
        "/credit/terms", _terms_payload(ficha_proveedor, facet="CLIENTE"), format="json"
    )

    assert response.status_code == 400
    assert "facet" in response.data
    assert not CreditTerms.objects.exists()


def test_edita_terminos_existentes(client, gestor, ficha_cliente):
    client.force_authenticate(gestor)
    created = client.post("/credit/terms", _terms_payload(ficha_cliente), format="json")
    terms_id = created.data["id"]

    response = client.patch(f"/credit/terms/{terms_id}", {"credit_limit": "3000.00"}, format="json")

    assert response.status_code == 200
    assert response.data["credit_limit"] == "3000.00"
    assert AuditLog.objects.filter(action="UPDATE", entity="CreditTerms").exists()


def test_anonimo_no_puede_definir_terminos(client, ficha_cliente):
    response = client.post("/credit/terms", _terms_payload(ficha_cliente), format="json")
    assert response.status_code == 401


def test_sin_permiso_no_puede_definir_terminos(client, sin_permiso, ficha_cliente):
    client.force_authenticate(sin_permiso)

    response = client.post("/credit/terms", _terms_payload(ficha_cliente), format="json")

    assert response.status_code == 403
    assert not CreditTerms.objects.exists()
