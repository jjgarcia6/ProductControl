"""Tests de la API de importación masiva (F7) — cubre los Scenarios del spec delta.

Dry-run válido/inválido (200 sin persistir), commit sin errores (201 + audit), commit con
fila inválida (400, nada persiste), deduplicación idempotente, lote mixto, validación
delegada (cédula inválida, categoría inexistente), fichas con roles múltiples, límite de
filas y formato no soportado (400), plantilla descargable, y autorización (403/401).
Se prueban CSV y Excel.
"""

import csv
import io

from django.core.files.uploadedfile import SimpleUploadedFile
from openpyxl import Workbook

from apps.common.models import AuditLog
from apps.directory.models import Ficha, FichaStatus
from apps.products.models import Product

PRODUCT_HEADER = ["name", "category", "unit"]
FICHA_HEADER = ["identification_type", "identification_number", "name", "email", "phone", "roles"]
VALID_CEDULA = "1710034065"
OTHER_CEDULA = "0926687856"
INVALID_CEDULA = "1710034060"


def _csv(name, header, *rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)
    return SimpleUploadedFile(name, buffer.getvalue().encode("utf-8"), content_type="text/csv")


def _xlsx(name, header, *rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(list(header))
    for row in rows:
        sheet.append(list(row))
    buffer = io.BytesIO()
    workbook.save(buffer)
    return SimpleUploadedFile(
        name,
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# --- Dry-run -----------------------------------------------------------------


def test_dry_run_valido_no_persiste(client, importer, catalogo):
    client.force_authenticate(importer)
    upload = _csv("p.csv", PRODUCT_HEADER, ["Leche", "Lácteos", "Unidad"])

    response = client.post(
        "/bulk-import/products?dry_run=true", {"file": upload}, format="multipart"
    )

    assert response.status_code == 200
    assert response.data["dry_run"] is True
    assert response.data["inserted"] == 0
    assert response.data["rows"][0]["status"] == "valid"
    assert not Product.objects.exists()


def test_dry_run_con_filas_invalidas_no_persiste(client, importer, catalogo):
    client.force_authenticate(importer)
    upload = _csv(
        "p.csv",
        PRODUCT_HEADER,
        ["Leche", "Lácteos", "Unidad"],
        ["Pan", "Inexistente", "Unidad"],
    )

    response = client.post(
        "/bulk-import/products?dry_run=true", {"file": upload}, format="multipart"
    )

    assert response.status_code == 200
    statuses = {row["row_number"]: row["status"] for row in response.data["rows"]}
    assert statuses == {2: "valid", 3: "error"}
    error_row = next(row for row in response.data["rows"] if row["status"] == "error")
    assert "category" in error_row["errors"]
    assert not Product.objects.exists()


# --- Commit ------------------------------------------------------------------


def test_commit_sin_errores_persiste_y_audita(client, importer, catalogo):
    client.force_authenticate(importer)
    upload = _csv("p.csv", PRODUCT_HEADER, ["Leche", "Lácteos", "Unidad"])

    response = client.post("/bulk-import/products", {"file": upload}, format="multipart")

    assert response.status_code == 201
    assert response.data["inserted"] == 1
    assert response.data["skipped"] == 0
    assert Product.objects.filter(name="Leche").exists()
    assert AuditLog.objects.filter(action="CREATE", entity="Product").exists()


def test_commit_con_fila_invalida_no_persiste_nada(client, importer, catalogo):
    client.force_authenticate(importer)
    upload = _csv(
        "p.csv",
        PRODUCT_HEADER,
        ["Leche", "Lácteos", "Unidad"],
        ["Pan", "Inexistente", "Unidad"],
    )

    response = client.post("/bulk-import/products", {"file": upload}, format="multipart")

    assert response.status_code == 400
    assert response.data["inserted"] == 0
    # All-or-nothing: ni siquiera la fila válida se persiste.
    assert not Product.objects.exists()


# --- Deduplicación / idempotencia --------------------------------------------


def test_reejecutar_mismo_archivo_es_idempotente(client, importer, catalogo):
    client.force_authenticate(importer)

    first = client.post(
        "/bulk-import/products",
        {"file": _csv("p.csv", PRODUCT_HEADER, ["Leche", "Lácteos", "Unidad"])},
        format="multipart",
    )
    assert first.status_code == 201
    assert first.data["inserted"] == 1

    second = client.post(
        "/bulk-import/products",
        {"file": _csv("p.csv", PRODUCT_HEADER, ["Leche", "Lácteos", "Unidad"])},
        format="multipart",
    )

    assert second.status_code == 201
    assert second.data["inserted"] == 0
    assert second.data["skipped"] == 1
    assert second.data["rows"][0]["status"] == "skipped"
    assert Product.objects.filter(name="Leche").count() == 1


def test_lote_mixto_inserta_nuevas_y_omite_duplicadas(client, importer, catalogo):
    client.force_authenticate(importer)
    Product.objects.create(name="Leche", category=catalogo[0], unit_of_measure=catalogo[1])

    upload = _csv(
        "p.csv",
        PRODUCT_HEADER,
        ["Leche", "Lácteos", "Unidad"],
        ["Queso", "Lácteos", "Unidad"],
    )
    response = client.post("/bulk-import/products", {"file": upload}, format="multipart")

    assert response.status_code == 201
    assert response.data["inserted"] == 1
    assert response.data["skipped"] == 1
    assert Product.objects.filter(name="Queso").exists()


# --- Validación delegada al dominio ------------------------------------------


def test_ficha_con_cedula_invalida_se_marca_error(client, importer):
    client.force_authenticate(importer)
    upload = _csv("f.csv", FICHA_HEADER, ["CEDULA", INVALID_CEDULA, "Juan", "", "", "CLIENTE"])

    response = client.post("/bulk-import/fichas?dry_run=true", {"file": upload}, format="multipart")

    assert response.status_code == 200
    error_row = response.data["rows"][0]
    assert error_row["status"] == "error"
    assert "identification_number" in error_row["errors"]


def test_producto_con_categoria_inexistente(client, importer, catalogo):
    client.force_authenticate(importer)
    upload = _csv("p.csv", PRODUCT_HEADER, ["Pan", "NoExiste", "Unidad"])

    response = client.post(
        "/bulk-import/products?dry_run=true", {"file": upload}, format="multipart"
    )

    assert response.status_code == 200
    assert response.data["rows"][0]["errors"]["category"]


def test_ficha_con_roles_multiples(client, importer):
    client.force_authenticate(importer)
    upload = _csv(
        "f.csv",
        FICHA_HEADER,
        ["CEDULA", VALID_CEDULA, "Juan", "j@e.com", "099", "CLIENTE,PROVEEDOR"],
    )

    response = client.post("/bulk-import/fichas", {"file": upload}, format="multipart")

    assert response.status_code == 201
    ficha = Ficha.objects.get(identification_number=VALID_CEDULA)
    assert set(ficha.roles) == {"CLIENTE", "PROVEEDOR"}
    assert ficha.status == FichaStatus.ACTIVO


# --- Excel -------------------------------------------------------------------


def test_importa_desde_excel(client, importer, catalogo):
    client.force_authenticate(importer)
    upload = _xlsx("p.xlsx", PRODUCT_HEADER, ["Yogurt", "Lácteos", "Unidad"])

    response = client.post("/bulk-import/products", {"file": upload}, format="multipart")

    assert response.status_code == 201
    assert Product.objects.filter(name="Yogurt").exists()


# --- Validación del archivo --------------------------------------------------


def test_supera_limite_de_filas(client, importer, catalogo):
    client.force_authenticate(importer)
    rows = [[f"Prod {i}", "Lácteos", "Unidad"] for i in range(1001)]
    upload = _csv("p.csv", PRODUCT_HEADER, *rows)

    response = client.post("/bulk-import/products", {"file": upload}, format="multipart")

    assert response.status_code == 400
    assert "file" in response.data
    assert not Product.objects.exists()


def test_formato_no_soportado(client, importer):
    client.force_authenticate(importer)
    upload = SimpleUploadedFile("datos.txt", b"algo", content_type="text/plain")

    response = client.post("/bulk-import/products", {"file": upload}, format="multipart")

    assert response.status_code == 400
    assert "file" in response.data


# --- Plantilla ---------------------------------------------------------------


def test_descarga_plantilla(client, importer):
    client.force_authenticate(importer)

    response = client.get("/bulk-import/products/template")

    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv"
    body = response.content.decode("utf-8")
    assert "name" in body and "category" in body


# --- Autorización ------------------------------------------------------------


def test_sin_permiso_recibe_403(client, sin_permiso, catalogo):
    client.force_authenticate(sin_permiso)
    upload = _csv("p.csv", PRODUCT_HEADER, ["Leche", "Lácteos", "Unidad"])

    response = client.post("/bulk-import/products", {"file": upload}, format="multipart")

    assert response.status_code == 403
    assert not Product.objects.exists()


def test_sin_sesion_recibe_401(client, catalogo):
    upload = _csv("p.csv", PRODUCT_HEADER, ["Leche", "Lácteos", "Unidad"])

    response = client.post("/bulk-import/products", {"file": upload}, format="multipart")

    assert response.status_code == 401
