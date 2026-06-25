"""Tests de los validadores de identificación ecuatoriana (funciones puras, sin ORM).

Cubre cédula, RUC (persona natural, sociedad privada, sector público) y pasaporte, con
casos válidos e inválidos por cada variante y el enrutado por tipo.
"""

from apps.common.validations import (
    is_valid_cedula,
    is_valid_identification,
    is_valid_passport,
    is_valid_ruc,
)

# Números válidos verificados con su dígito verificador:
VALID_CEDULA = "1710034065"
VALID_RUC_NATURAL = "1710034065001"  # cédula válida + establecimiento 001
VALID_RUC_PRIVADA = "1790011674001"  # 3er dígito 9, módulo 11
VALID_RUC_PUBLICA = "1760000150001"  # 3er dígito 6, módulo 11


# --- Cédula ------------------------------------------------------------------


def test_cedula_valida():
    assert is_valid_cedula(VALID_CEDULA) is True


def test_cedula_digito_verificador_invalido():
    assert is_valid_cedula("1710034060") is False


def test_cedula_provincia_invalida():
    assert is_valid_cedula("9910034065") is False


def test_cedula_tercer_digito_invalido():
    # Tercer dígito 6 no corresponde a persona natural.
    assert is_valid_cedula("1760034065") is False


def test_cedula_longitud_invalida():
    assert is_valid_cedula("171003406") is False
    assert is_valid_cedula("17100340655") is False


def test_cedula_no_numerica():
    assert is_valid_cedula("17100A4065") is False


# --- RUC ---------------------------------------------------------------------


def test_ruc_persona_natural_valido():
    assert is_valid_ruc(VALID_RUC_NATURAL) is True


def test_ruc_persona_natural_establecimiento_cero_invalido():
    assert is_valid_ruc("1710034065000") is False


def test_ruc_sociedad_privada_valido():
    assert is_valid_ruc(VALID_RUC_PRIVADA) is True


def test_ruc_sociedad_privada_digito_invalido():
    assert is_valid_ruc("1790011675001") is False


def test_ruc_sector_publico_valido():
    assert is_valid_ruc(VALID_RUC_PUBLICA) is True


def test_ruc_sector_publico_digito_invalido():
    assert is_valid_ruc("1760000160001") is False


def test_ruc_longitud_invalida():
    assert is_valid_ruc("179001167400") is False


def test_ruc_tercer_digito_no_valido():
    # Tercer dígito 7 no es persona natural (0-5), pública (6) ni privada (9).
    assert is_valid_ruc("1770011674001") is False


# --- Pasaporte ---------------------------------------------------------------


def test_pasaporte_valido():
    assert is_valid_passport("AB123456") is True


def test_pasaporte_con_espacios_invalido():
    assert is_valid_passport("AB 1234") is False


def test_pasaporte_demasiado_corto():
    assert is_valid_passport("AB1") is False


# --- Enrutado por tipo -------------------------------------------------------


def test_router_cedula():
    assert is_valid_identification("CEDULA", VALID_CEDULA) is True


def test_router_ruc():
    assert is_valid_identification("RUC", VALID_RUC_PRIVADA) is True


def test_router_pasaporte():
    assert is_valid_identification("PASAPORTE", "X1234567") is True


def test_router_tipo_desconocido():
    assert is_valid_identification("LICENCIA", "1710034065") is False
