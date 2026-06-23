"""Tests de los helpers de settings (config.settings.base)."""

from config.settings.base import parse_database_url


def test_parse_database_url_extrae_componentes_postgres():
    url = "postgresql://user:p%40ss@db.example.com:5432/postgres"
    cfg = parse_database_url(url)

    assert cfg["ENGINE"] == "django.db.backends.postgresql"
    assert cfg["NAME"] == "postgres"
    assert cfg["USER"] == "user"
    # La contraseña URL-encoded (%40 = @) se decodifica.
    assert cfg["PASSWORD"] == "p@ss"
    assert cfg["HOST"] == "db.example.com"
    assert cfg["PORT"] == "5432"
