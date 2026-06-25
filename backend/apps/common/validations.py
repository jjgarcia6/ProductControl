"""Validadores de identificación ecuatoriana — funciones PURAS (sin ORM).

Módulo transversal utilitario. Enruta por tipo y dígito verificador:

- **Cédula** (10 dígitos) y **RUC de persona natural** (3er dígito 0-5, 13 dígitos):
  módulo 10 sobre los primeros 9 dígitos.
- **RUC de sociedad privada** (3er dígito 9, 13 dígitos): módulo 11, coeficientes
  [4,3,2,7,6,5,4,3,2] sobre los primeros 9 dígitos.
- **RUC del sector público** (3er dígito 6, 13 dígitos): módulo 11, coeficientes
  [3,2,7,6,5,4,3,2] sobre los primeros 8 dígitos.
- **Pasaporte:** sin checksum; se acepta cualquier alfanumérico razonable.

Sin imports de Django: reutilizable desde serializers, services, migraciones y tests.
El dígito verificador se valida SIEMPRE server-side; la validación de cliente es
conveniencia. Las funciones devuelven `bool`; el serializer mapea el error al campo.
"""

from __future__ import annotations

# Provincias válidas: 01-24 (provincias) y 30 (ecuatorianos en el exterior).
_VALID_PROVINCES = set(range(1, 25)) | {30}


def _province_ok(number: str) -> bool:
    return int(number[0:2]) in _VALID_PROVINCES


def _modulo10(first_nine: str, check_digit: int) -> bool:
    """Algoritmo módulo 10 (cédula / RUC persona natural)."""
    coefficients = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    total = 0
    for coef, char in zip(coefficients, first_nine, strict=True):
        product = coef * int(char)
        if product >= 10:
            product -= 9
        total += product
    expected = (10 - (total % 10)) % 10
    return expected == check_digit


def _modulo11(digits: str, coefficients: list[int], check_digit: int) -> bool:
    """Algoritmo módulo 11 (sociedad privada / sector público)."""
    total = sum(coef * int(char) for coef, char in zip(coefficients, digits, strict=True))
    residue = total % 11
    expected = 0 if residue == 0 else 11 - residue
    return expected == check_digit


def is_valid_cedula(number: str) -> bool:
    """Cédula ecuatoriana: 10 dígitos, provincia válida, 3er dígito 0-5, módulo 10."""
    if len(number) != 10 or not number.isdigit():
        return False
    if not _province_ok(number):
        return False
    if int(number[2]) > 5:
        return False
    return _modulo10(number[0:9], int(number[9]))


def is_valid_ruc(number: str) -> bool:
    """RUC ecuatoriano (13 dígitos): enruta por el 3er dígito a su algoritmo."""
    if len(number) != 13 or not number.isdigit():
        return False
    if not _province_ok(number):
        return False

    third = int(number[2])
    if third <= 5:
        # Persona natural: los primeros 10 dígitos son una cédula válida y el
        # establecimiento (últimos 3) no puede ser "000".
        return is_valid_cedula(number[0:10]) and number[10:13] != "000"
    if third == 6:
        # Sector público: módulo 11 sobre 8 dígitos, verificador en la posición 9,
        # establecimiento "0001" en adelante (últimos 4 dígitos).
        if not _modulo11(number[0:8], [3, 2, 7, 6, 5, 4, 3, 2], int(number[8])):
            return False
        return number[9:13] != "0000"
    if third == 9:
        # Sociedad privada: módulo 11 sobre 9 dígitos, verificador en la posición 10,
        # establecimiento "001" en adelante (últimos 3 dígitos).
        if not _modulo11(number[0:9], [4, 3, 2, 7, 6, 5, 4, 3, 2], int(number[9])):
            return False
        return number[10:13] != "000"
    return False


def is_valid_passport(number: str) -> bool:
    """Pasaporte: alfanumérico sin checksum, longitud razonable."""
    candidate = number.strip()
    return 5 <= len(candidate) <= 20 and candidate.isalnum()


def is_valid_identification(identification_type: str, number: str) -> bool:
    """Enruta la validación por tipo. Tipo desconocido -> inválido."""
    validators = {
        "CEDULA": is_valid_cedula,
        "RUC": is_valid_ruc,
        "PASAPORTE": is_valid_passport,
    }
    validator = validators.get(identification_type)
    if validator is None:
        return False
    return validator(number)
