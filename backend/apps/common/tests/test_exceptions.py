"""Tests del contrato de errores (§6.2).

Verifican que el exception handler normaliza:
- 400 -> {campo: [mensajes]} (con non_field_errors para errores sin campo)
- 403/404 -> {detail}
- excepción no manejada -> {detail} genérico, SIN traceback ni ruido técnico
"""

from rest_framework.exceptions import (
    NotFound,
    PermissionDenied,
    ValidationError,
)

from apps.common.exceptions import GENERIC_500_DETAIL, custom_exception_handler


def _handle(exc):
    return custom_exception_handler(exc, context={})


def test_validation_error_por_campo_se_normaliza_a_lista():
    exc = ValidationError({"ruc": ["El RUC ingresado no es válido."]})
    response = _handle(exc)

    assert response.status_code == 400
    assert response.data == {"ruc": ["El RUC ingresado no es válido."]}


def test_validation_error_sin_campo_va_a_non_field_errors():
    exc = ValidationError(["La fecha pertenece a un período cerrado."])
    response = _handle(exc)

    assert response.status_code == 400
    assert response.data == {"non_field_errors": ["La fecha pertenece a un período cerrado."]}


def test_permission_denied_devuelve_detail():
    response = _handle(PermissionDenied("No tiene permiso para realizar esta acción."))

    assert response.status_code == 403
    assert set(response.data.keys()) == {"detail"}
    assert response.data["detail"] == "No tiene permiso para realizar esta acción."


def test_not_found_devuelve_detail():
    response = _handle(NotFound("No se encontró el recurso."))

    assert response.status_code == 404
    assert set(response.data.keys()) == {"detail"}


def test_excepcion_no_manejada_devuelve_detail_generico_sin_traceback():
    response = _handle(RuntimeError("conexión a la base de datos rechazada en db.py:42"))

    assert response.status_code == 500
    assert response.data == {"detail": GENERIC_500_DETAIL}
    # El mensaje crudo de la excepción NUNCA llega al cliente.
    serialized = str(response.data)
    assert "db.py" not in serialized
    assert "RuntimeError" not in serialized
