# Backend — Sistema de gestión operativa

Django 5.2 LTS + DRF. Gestionado con `uv`. Ver `README.md` raíz para el arranque local.

## Decisiones de seguridad de sesión (F1 · add-auth)

Estrategia de tokens (SimpleJWT):

- **Access token** (15 min): se devuelve en el cuerpo de la respuesta y el cliente lo
  mantiene **en memoria** (nunca en `localStorage`). Viaja en la cabecera
  `Authorization: Bearer`, por lo que los endpoints de negocio son inmunes a CSRF.
- **Refresh token** (7 días): viaja **solo** en una cookie `httpOnly`, `Secure`, con
  `Path=/auth`. Rotación activada + blacklist tras rotación (`token_blacklist`).
- Al recargar la página el access se pierde y se repone con un **refresh silencioso**.

### ADR — `SameSite` de la cookie de refresh y CSRF

- **Decisión:** por defecto `AUTH_COOKIE_SAMESITE=Lax`. Es seguro cuando el frontend y el
  backend comparten el dominio raíz (despliegue en **subdominios** del dominio propio),
  que es la topología **recomendada**.
- **Si el despliegue queda cross-site** (p. ej. frontend en `*.vercel.app` y backend en
  `*.run.app`), se debe usar `AUTH_COOKIE_SAMESITE=None` (+ `Secure`) y, en ese caso,
  **añadir protección CSRF double-submit** en `POST /auth/refresh` y `POST /auth/logout`
  (los únicos endpoints que confían en la cookie). El login no la necesita (no hay cookie
  previa) y los endpoints de negocio usan `Authorization`, no la cookie.
- `CORS_ALLOW_CREDENTIALS=True` y `CORS_ALLOWED_ORIGINS` acotado al origen del frontend
  (nunca `*` con credenciales).
- Variables relevantes en `backend/.env.example`: `JWT_SIGNING_KEY`,
  `AUTH_COOKIE_SAMESITE`, `AUTH_COOKIE_SECURE`, `AUTH_COOKIE_DOMAIN`, `LOGIN_RATELIMIT`.
