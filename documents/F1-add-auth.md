# Change: add-auth — Fase 1

**Capability:** `auth` (inicia) · **Depende de:** F0 (bootstrap) · **Desbloquea:** F2, F3, F4, F5, F8, F9, F10
**Fuente de verdad:** `openspec/config.yaml`. Ante conflicto, manda el `config.yaml`.
**Requerimientos:** 2.5.

> **Cómo usar este archivo.** Consolida los cuatro artefactos del change. Cada sección de primer nivel mapea a un archivo dentro de `openspec/changes/add-auth/`. Descomponer respetando ese mapeo:
> - `## 1) PROPOSAL` → `proposal.md`
> - `## 2) SPECS` → `specs/auth/spec.md` (delta)
> - `## 3) DESIGN` → `design.md`
> - `## 4) TASKS` → `tasks.md`
>
> Los Requirements usan RFC 2119 con keyword en inglés (MUST/MUST NOT/SHALL); los Scenarios usan keywords en español (DADO/CUANDO/ENTONCES). Código e identificadores en inglés; documentación en español.

---

## 1) PROPOSAL → proposal.md

### Intent

Establecer la base de autenticación e identidad del sistema. Es la precondición dura de todas las fases siguientes: sin un usuario autenticable y un mecanismo de tokens, ninguna otra capability puede protegerse. Este change entrega login, renovación, cierre de sesión, identidad del usuario actual, cambio de contraseña propio y la estructura de roles, sobre SimpleJWT (fijo, sin Supabase Auth).

### Scope (qué cambia)

- **Custom User Model** (`AbstractUser` extendido con un campo `role`), establecido **antes del primer migrate de negocio** por ser una decisión costosa de revertir en Django.
- **Estrategia de tokens:** access token de vida corta (15 min) entregado en el cuerpo de la respuesta para mantenerse **en memoria** en el cliente; refresh token (7 días) entregado en una **cookie `httpOnly`**.
- **Endpoints:** login, refresh (con rotación), logout (con blacklist del refresh), usuario actual (`me`), cambio de contraseña propio.
- **Blacklist** de SimpleJWT habilitada (la necesitan el logout de esta fase y la desactivación que invalida refresh de F3).
- **Roles del sistema** (Jefe, Supervisor, Responsable de ruta, Usuario) como estructura en el modelo (no la autorización fina, que es F2).
- **Rate limiting** en el endpoint de login.

### Impacto en el modelo de datos (antes que UI — DIP)

- Nueva tabla de usuario (custom), con `role` (choices), `is_active`, y los campos de identidad. `AUTH_USER_MODEL` apuntando a ella.
- Tablas de la app de blacklist de SimpleJWT (outstanding tokens + blacklisted tokens).
- Migración inicial reversible. **No** hay otras tablas de negocio en esta fase.

### Fuera de alcance

- Permisos finos por perfil, campos invisibles y auto-aprobación → F2 (`access-control`).
- Gestión administrativa de usuarios, reset administrativo, contraseña temporal, desactivación → F3 (`user-management`).
- Recuperación self-service por email → diferida a post-F25 (depende de F22).
- Vínculo User ↔ Ficha de Directorio → se modela en F4 (FK opcional).

### Verificación de invariantes

Este change no toca Kardex, período, costeo ni documentos de negocio, por lo que no interactúa con esos invariantes. Respeta: SimpleJWT fijo (sin Supabase Auth); access 15 min / refresh 7 d; contrato de errores uniforme; rate limiting en login.

### Criterio de aborto (verificable)

Si al establecer el custom user model ya existe una migración aplicada con el `User` por defecto de Django (estado detectable con `showmigrations`), abortar: el repositorio recién bootstrapeado no debe tener migraciones de negocio aún. Condición verificable, no subjetiva.

---

## 2) SPECS → specs/auth/spec.md

# Delta para la capability `auth`

## ADDED Requirements

### Requirement: Autenticación por credenciales
El sistema MUST autenticar a un usuario con credenciales válidas y emitir un access token (vida 15 min) en el cuerpo de la respuesta y un refresh token (vida 7 días) en una cookie `httpOnly`. El sistema MUST NOT emitir tokens para credenciales inválidas ni para usuarios inactivos. Los errores MUST seguir el contrato de errores uniforme.

#### Scenario: Login con credenciales válidas
- DADO un usuario activo con credenciales correctas
- CUANDO envía una solicitud de login
- ENTONCES el sistema responde 200 con el access token en el cuerpo
- Y establece el refresh token en una cookie `httpOnly`, `Secure`, con `SameSite` configurado
- Y la respuesta incluye el identificador, el nombre y el rol del usuario

#### Scenario: Login con credenciales inválidas
- DADO un identificador con contraseña incorrecta
- CUANDO envía una solicitud de login
- ENTONCES el sistema responde 401 con `{detail}` en español
- Y no establece ninguna cookie

#### Scenario: Login de usuario inactivo
- DADO un usuario con `is_active = false`
- CUANDO envía credenciales correctas
- ENTONCES el sistema responde 401 con `{detail}`
- Y no emite tokens

### Requirement: Renovación de access token
El sistema MUST emitir un nuevo access token a partir de un refresh token válido presente en la cookie `httpOnly`, y MUST rotar el refresh token (emitir uno nuevo e invalidar el anterior por blacklist). El sistema MUST rechazar refresh tokens expirados, ausentes o revocados.

#### Scenario: Refresh con token válido
- DADO un refresh token válido en la cookie
- CUANDO solicita renovación
- ENTONCES el sistema responde 200 con un nuevo access token en el cuerpo
- Y rota el refresh token estableciendo una nueva cookie `httpOnly`
- Y agrega el refresh anterior a la blacklist

#### Scenario: Refresh con token revocado
- DADO un refresh token previamente invalidado por logout o por cambio de contraseña
- CUANDO solicita renovación
- ENTONCES el sistema responde 401 con `{detail}`

#### Scenario: Refresh sin cookie
- DADO una solicitud de renovación sin cookie de refresh
- CUANDO llega al endpoint
- ENTONCES el sistema responde 401 con `{detail}`

### Requirement: Cierre de sesión
El sistema MUST invalidar el refresh token (blacklist) y limpiar la cookie `httpOnly` al cerrar sesión, de modo que el refresh no pueda reutilizarse.

#### Scenario: Logout de sesión activa
- DADO un usuario autenticado con un refresh válido
- CUANDO solicita cierre de sesión
- ENTONCES el sistema agrega el refresh a la blacklist
- Y limpia la cookie de refresh
- Y responde 200

#### Scenario: Refresh tras logout
- DADO un usuario que cerró sesión
- CUANDO intenta renovar con el refresh anterior
- ENTONCES el sistema responde 401

### Requirement: Identidad del usuario autenticado
El sistema MUST exponer un endpoint que devuelva la identidad del usuario autenticado (identificador, nombre, rol, estado) a partir de un access token válido, y MUST rechazar solicitudes sin access token válido.

#### Scenario: Consulta de identidad con access válido
- DADO un access token válido en la cabecera de autorización
- CUANDO consulta el endpoint de usuario actual
- ENTONCES el sistema responde 200 con identificador, nombre y rol

#### Scenario: Consulta sin autenticación
- DADO una solicitud sin access token
- CUANDO consulta el endpoint de usuario actual
- ENTONCES el sistema responde 401 con `{detail}`

### Requirement: Cambio de contraseña propio
El sistema MUST permitir que un usuario autenticado cambie su propia contraseña proporcionando la contraseña actual y una nueva que cumpla la política de contraseñas. MUST rechazar si la contraseña actual es incorrecta o la nueva no cumple la política. Tras un cambio exitoso, el sistema MUST invalidar los refresh tokens vigentes del usuario.

#### Scenario: Cambio con contraseña actual correcta
- DADO un usuario autenticado
- CUANDO envía su contraseña actual correcta y una nueva válida
- ENTONCES el sistema actualiza la contraseña
- Y invalida los refresh tokens previos del usuario
- Y responde 200

#### Scenario: Cambio con contraseña actual incorrecta
- DADO un usuario autenticado
- CUANDO envía una contraseña actual incorrecta
- ENTONCES el sistema responde 400 con `{campo: [mensajes]}` señalando el campo de la contraseña actual

#### Scenario: Nueva contraseña no cumple la política
- DADO un usuario autenticado
- CUANDO envía una nueva contraseña que no cumple los validadores
- ENTONCES el sistema responde 400 con `{campo: [mensajes]}` señalando el campo de la nueva contraseña

### Requirement: Roles del sistema
El modelo de usuario MUST incluir un rol entre cuatro valores: Jefe, Supervisor, Responsable de ruta, Usuario. El rol MUST formar parte de la identidad expuesta del usuario. La autorización fina por rol se define en la capability `access-control`; aquí el rol es solo estructura.

#### Scenario: Usuario con rol asignado
- DADO un usuario con rol Supervisor
- CUANDO se consulta su identidad
- ENTONCES la respuesta incluye el rol Supervisor

### Requirement: Limitación de intentos de login
El sistema MUST limitar la tasa de intentos de login para mitigar ataques de fuerza bruta, y MUST responder con un error claro siguiendo el contrato uniforme cuando se supere el umbral.

#### Scenario: Exceso de intentos de login
- DADO múltiples intentos de login fallidos desde el mismo origen por encima del umbral configurado
- CUANDO se realiza otro intento
- ENTONCES el sistema responde con un error de límite excedido en formato `{detail}`

---

## 3) DESIGN → design.md

### Capa de datos

- **Custom User Model** en una app Django `accounts` (nombre `accounts` para no colisionar con `django.contrib.auth`; la **capability** OpenSpec es `auth`). Extiende `AbstractUser` y añade `role` como campo con `choices` (`JEFE`, `SUPERVISOR`, `RUTA`, `USUARIO`). Identificador de login: `username` (no se acopla a email, porque la recuperación es administrativa, no por correo). `AUTH_USER_MODEL = "accounts.User"` desde el inicio.
- **Manager** propio si se requiere normalizar la creación; sin lógica de negocio adicional.
- **Blacklist:** habilitar `rest_framework_simplejwt.token_blacklist` (añade tablas de outstanding y blacklisted tokens). Necesaria para logout, rotación y la desactivación de F3.
- **Migración inicial reversible**; es la primera migración del proyecto, debe preceder a cualquier app de negocio.

### Capa de API

- **Contrato OpenAPI primero:** las vistas son custom (cookie para refresh), así que cada endpoint MUST anotarse con `drf-spectacular` para que el `schema.yml` refleje el cuerpo real (access en body, refresh en cookie). El frontend genera sus tipos/Zod desde ese schema.
- **Endpoints** (transiciones explícitas, no CRUD genérico):
  - `POST /auth/login` → valida credenciales, emite access (body) + refresh (cookie `httpOnly`).
  - `POST /auth/refresh` → lee refresh de la cookie, rota, emite nuevo access (body) + nueva cookie.
  - `POST /auth/logout` → blacklist del refresh + limpia cookie.
  - `GET /auth/me` → identidad del usuario autenticado.
  - `POST /auth/change-password` → cambio propio; invalida refresh vigentes.
- **ViewSets/APIViews delgados:** reciben y validan; la lógica de emisión/rotación/blacklist y de seteo de cookies vive en `apps/accounts/services.py`. Serializers para credenciales y cambio de contraseña.
- **Errores:** todo pasa por el exception handler del contrato uniforme; `{campo: [mensajes]}` en validación, `{detail}` en auth.

### Estrategia de tokens (decisión central)

- **Access en memoria:** se devuelve en el cuerpo y el cliente lo guarda en memoria (no `localStorage` ni cookie). Viaja en `Authorization: Bearer`. Los endpoints de negocio se autentican por cabecera, lo que los deja **inmunes a CSRF**.
- **Refresh en cookie `httpOnly`:** `Secure` siempre; `SameSite` según el despliegue (ver más abajo); `Path` acotado a los endpoints de auth. No accesible desde JS (mitiga robo por XSS).
- **Rotación + blacklist:** cada refresh emite un nuevo refresh e invalida el anterior.
- **Refresh silencioso al cargar la app:** como el access vive en memoria, al recargar la página se pierde; el cliente MUST intentar un refresh silencioso al iniciar (la cookie viaja sola) para restaurar la sesión; si falla, va a login.

### Cookies cross-site (Vercel ↔ Cloud Run) — riesgo a manejar

Frontend (Vercel) y backend (Cloud Run) son orígenes distintos. Implicaciones:

- **Opción preferible:** servir ambos bajo el **mismo dominio raíz** vía subdominios (p. ej. `app.midominio.com` y `api.midominio.com`, usando el dominio propio que el proyecto ya adquiere para email). Permite `SameSite=Lax` con `Domain=.midominio.com` y elimina buena parte del riesgo CSRF.
- **Fallback (dominios de plataforma):** `SameSite=None; Secure` para que la cookie viaje cross-site. Esto reabre CSRF en los endpoints que usan cookie (`refresh`, `logout`), así que MUST añadirse protección CSRF (token double-submit) en esos dos endpoints. Los demás endpoints no usan cookie y no la requieren.
- **CORS:** `CORS_ALLOW_CREDENTIALS = True` y origen restringido al dominio del frontend (nunca `*` con credenciales).

> Esta decisión MUST quedar registrada en el `README`/ADR para poder endurecerla. La recomendación es ir a subdominios del dominio propio en cuanto el dominio esté disponible.

### Capa de frontend

- **`authProvider` de Refine custom** (no el de `simple-rest` por defecto): `login`, `logout`, `check`, `getIdentity`, `onError`.
- **Access en memoria:** un módulo/`store` Zustand de sesión (solo UI/sesión, permitido por el config) que NO persiste el access. Nada de `localStorage`.
- **Interceptor HTTP:** añade `Authorization` con el access en memoria; ante 401 intenta `refresh` (con `withCredentials`) una vez y reintenta; si el refresh falla, limpia sesión y redirige a login.
- **Pantallas:** Login y Cambio de contraseña. Ambas cubren los estados vacío/carga/error/éxito (Refine). Inputs ≥16px en iOS (evita zoom de Safari); áreas táctiles ≥44px; tokens del theme (índigo), sin hex literales; errores de campo con el componente `FieldError` compartido con Zod.

### Seguridad

- Rate limiting (`django-ratelimit`) en `login`.
- Política de contraseñas: validadores de Django (longitud, similitud, comunes) configurados; los mensajes salen en español por `LANGUAGE_CODE`.
- `SIMPLE_JWT`: access 15 min, refresh 7 d, rotación activada, blacklist tras rotación.
- CSRF en `refresh`/`logout` si el despliegue queda cross-site (ver arriba).

### Qué NO se hace (YAGNI)

Sin recuperación por email, sin MFA, sin SSO, sin gestión administrativa de usuarios, sin permisos por perfil. Cada uno llega en su fase si el requisito lo pide.

---

## 4) TASKS → tasks.md

> Orden obligatorio del `config.yaml`: Contrato (OpenAPI) → Migraciones Django → Backend (services) → Frontend → Seguridad → Pruebas. No se avanza de grupo con ítems pendientes. Cada tarea nombra el archivo/módulo exacto. Definition of done global: todos los gates del pipeline en verde localmente antes de declarar el change completo.

### A. Contrato y modelo (OpenAPI + datos)
- [ ] A.1 Crear la app `accounts` (`apps/accounts/`) y definir `User(AbstractUser)` con `role` (choices) en `apps/accounts/models.py`.
- [ ] A.2 Configurar `AUTH_USER_MODEL = "accounts.User"` en `config/settings/base.py`.
- [ ] A.3 Habilitar `rest_framework_simplejwt.token_blacklist` en `INSTALLED_APPS` y configurar `SIMPLE_JWT` (access 15 min, refresh 7 d, rotación + blacklist).
- [ ] A.4 Definir serializers en `apps/accounts/serializers.py` (login, identidad/`me`, cambio de contraseña).
- [ ] A.5 Anotar los endpoints con `drf-spectacular` (cuerpo real: access en body, refresh en cookie) y regenerar `schema.yml`.

### B. Migraciones
- [ ] B.1 `makemigrations accounts` y verificar que es la **primera** migración del proyecto (`showmigrations`); confirmar reversibilidad.
- [ ] B.2 `migrate` y verificar arranque limpio.

### C. Backend (services + vistas)
- [ ] C.1 Implementar en `apps/accounts/services.py` la emisión, rotación, blacklist y el seteo/limpieza de la cookie `httpOnly` de refresh.
- [ ] C.2 Implementar las vistas delgadas en `apps/accounts/views.py` (`login`, `refresh`, `logout`, `me`, `change-password`) delegando en services.
- [ ] C.3 Registrar rutas en `apps/accounts/urls.py` e incluirlas en `config/urls.py`.
- [ ] C.4 Verificar que todos los errores salen por el contrato uniforme (`{campo: [mensajes]}` / `{detail}`).

### D. Frontend
- [ ] D.1 Generar tipos + Zod desde `schema.yml` (`npm run codegen`).
- [ ] D.2 Implementar el store de sesión en memoria (Zustand) en `src/features/auth/` (sin `localStorage`).
- [ ] D.3 Implementar el `authProvider` de Refine y el interceptor HTTP (Authorization + refresh silencioso ante 401 + refresh al cargar la app), con `withCredentials`.
- [ ] D.4 Construir las pantallas Login y Cambio de contraseña en `src/features/auth/` con estados vacío/carga/error/éxito, tokens del theme, `FieldError` compartido, inputs ≥16px iOS.

### E. Seguridad
- [ ] E.1 Activar `django-ratelimit` en `login`.
- [ ] E.2 Configurar validadores de contraseña de Django y verificar mensajes en español.
- [ ] E.3 Configurar `CORS_ALLOW_CREDENTIALS`, origen del frontend y atributos de cookie (`Secure`, `SameSite`, `Path`); si el despliegue queda cross-site, añadir protección CSRF en `refresh`/`logout`. Registrar la decisión en el README/ADR.

### F. Pruebas (gate)
- [ ] F.1 Tests de backend en `apps/accounts/tests/` cubriendo todos los Scenarios del spec (login válido/ inválido/ inactivo; refresh válido/ revocado/ ausente; logout + refresh tras logout; `me` con/sin token; cambio de contraseña correcto/ incorrecto/ política; rol en identidad; rate limit).
- [ ] F.2 Tests de frontend (Vitest + RTL) del flujo de login y del interceptor de refresh; smoke en WebKit (Playwright) del login en Safari iOS.
- [ ] F.3 Ejecutar y dejar en verde: `ruff`, `mypy --strict`, `bandit`, `pip-audit`, `pytest` (cobertura ≥80%); `eslint`, `tsc`, `npm audit`, `vitest`. Confirmar antes de declarar el change completo.
