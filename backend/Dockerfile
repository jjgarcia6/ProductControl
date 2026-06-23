# Backend — imagen para GCP Cloud Run (escala a cero, stateless).
# Sirve con gunicorn; NO incluye worker persistente (no hay Celery).
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# Libs nativas de WeasyPrint (Pango, Cairo, GDK-Pixbuf y dependencias).
# Sin estas, WeasyPrint NO renderiza PDFs.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libpangoft2-1.0-0 \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libffi8 \
        libharfbuzz0b \
        libfontconfig1 \
        fonts-dejavu-core \
        shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# uv para instalar dependencias dentro de la imagen.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Capa de dependencias cacheable: solo se invalida si cambia el lockfile.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Código de la aplicación.
COPY . .

# Cloud Run inyecta $PORT; escuchar ahí. Filesystem efímero -> escribir solo en /tmp.
ENV PORT=8080 \
    DJANGO_SETTINGS_MODULE=config.settings.prod
EXPOSE 8080

# `exec` para que gunicorn reciba las señales de Cloud Run (PID 1).
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT} --workers 2 --timeout 120"]
