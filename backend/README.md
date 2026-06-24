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

## Administración de identidad (F3 · add-user-management)

Consola de administración restringida al **Jefe** (resuelto server-side por el perfil de F2; 403
`{detail}` al denegar). Toda la lógica vive en `services/` bajo `@audit` + `transaction.atomic()`.

- **Usuarios** (`apps/accounts`, prefijo `/auth`):
  - `GET/POST /auth/users` — listar / crear (el `role` se sincroniza del perfil; identificador
    duplicado → 400 en el campo).
  - `PATCH /auth/users/{id}` — editar datos básicos.
  - `POST /auth/users/{id}/reset-password` — **reset administrativo**: contraseña temporal **dada por
    el admin o generada** por el sistema (RNG de la stdlib, nunca se loggea), activa
    `must_change_password` y **blacklistea** los refresh vigentes. Devuelve la temporal **una sola vez**.
  - `POST /auth/users/{id}/deactivate` · `…/reactivate` — la baja es `is_active=False` (el usuario **no**
    es catálogo: no usa `deleted_at`) e invalida sus refresh.
- **Perfiles** (`apps/authz`, prefijo `/authz`) — completan la administración que F2 dejó en modelo + seed:
  - `PATCH /authz/profiles/{id}` — editar permisos por `(módulo, acción)` del catálogo + flags.
  - `DELETE /authz/profiles/{id}` — baja (soft delete clase 2). Un perfil **con usuarios asignados** no
    puede darse de baja → **409 Conflict** (`Conflict` en `apps/common/exceptions.py`).
  - `assign-profile` de F2 se **extiende**: además de cambiar el perfil, sincroniza el `role` nominal e
    invalida los refresh para que los permisos nuevos surtan efecto sin esperar a la expiración.
- **Cambio de contraseña forzado:** `must_change_password` (campo en `accounts.User`) lo activa el reset
  y lo apaga el cambio propio (F1). Un **middleware** (`apps/accounts/middleware.py`) resuelve el usuario
  por el JWT y, mientras el flag esté activo, responde **403** a todo salvo `me`, `change-password` y
  `logout` — bloqueo global imposible de saltar por endpoint.
- **Autorización:** los endpoints admin **reutilizan** el módulo `access-control` (`read/create/update`),
  sin tocar el catálogo ni el seed de F2 (KISS). La baja de perfil mapea a `update` (cambio de estado).
- **Sin variables de entorno nuevas.**
