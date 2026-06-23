"""Contrato de errores uniforme — exception handler de DRF (§6).

Toda respuesta de error del backend cumple UNO de dos formatos, en español y sin ruido:

- Validación (HTTP 400): plano, una clave por campo; los errores no atados a un campo
  van en `non_field_errors`:
      {"ruc": ["El RUC ingresado no es válido."], "non_field_errors": ["..."]}
- Errores generales (401/403/404/409/5xx): un único mensaje:
      {"detail": "No tiene permiso para realizar esta acción."}

NUNCA se devuelve al cliente: traceback, nombre de excepción, ruta de archivo, SQL ni
status interno. Las excepciones no manejadas (5xx) registran el traceback SOLO en los
logs del servidor.
"""

from __future__ import annotations

import logging
from typing import Any

from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger("django.request")

GENERIC_500_DETAIL = "Ocurrió un error interno. Intente nuevamente."


def _coerce_messages(value: Any) -> list[str]:
    """Aplana cualquier estructura de errores DRF a una lista de strings."""
    if isinstance(value, list):
        messages: list[str] = []
        for item in value:
            messages.extend(_coerce_messages(item))
        return messages
    if isinstance(value, dict):
        messages = []
        for item in value.values():
            messages.extend(_coerce_messages(item))
        return messages
    return [str(value)]


def _normalize_validation(data: Any) -> dict[str, list[str]]:
    """Normaliza un 400 al contrato {campo: [mensajes]} con non_field_errors."""
    if isinstance(data, dict):
        return {key: _coerce_messages(value) for key, value in data.items()}
    # Lista o string sueltos: no están atados a un campo.
    return {"non_field_errors": _coerce_messages(data)}


def _extract_detail(data: Any) -> str:
    """Extrae un único mensaje para los errores generales ({detail})."""
    if isinstance(data, dict):
        if "detail" in data:
            return str(data["detail"])
        messages = _coerce_messages(data)
        return messages[0] if messages else GENERIC_500_DETAIL
    if isinstance(data, list):
        messages = _coerce_messages(data)
        return messages[0] if messages else GENERIC_500_DETAIL
    return str(data)


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response:
    """Handler del contrato de errores. Registrado en REST_FRAMEWORK.EXCEPTION_HANDLER."""
    response = drf_exception_handler(exc, context)

    # Excepción NO manejada por DRF (5xx): el traceback solo va a logs del servidor.
    if response is None:
        logger.exception("Excepción no manejada en la API", exc_info=exc)
        return Response({"detail": GENERIC_500_DETAIL}, status=500)

    if response.status_code == 400:
        response.data = _normalize_validation(response.data)
    else:
        response.data = {"detail": _extract_detail(response.data)}

    return response
