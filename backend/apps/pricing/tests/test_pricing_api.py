"""Tests de la API del maestro de precios (F6) — cubre los Scenarios del spec delta.

Lista: alta NORMAL/DESCARTE (+audit CREATE), nombre duplicado (409), sin autorización
(403). Ítem: alta con precio (+audit CREATE), producto duplicado en la lista (409),
precio negativo (400 mapeado a `price`). Baja: lista sin fichas (+audit SOFT_DELETE) y
reutilización del nombre; lista asignada a una ficha (409).
"""

from decimal import Decimal

from apps.common.models import AuditLog
from apps.directory.models import Ficha, FichaRole
from apps.pricing.models import PriceList, PriceListItem, PriceListType

# --- Lista de precios --------------------------------------------------------


def test_crea_listas_normal_y_descarte(client, gestor):
    client.force_authenticate(gestor)

    r_normal = client.post(
        "/pricing/price-lists", {"name": "Mayorista", "type": "NORMAL"}, format="json"
    )
    r_descarte = client.post(
        "/pricing/price-lists", {"name": "Descarte", "type": "DESCARTE"}, format="json"
    )

    assert r_normal.status_code == 201
    assert r_normal.data["type"] == "NORMAL"
    assert r_descarte.status_code == 201
    assert r_descarte.data["type"] == "DESCARTE"
    assert PriceList.objects.count() == 2
    assert AuditLog.objects.filter(action="CREATE", entity="PriceList").count() == 2


def test_crea_lista_con_nombre_duplicado(client, gestor):
    client.force_authenticate(gestor)
    PriceList.objects.create(name="Mayorista", type=PriceListType.NORMAL)

    response = client.post(
        "/pricing/price-lists", {"name": "Mayorista", "type": "NORMAL"}, format="json"
    )

    assert response.status_code == 409
    assert "detail" in response.data


def test_gestion_de_listas_sin_autorizacion(client, sin_permiso):
    client.force_authenticate(sin_permiso)

    response = client.post("/pricing/price-lists", {"name": "X", "type": "NORMAL"}, format="json")

    assert response.status_code == 403
    assert "detail" in response.data


def test_gestion_de_listas_sin_sesion(client):
    response = client.get("/pricing/price-lists")

    assert response.status_code == 401


# --- Ítem de precio ----------------------------------------------------------


def test_agrega_producto_con_precio(client, gestor, producto):
    client.force_authenticate(gestor)
    price_list = PriceList.objects.create(name="Mayorista", type=PriceListType.NORMAL)

    response = client.post(
        f"/pricing/price-lists/{price_list.id}/items",
        {"product": str(producto.id), "price": "12.50"},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["price"] == "12.50"
    assert response.data["product_name"] == producto.name
    assert AuditLog.objects.filter(action="CREATE", entity="PriceListItem").exists()


def test_agrega_producto_duplicado_en_lista(client, gestor, producto):
    client.force_authenticate(gestor)
    price_list = PriceList.objects.create(name="Mayorista", type=PriceListType.NORMAL)
    PriceListItem.objects.create(price_list=price_list, product=producto, price=Decimal("10"))

    response = client.post(
        f"/pricing/price-lists/{price_list.id}/items",
        {"product": str(producto.id), "price": "9.00"},
        format="json",
    )

    assert response.status_code == 409
    assert "detail" in response.data


def test_fija_precio_negativo(client, gestor, producto):
    client.force_authenticate(gestor)
    price_list = PriceList.objects.create(name="Mayorista", type=PriceListType.NORMAL)

    response = client.post(
        f"/pricing/price-lists/{price_list.id}/items",
        {"product": str(producto.id), "price": "-1.00"},
        format="json",
    )

    assert response.status_code == 400
    assert "price" in response.data


# --- Baja de lista -----------------------------------------------------------


def test_baja_lista_sin_clientes_y_reutiliza_nombre(client, gestor):
    client.force_authenticate(gestor)
    price_list = PriceList.objects.create(name="Temporal", type=PriceListType.NORMAL)

    response = client.delete(f"/pricing/price-lists/{price_list.id}")

    assert response.status_code == 204
    assert not PriceList.objects.filter(pk=price_list.pk).exists()  # el manager filtra las vivas
    assert AuditLog.objects.filter(action="SOFT_DELETE", entity="PriceList").exists()

    # El nombre se reutiliza tras la baja (índice único parcial entre vivas).
    reuse = client.post(
        "/pricing/price-lists", {"name": "Temporal", "type": "NORMAL"}, format="json"
    )
    assert reuse.status_code == 201


def test_baja_lista_asignada_a_cliente(client, gestor):
    client.force_authenticate(gestor)
    price_list = PriceList.objects.create(name="Asignada", type=PriceListType.NORMAL)
    Ficha.objects.create(
        name="Cliente",
        identification_type="CEDULA",
        identification_number="1710034065",
        roles=[FichaRole.CLIENTE],
        price_list=price_list,
    )

    response = client.delete(f"/pricing/price-lists/{price_list.id}")

    assert response.status_code == 409
    assert "detail" in response.data
    assert PriceList.objects.filter(pk=price_list.pk).exists()
