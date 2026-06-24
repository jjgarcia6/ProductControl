# Propuesta: add-auth

## 1. El Problema o Necesidad de Negocio

El sistema recién bootstrapeado (F0) no tiene identidad ni autenticación: hoy no existe un usuario autenticable ni un mecanismo de tokens, por lo que **ninguna otra capability puede protegerse**. Esta es la precondición dura de todas las fases siguientes (F2, F3, F4, F5, F8, F9, F10 dependen de ella).

Sin esta base, cualquier endpoint de negocio quedaría abierto y no habría forma de distinguir quién ejecuta una operación (requisito para auditoría, autorización por rol y trazabilidad). Se necesita, como mínimo viable, que un usuario pueda iniciar sesión, mantener la sesión de forma segura, cerrarla, consultar su identidad y cambiar su propia contraseña, sobre la base de roles del sistema.

## 2. Alcance Crítico

### In-Scope (Lo que se va a construir)

**Backend (dominio `auth`, app Django `accounts`):**
- **Custom User Model**: `AbstractUser` extendido con un campo `role` (choices), establecido **antes del primer migrate de negocio** por ser una decisión costosa de revertir en Django. `AUTH_USER_MODEL = "accounts.User"`.
- **Estrategia de tokens (SimpleJWT, fijo)**: access token de vida corta (15 min) en el cuerpo de la respuesta para mantenerse **en memoria** en el cliente; refresh token (7 días) en una **cookie `httpOnly`**, con **rotación + blacklist**.
- **Endpoints de transición** (no CRUD): `login`, `refresh`, `logout`, `me`, `change-password`.
- **Roles del sistema** (Jefe, Supervisor, Responsable de ruta, Usuario) como estructura del modelo (no la autorización fina, que es F2).
- **Rate limiting** en el endpoint de login.
- Nuevos contratos de datos: serializers DRF de credenciales, identidad y cambio de contraseña, anotados con `drf-spectacular`; tipos/Zod generados del OpenAPI.

**Frontend (feature `auth`):**
- `authProvider` custom de Refine (`login`, `logout`, `check`, `getIdentity`, `onError`).
- Store de sesión en memoria (Zustand, solo sesión/UI; sin `localStorage`).
- Pantallas Login y Cambio de contraseña con estados vacío/carga/error/éxito.

### Out-of-Scope (Prohibiciones Estrictas)
- **Backend:** Toda persistencia MUST ser PostgreSQL vía Django ORM. Sin SQL raw salvo justificación explícita.
- **Backend:** Las transacciones multi-tabla MUST usar `transaction.atomic()` con rollback total.
- **Backend:** Los modelos de catálogo/datos maestros MUST heredar del mixin de soft-delete (política de 3 clases). El modelo `User` NO es catálogo: su baja se modela con `is_active` (la desactivación administrativa es F3), MUST NOT usar soft delete.
- **Backend:** El cálculo financiero (FIFO, costo nominal/efectivo, merma, saldos CxC/CxP) MUST vivir en funciones puras sin dependencia del ORM. (No aplica en esta fase; sin cálculo financiero.)
- **Frontend:** Los colores hardcodeados MUST NOT usarse; todo estilo MUST usar tokens del theme (shadcn/Tailwind) con soporte de modo claro y oscuro.
- **Seguridad:** Las credenciales y claves de firma JWT MUST NOT almacenarse en el código; MUST gestionarse vía `.env` / GCP Secret Manager.
- **Calidad:** Las refactorizaciones paralelas ajenas al dominio de este cambio MUST NOT introducirse (YAGNI).

**Fuera de alcance por dominio (se difiere a fases posteriores):**
- Permisos finos por perfil, campos invisibles y auto-aprobación → F2 (`access-control`).
- Gestión administrativa de usuarios, reset administrativo, contraseña temporal, desactivación que invalida refresh → F3 (`user-management`).
- Recuperación self-service por email → diferida a post-F25 (depende de la infraestructura de email de F22).
- Vínculo User ↔ Ficha de Directorio → se modela en F4 (FK opcional).
- MFA, SSO (YAGNI).

## 3. Evaluación de Impacto

### Modelo de Datos (PostgreSQL)
- **Nueva tabla de usuario (custom)** con `role` (choices), `is_active` y los campos de identidad heredados de `AbstractUser`. `AUTH_USER_MODEL` apunta a ella desde el inicio.
- **Tablas de la app de blacklist de SimpleJWT** (`outstanding tokens` + `blacklisted tokens`), necesarias para logout, rotación y la desactivación de F3.
- **Migración inicial reversible**; es la primera migración del proyecto y MUST preceder a cualquier app de negocio. **No** se crean otras tablas de negocio en esta fase.
- Índice único sobre el identificador de login (`username`). No se afectan índices, constraints ni FKs existentes (no los hay aún).

### Lógica de Negocio y API
- Nuevos endpoints DRF derivados de transiciones explícitas (no CRUD): `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me`, `POST /auth/change-password`.
- Nuevo servicio `apps/accounts/services.py`: emisión, rotación y blacklist de tokens; seteo/limpieza de la cookie `httpOnly`; invalidación de refresh al cambiar contraseña. ViewSets/APIViews delgados que delegan.
- Todos los errores pasan por el exception handler del **contrato de errores uniforme** (`{campo: [mensajes]}` en validación, `{detail}` en auth).
- No se modifica FIFO, costeo, merma, CxC ni CxP (no existen aún).

### Flujo del Usuario (UI)
- Recursos nuevos en Refine: una ruta **pública** de Login y una ruta **protegida** de Cambio de contraseña.
- El `authProvider` custom protege el resto de la app; ante 401 redirige a login.
- Roles afectados: los cuatro (Jefe, Supervisor, Responsable de ruta, Usuario) obtienen identidad y pueden autenticarse e iniciar/cambiar su sesión; la diferenciación de permisos por rol no se aplica aquí (F2).
- Pantallas con estados vacío/carga/error/éxito, áreas táctiles ≥44px e inputs ≥16px en iOS.

### Cadena de Trazabilidad
No se altera la cadena de trazabilidad (Ingreso → Kardex → Entrega → Cobro / Ingreso → CxP → Pago). Este cambio no toca Kardex, período, costeo ni documentos de negocio.

## 4. Riesgos y Rollback

### Riesgo Principal
El **custom user model debe establecerse antes de cualquier migración de negocio**. Si se aplica una migración con el `User` por defecto de Django, cambiar `AUTH_USER_MODEL` después es muy costoso (Django no lo soporta de forma limpia). Riesgo secundario: la **cookie de refresh cross-site** (Vercel ↔ Cloud Run) puede requerir `SameSite=None; Secure`, reabriendo CSRF en `refresh`/`logout` si el despliegue queda en dominios de plataforma distintos (mitigación: protección CSRF double-submit en esos dos endpoints, decisión registrada en README/ADR).

### Criterio de Aborto
Condición verificable, no subjetiva: si al establecer el custom user model ya existe una migración aplicada con el `User` por defecto de Django (estado detectable con `python manage.py showmigrations`), **abortar** — el repositorio recién bootstrapeado no debe tener migraciones de negocio aún. También se aborta si la migración inicial no es reversible (su reverse falla) o si las pruebas de integración de los endpoints de auth fallan tras 2 intentos de corrección.

### Plan de Rollback
La migración inicial de `accounts` (incluida la app de blacklist) MUST tener reverse funcional: `python manage.py migrate accounts zero` revierte sin pérdida de datos (no hay datos de negocio en esta fase). No se requiere data migration de limpieza ni recálculo de saldos. Revertir el code merge restaura el estado pre-auth; al ser la primera migración, no deja huérfanos en otras apps.
