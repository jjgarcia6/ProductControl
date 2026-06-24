"""Fixtures de los tests de auth."""

import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clear_ratelimit_cache():
    """El rate limit del login usa la caché local; se limpia entre tests para aislar."""
    cache.clear()
    yield
    cache.clear()
