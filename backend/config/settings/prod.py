"""Settings de producción (Cloud Run).

DEBUG = False es OBLIGATORIO: sin esto el contrato de errores (§6) no se garantiza
y se filtrarían tracebacks. Todos los secretos vienen del entorno (GCP Secret Manager).
"""

from .base import *  # noqa: F401,F403
from .base import DATABASE_URL, env

DEBUG = False

# Variables requeridas en producción: fallar rápido si faltan.
SECRET_KEY = env("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY es obligatoria en producción.")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL es obligatoria en producción (Supabase PostgreSQL).")

ALLOWED_HOSTS = [
    host.strip() for host in (env("DJANGO_ALLOWED_HOSTS", "") or "").split(",") if host.strip()
]

# CORS: SOLO el dominio de Vercel (configurable por entorno).
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in (env("CORS_ALLOWED_ORIGINS", "") or "").split(",")
    if origin.strip()
]

# Endurecimiento de seguridad. Cloud Run termina TLS y reenvía X-Forwarded-Proto.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# El traceback de las excepciones 5xx se registra SOLO en logs del servidor (§6.2).
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
    },
}
