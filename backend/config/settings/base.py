"""
Settings base compartidos por todos los entornos.

Reglas (runbook §4.4 / config.yaml — fuente de verdad):
- Secretos y credenciales SOLO desde variables de entorno. NUNCA en el repositorio.
- DATABASES apunta a Supabase (PostgreSQL) vía DATABASE_URL. Supabase se usa SOLO como
  PostgreSQL hosteado: sin Auth/Realtime/Storage.
- Autenticación por JWTAuthentication (SimpleJWT). Access 15 min / refresh 7 días.
- Contrato de errores uniforme vía EXCEPTION_HANDLER de apps.common.
- LANGUAGE_CODE = "es" para que los mensajes de error por defecto salgan en español.

Cada entorno (dev.py, prod.py) importa este módulo y ajusta DEBUG, ALLOWED_HOSTS,
DATABASES, CORS y endurecimiento de seguridad.
"""

import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

# backend/ (config/settings/base.py -> parents: settings, config, backend)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# python-dotenv carga backend/.env en desarrollo. En producción las variables vienen
# del entorno (GCP Secret Manager), no de un archivo.
load_dotenv(BASE_DIR / ".env")


def env(name: str, default: str | None = None) -> str | None:
    """Lee una variable de entorno. Los entornos que la requieran deben validarla."""
    return os.environ.get(name, default)


def parse_database_url(url: str) -> dict[str, object]:
    """Traduce una DATABASE_URL de PostgreSQL al dict DATABASES de Django.

    Se parsea a mano (urllib) para no añadir una dependencia fuera de las listadas
    en el runbook (§0). Supabase entrega una URL postgres:// estándar.
    """
    parsed = urlparse(url)
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or ""),
        "CONN_MAX_AGE": 600,
    }


# SECURITY WARNING: el secreto real SIEMPRE viene de DJANGO_SECRET_KEY en el entorno.
# El valor por defecto es claramente inseguro y solo habilita el arranque local.
SECRET_KEY = env("DJANGO_SECRET_KEY", "django-insecure-dev-only-do-not-use-in-prod")

# Sobrescrito por cada entorno.
DEBUG = False
ALLOWED_HOSTS: list[str] = []


# Application definition

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "corsheaders",
]

LOCAL_APPS = [
    "apps.common",
    "apps.accounts",
    "apps.authz",
    "apps.directory",
    "apps.credit",
    "apps.products",
    "apps.pricing",
    "apps.bulk_import",
    "apps.system_settings",
    "apps.period",
]

# Modelo de usuario propio (accounts.User extiende AbstractUser con `role`).
# DEBE definirse antes de la primera migración del proyecto.
AUTH_USER_MODEL = "accounts.User"

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # F3: bloqueo global de cambio de contraseña forzado (resuelve el usuario por JWT).
    "apps.accounts.middleware.ForcePasswordChangeMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database — PostgreSQL en TODOS los entornos vía DATABASE_URL (sin fallback SQLite):
# Supabase (Session pooler IPv4) en prod; contenedor local (docker-compose.dev.yml) en dev/CI.
DATABASE_URL = env("DATABASE_URL")
if not DATABASE_URL:  # pragma: no cover - guardia de configuración
    raise ImproperlyConfigured(
        "DATABASE_URL es obligatorio (PostgreSQL). En dev/CI usa el Postgres local de "
        "docker-compose.dev.yml; en prod, la Session pooler de Supabase."
    )
DATABASES = {"default": parse_database_url(DATABASE_URL)}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization — español por contrato de errores (§6).
LANGUAGE_CODE = "es"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# Static files
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Django REST Framework — JWT + drf-spectacular + contrato de errores.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.common.exceptions.custom_exception_handler",
}

# SimpleJWT — access 15 min / refresh 7 días (decisión cerrada §1).
# Rotación + blacklist tras rotación: cada refresh emite uno nuevo e invalida el anterior.
# SIGNING_KEY: clave dedicada desde el entorno (Secret Manager en prod); si falta, cae a
# DJANGO_SECRET_KEY para no romper el arranque local. NUNCA un literal en el repo.
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "SIGNING_KEY": env("JWT_SIGNING_KEY") or SECRET_KEY,
}

# Cookie del refresh token (httpOnly). El access NUNCA va en cookie: viaja en el cuerpo y
# el cliente lo mantiene en memoria. Atributos configurables por entorno (cross-site vs.
# subdominios). `Secure` se fuerza en prod; en local se permite false para http://localhost.
AUTH_COOKIE_NAME = "refresh_token"
AUTH_COOKIE_PATH = "/auth"
AUTH_COOKIE_HTTPONLY = True
AUTH_COOKIE_SECURE = (env("AUTH_COOKIE_SECURE", "false") or "false").lower() == "true"
AUTH_COOKIE_SAMESITE = env("AUTH_COOKIE_SAMESITE", "Lax") or "Lax"
AUTH_COOKIE_DOMAIN = env("AUTH_COOKIE_DOMAIN") or None

# Umbral de rate limit del login (django-ratelimit). Constante centralizada, no literal.
LOGIN_RATELIMIT = env("LOGIN_RATELIMIT", "5/m") or "5/m"

# El frontend envía la cookie de refresh con withCredentials: el backend debe permitir
# credenciales en CORS. El origen permitido se acota por entorno (CORS_ALLOWED_ORIGINS);
# nunca `*` junto con credenciales.
CORS_ALLOW_CREDENTIALS = True

# drf-spectacular — el schema OpenAPI del backend es la fuente de tipos del frontend.
SPECTACULAR_SETTINGS = {
    "TITLE": "Sistema de gestión operativa — API",
    "DESCRIPTION": "Contrato OpenAPI del backend. Fuente de verdad de tipos para el frontend.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# Caché por defecto (django-ratelimit la usa para los contadores de los logins).
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# django-ratelimit activo (se aplica por vista con su decorador en los endpoints de login).
RATELIMIT_ENABLE = True
