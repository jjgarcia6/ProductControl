"""Tests de la API del maestro de inventario (F5) — cubre los Scenarios del spec delta.

Categoría: alta (+audit CREATE), sin valores de merma, tipo de ingreso inválido (400),
nombre duplicado (409), sin autorización de perfil (403). Producto: alta (+audit),
categoría inexistente (400), nombre duplicado (409). Unidades base sembradas idempotentes.
Baja lógica: categoría sin/con productos (+audit SOFT_DELETE / 409), reutilización del
nombre tras baja.
"""

from decimal import Decimal

from apps.common.models import AuditLog
from apps.products.models import Category, IntakeType, Product, UnitOfMeasure

PASSWORD = "Str0ng-Pass!2024"  # noqa: S105 — credencial de prueba, no secreto real


def _category_payload(**overrides):
    payload = {
        "name": "Lácteos",
        "shelf_life_days": 5,
        "intake_type": "GAVETA",
    }
    payload.update(overrides)
    return payload


def _unit(name="Libras Test", symbol="lbx"):
    return UnitOfMeasure.objects.create(name=name, symbol=symbol, conversion_factor=Decimal("1"))


def _category(name="Verduras"):
    return Category.objects.create(name=name, intake_type=IntakeType.PESO)


# --- Categoría ---------------------------------------------------------------


def test_crea_categoria(client, gestor):
    client.force_authenticate(gestor)

    response = client.post("/products/categories", _category_payload(), format="json")

    assert response.status_code == 201
    assert response.data["intake_type"] == "GAVETA"
    assert response.data["reference_qty"] == "100.000"
    assert Category.objects.filter(name="Lácteos").exists()
    assert AuditLog.objects.filter(action="CREATE", entity="Category").exists()


def test_crea_categoria_sin_valores_de_merma(client, gestor):
    client.force_authenticate(gestor)

    response = client.post(
        "/products/categories", _category_payload(intake_type="PESO"), format="json"
    )

    assert response.status_code == 201
    assert response.data["merma_min"] is None
    assert response.data["merma_max"] is None


def test_tipo_de_ingreso_invalido(client, gestor):
    client.force_authenticate(gestor)

    response = client.post(
        "/products/categories", _category_payload(intake_type="OTRO"), format="json"
    )

    assert response.status_code == 400
    assert "intake_type" in response.data
    assert not Category.objects.exists()


def test_nombre_de_categoria_duplicado(client, gestor):
    client.force_authenticate(gestor)
    client.post("/products/categories", _category_payload(), format="json")

    response = client.post("/products/categories", _category_payload(), format="json")

    assert response.status_code == 409
    assert "detail" in response.data
    assert Category.objects.count() == 1


def test_crea_categoria_sin_autorizacion(client, sin_permiso):
    client.force_authenticate(sin_permiso)

    response = client.post("/products/categories", _category_payload(), format="json")

    assert response.status_code == 403
    assert "detail" in response.data
    assert not Category.objects.exists()


# --- Producto ----------------------------------------------------------------


def test_crea_producto(client, gestor):
    client.force_authenticate(gestor)
    category = _category()
    unit = _unit()

    response = client.post(
        "/products/products",
        {"name": "Tomate riñón", "category": str(category.id), "unit_of_measure": str(unit.id)},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["category_name"] == category.name
    assert Product.objects.filter(name="Tomate riñón").exists()
    assert AuditLog.objects.filter(action="CREATE", entity="Product").exists()


def test_producto_con_categoria_inexistente(client, gestor):
    client.force_authenticate(gestor)
    unit = _unit()

    response = client.post(
        "/products/products",
        {
            "name": "Fantasma",
            "category": "00000000-0000-0000-0000-000000000000",
            "unit_of_measure": str(unit.id),
        },
        format="json",
    )

    assert response.status_code == 400
    assert "category" in response.data


def test_nombre_de_producto_duplicado(client, gestor):
    client.force_authenticate(gestor)
    category = _category()
    unit = _unit()
    payload = {"name": "Papa", "category": str(category.id), "unit_of_measure": str(unit.id)}
    client.post("/products/products", payload, format="json")

    response = client.post("/products/products", payload, format="json")

    assert response.status_code == 409
    assert "detail" in response.data
    assert Product.objects.count() == 1


# --- Unidad de medida --------------------------------------------------------


def test_unidades_base_sembradas_idempotentes(db):
    libras = UnitOfMeasure.objects.get(name="Libras")
    kilos = UnitOfMeasure.objects.get(name="Kilogramos")

    assert libras.conversion_factor == Decimal("1.000000")
    assert kilos.conversion_factor == Decimal("2.204623")
    # La siembra usa get_or_create por nombre: no hay filas duplicadas.
    assert UnitOfMeasure.objects.filter(name="Libras").count() == 1


# --- Baja lógica de catálogos ------------------------------------------------


def test_baja_de_categoria_sin_productos(client, gestor):
    client.force_authenticate(gestor)
    category = _category()

    response = client.delete(f"/products/categories/{category.id}")

    assert response.status_code == 204
    assert not Category.objects.filter(pk=category.pk).exists()  # el manager filtra vivos
    assert Category.all_objects.get(pk=category.pk).deleted_at is not None
    assert AuditLog.objects.filter(action="SOFT_DELETE", entity="Category").exists()


def test_baja_de_categoria_con_productos(client, gestor):
    client.force_authenticate(gestor)
    category = _category()
    Product.objects.create(name="Zanahoria", category=category, unit_of_measure=_unit())

    response = client.delete(f"/products/categories/{category.id}")

    assert response.status_code == 409
    assert "detail" in response.data
    assert Category.objects.filter(pk=category.pk).exists()  # sigue viva


def test_reutilizacion_de_nombre_tras_baja(client, gestor):
    client.force_authenticate(gestor)
    category = _category(name="Congelados")
    category.delete()  # baja lógica directa

    response = client.post(
        "/products/categories", _category_payload(name="Congelados"), format="json"
    )

    assert response.status_code == 201
    assert Category.objects.filter(name="Congelados").count() == 1


# --- Edición (PATCH) ---------------------------------------------------------


def test_edita_categoria(client, gestor):
    client.force_authenticate(gestor)
    category = _category(name="Enlatados")

    response = client.patch(
        f"/products/categories/{category.id}", {"shelf_life_days": 30}, format="json"
    )

    assert response.status_code == 200
    assert response.data["shelf_life_days"] == 30
    assert AuditLog.objects.filter(action="UPDATE", entity="Category").exists()


def test_edita_categoria_a_nombre_duplicado(client, gestor):
    client.force_authenticate(gestor)
    _category(name="Frutas")
    otra = _category(name="Granos")

    response = client.patch(f"/products/categories/{otra.id}", {"name": "Frutas"}, format="json")

    assert response.status_code == 409
    assert "detail" in response.data


def test_edita_producto(client, gestor):
    client.force_authenticate(gestor)
    product = Product.objects.create(name="Cebolla", category=_category(), unit_of_measure=_unit())

    response = client.patch(
        f"/products/products/{product.id}", {"name": "Cebolla perla"}, format="json"
    )

    assert response.status_code == 200
    assert response.data["name"] == "Cebolla perla"


def test_baja_de_producto(client, gestor):
    client.force_authenticate(gestor)
    product = Product.objects.create(name="Ajo", category=_category(), unit_of_measure=_unit())

    response = client.delete(f"/products/products/{product.id}")

    assert response.status_code == 204
    assert not Product.objects.filter(pk=product.pk).exists()
    assert AuditLog.objects.filter(action="SOFT_DELETE", entity="Product").exists()


# --- Unidad de medida: CRUD y baja -------------------------------------------


def test_crea_unidad(client, gestor):
    client.force_authenticate(gestor)

    response = client.post(
        "/products/units",
        {"name": "Gramos", "symbol": "g", "conversion_factor": "0.002205"},
        format="json",
    )

    assert response.status_code == 201
    assert UnitOfMeasure.objects.filter(name="Gramos").exists()
    assert AuditLog.objects.filter(action="CREATE", entity="UnitOfMeasure").exists()


def test_nombre_de_unidad_duplicado(client, gestor):
    client.force_authenticate(gestor)
    payload = {"name": "Onzas", "symbol": "oz", "conversion_factor": "0.0625"}
    client.post("/products/units", payload, format="json")

    response = client.post("/products/units", payload, format="json")

    assert response.status_code == 409
    assert "detail" in response.data


def test_edita_unidad(client, gestor):
    client.force_authenticate(gestor)
    unit = _unit(name="Saco", symbol="sc")

    response = client.patch(f"/products/units/{unit.id}", {"symbol": "sco"}, format="json")

    assert response.status_code == 200
    assert response.data["symbol"] == "sco"


def test_baja_de_unidad_sin_productos(client, gestor):
    client.force_authenticate(gestor)
    unit = _unit(name="Bulto", symbol="blt")

    response = client.delete(f"/products/units/{unit.id}")

    assert response.status_code == 204
    assert not UnitOfMeasure.objects.filter(pk=unit.pk).exists()
    assert AuditLog.objects.filter(action="SOFT_DELETE", entity="UnitOfMeasure").exists()


def test_baja_de_unidad_con_productos(client, gestor):
    client.force_authenticate(gestor)
    unit = _unit(name="Caja", symbol="cj")
    Product.objects.create(name="Huevos", category=_category(), unit_of_measure=unit)

    response = client.delete(f"/products/units/{unit.id}")

    assert response.status_code == 409
    assert "detail" in response.data
    assert UnitOfMeasure.objects.filter(pk=unit.pk).exists()
