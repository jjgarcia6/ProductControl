"""Settings de desarrollo. DEBUG activo; DB local (sqlite) si no hay DATABASE_URL."""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# CORS: en dev permitimos el frontend de Vite. Configurable por entorno.
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in (env("CORS_ALLOWED_ORIGINS", "http://localhost:5173") or "").split(",")
    if origin.strip()
]
