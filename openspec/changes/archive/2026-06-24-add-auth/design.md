# Diseño Técnico: add-auth
<!-- DIP: Datos → API → UI. -->

## 1. Capa de Datos (PostgreSQL + Django ORM)

App Django `accounts` (nombre técnico para no colisionar con `django.contrib.auth`; la capability OpenSpec es `auth`). Es la **primera migración del proyecto** y MUST preceder a cualquier app de negocio.

### Tablas e Índices

| Tabla | Índice / Constraint | Tipo | Justificación |
| :--- | :--- | :--- | :--- |
| `accounts_user` | `username` | `unique` (btree) | Identificador de login; unicidad e índice para autenticación. |
| `accounts_user` | `role` | `btree` | Filtro futuro por rol (F2 autorización). Bajo costo, alto uso. |
| `token_blacklist_outstandingtoken` | (provisto por SimpleJWT) | `fk → accounts_user` | Registro de refresh tokens emitidos; soporte de rotación/blacklist. |
| `token_blacklist_blacklistedtoken` | (provisto por SimpleJWT) | `fk → outstandingtoken` | Refresh tokens invalidados (logout, rotación, cambio de contraseña). |

> **Decisión de PK:** `accounts.User` extiende `AbstractUser`, que trae **PK entera autoincremental** por defecto. Se mantiene la PK de `AbstractUser` (no se fuerza `UUIDField`) para no romper la compatibilidad de SimpleJWT/Django auth ni añadir complejidad innecesaria (KISS). El identificador de login es `username` (no email: la recuperación es administrativa, no por correo).

### Modelo Django
<!-- User NO es catálogo: su baja se modela con is_active (F3). NO hereda SoftDeleteMixin. -->
```python
# Modelo Django — Tabla: accounts_user
# Hereda de AbstractUser (incluye username, password, is_active, first_name, last_name, ...).
# NO usa SoftDeleteMixin (no es catálogo): la desactivación se modela con is_active (F3).

from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    JEFE = "JEFE", "Jefe"
    SUPERVISOR = "SUPERVISOR", "Supervisor"
    RUTA = "RUTA", "Responsable de ruta"
    USUARIO = "USUARIO", "Usuario"


class User(AbstractUser):
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.USUARIO,
        help_text="Rol del sistema. La autorización fina por rol se define en access-control (F2).",
    )

    class Meta:
        db_table = "accounts_user"
```

### Migración Django
```
# Archivo: apps/accounts/migrations/0001_initial.py
# operations: CreateModel(User) ...  (+ migración de token_blacklist vía su app)
# Generar con: python manage.py makemigrations accounts
# Aplicar con:  python manage.py migrate
# Reverse de prueba: python manage.py migrate accounts zero
# Precondición (criterio de aborto): showmigrations NO debe mostrar migraciones de negocio previas.
```

### Impacto en Invariantes del Sistema
- **Período cerrado:** No aplica. Auth no crea documentos con fecha.
- **Kardex FIFO / append-only:** No aplica. No se toca el Kardex.
- **Doble costeo:** No aplica. Sin cálculo financiero.
- **Cuadre de ruta:** No aplica.
- **Snapshot inmutable de entrega:** No aplica.
- **Nota de crédito vinculada:** No aplica.
- **Soft delete (3 clases):** `User` no es catálogo ni documento con estado. Su baja se modela con `is_active` (desactivación administrativa en F3), MUST NOT usar `deleted_at`.
- **Trazabilidad:** No se altera Ingreso → Kardex → Entrega → Cobro / Ingreso → CxP → Pago.

---

## 2. Capa de API y Contratos (Fuente de Verdad)

Las vistas son **custom** (cookie para refresh), por lo que cada endpoint MUST anotarse con `drf-spectacular` para que el `schema.yml` refleje el cuerpo real (access en body, refresh en cookie). El Frontend genera sus tipos/Zod desde ese schema.

### Diccionario de Datos Vivo

| Entidad | Campo | Tipo (Py / TS) | Descripción (Uso y Propósito) | Restricciones |
| :--- | :--- | :--- | :--- | :--- |
| `User` | `username` | `str / string` | Identificador de login. | Unique, requerido, ≤150 |
| `User` | `first_name` / `last_name` | `str / string` | Nombre mostrado en la identidad. | Opcional |
| `User` | `role` | `str(enum) / enum` | Rol del sistema (JEFE/SUPERVISOR/RUTA/USUARIO). | Requerido, default USUARIO |
| `User` | `is_active` | `bool / boolean` | Estado del usuario; inactivo no autentica. | Default true |
| `LoginRequest` | `username`, `password` | `str / string` | Credenciales de entrada. | Requeridos, write-only |
| `TokenResponse` | `access` | `str / string` | Access JWT (15 min), en el cuerpo. Cliente lo mantiene en memoria. | Read-only |
| `TokenResponse` | `user` | `obj / object` | Identidad embebida (id, username, nombre, role). | Read-only |
| `ChangePasswordRequest` | `current_password`, `new_password` | `str / string` | Cambio propio de contraseña. | Requeridos, write-only, `new_password` valida política Django |

> El refresh token **no** aparece en el cuerpo: viaja solo en la cookie `httpOnly`. Se documenta como cookie en el OpenAPI, no como campo de respuesta.

### Backend: Serializers DRF
```python
# apps/accounts/serializers.py — entrada (write) y salida (read) separadas.
# Cada campo MUST incluir help_text para el OpenAPI / Diccionario Vivo.

from rest_framework import serializers


class LoginSerializer(serializers.Serializer):           # write
    username = serializers.CharField(help_text="Identificador de login.")
    password = serializers.CharField(write_only=True, help_text="Contraseña.")


class UserIdentitySerializer(serializers.ModelSerializer):  # read (me / login response)
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "role", "is_active"]


class ChangePasswordSerializer(serializers.Serializer):  # write
    current_password = serializers.CharField(write_only=True, help_text="Contraseña actual.")
    new_password = serializers.CharField(write_only=True, help_text="Nueva contraseña (valida política Django).")
```

### Frontend: Tipos generados (Zod + TypeScript)
```typescript
// Generado desde el OpenAPI de DRF (schema.yml) — NO editar a mano.
// loginSchema, changePasswordSchema, userIdentitySchema (Zod) + z.infer<>.
// Los formularios usan React Hook Form + zodResolver(...).
```

### Endpoints de DRF
<!-- Transiciones explícitas, NO CRUD genérico. -->

| Verbo | Ruta | Write Serializer | Read Serializer | Códigos HTTP | Roles |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/auth/login` | `LoginSerializer` | `UserIdentitySerializer` | `200 / 401` (+ `429` rate limit) | Público |
| `POST` | `/auth/refresh` | — (cookie) | — | `200 / 401` | Autenticado por cookie refresh |
| `POST` | `/auth/logout` | — (cookie) | — | `200 / 401` | Autenticado |
| `GET` | `/auth/me` | — | `UserIdentitySerializer` | `200 / 401` | Autenticado |
| `POST` | `/auth/change-password` | `ChangePasswordSerializer` | — | `200 / 400 / 401` | Autenticado |

> Errores: todo pasa por el exception handler del contrato uniforme — `{campo: [mensajes]}` en validación (400), `{detail}` en auth (401/429).

### Servicio de Negocio
<!-- La lógica de emisión/rotación/blacklist/cookies vive en services, no en las vistas. -->

| Servicio | Método | Responsabilidad única | Transaccional |
| :--- | :--- | :--- | :--- |
| `accounts/services.py` | `issue_tokens(user, response)` | Emitir access (body) + setear refresh en cookie `httpOnly`. | No |
| `accounts/services.py` | `rotate_refresh(request, response)` | Leer refresh de cookie, rotar, blacklist del anterior, nueva cookie. | Sí |
| `accounts/services.py` | `revoke_refresh(request, response)` | Blacklist del refresh de la cookie + limpiar cookie (logout). | Sí |
| `accounts/services.py` | `revoke_all_refresh(user)` | Blacklist de **todos** los outstanding refresh del usuario. Helper reutilizable. | Sí |
| `accounts/services.py` | `change_own_password(user, current, new)` | Validar actual, aplicar política y llamar a `revoke_all_refresh(user)`. | Sí |

> **DRY / alineación con F3:** `revoke_all_refresh(user)` se diseña como helper reutilizable porque F3 (`user-management`) lo necesita en tres operaciones — reset administrativo, desactivación y cambio de perfil. `change_own_password` NO debe invalidar refresh inline; MUST delegar en `revoke_all_refresh(user)` para que F3 reuse el mismo servicio sin reimplementar la lógica de blacklist por usuario.

> **Auditoría:** los eventos de seguridad sensibles (cambio de contraseña, logout) se registran vía el mecanismo `@audit` del bootstrap cuando aplique; el régimen completo de auditoría de eventos de seguridad (reset, desactivación, cambio de rol) es F3.

> **Punto de extensión para F2/F3:** `UserIdentitySerializer` (la respuesta de `me` y de `login`) es el punto de extensión de la identidad. F2 le añade `profile` y F3 el flag `must_change_password`; ambas fases MUST **extender** este serializer, no crear uno paralelo (DRY). Además, cuando F3 implemente el bloqueo por cambio forzado, su allow-list MUST incluir `/auth/refresh` (no solo `change-password`/`me`/`logout`): el access vive en memoria y se pierde al recargar, por lo que el refresh silencioso debe poder reponerlo antes de que el usuario pueda cambiar la contraseña.

---

## 3. Capa de Presentación (UI — React + Refine)

### Árbol de Directorios de la Feature
```
src/features/auth/
├── components/
│   ├── LoginForm.tsx              # Presentacional: campos + estados (vacío/carga/error/éxito)
│   ├── ChangePasswordForm.tsx     # Presentacional: campos + estados
│   └── LoginContainer.tsx         # Contenedor: orquesta authProvider.login + navegación
├── hooks/
│   └── useChangePassword.ts       # Mutación de cambio de contraseña (Refine useCustomMutation)
├── providers/
│   └── authProvider.ts            # login/logout/check/getIdentity/onError de Refine
├── store/
│   └── sessionStore.ts            # Zustand: access en memoria (NO persiste, sin localStorage)
├── api/
│   └── httpClient.ts              # Interceptor: Authorization + refresh silencioso ante 401
├── types/
│   └── auth.types.ts              # Re-exporta tipos generados del OpenAPI
└── index.ts                       # Contrato público
```

### Contrato Público (`index.ts`)
```typescript
export { authProvider } from './providers/authProvider';
export { LoginContainer } from './components/LoginContainer';
export { useChangePassword } from './hooks/useChangePassword';
export { useSessionStore } from './store/sessionStore';
export type { UserIdentityType } from './types/auth.types';
```

### Custom Hooks (`hooks/`)

| Hook | Responsabilidad única | Endpoint / resource | Refine hook |
| :--- | :--- | :--- | :--- |
| `useChangePassword` | Enviar cambio de contraseña propio y mapear errores de campo. | `POST /auth/change-password` | `useCustomMutation` |

> `login`, `logout`, `getIdentity` y la verificación de sesión viven en el `authProvider` de Refine, no en hooks sueltos. El **refresh silencioso al cargar la app** (el access vive en memoria y se pierde al recargar) lo dispara el `check`/interceptor: intenta `refresh` con `withCredentials` una vez; si falla, va a login.

### Resources y Páginas (`src/pages/`)
<!-- Dumb pages: solo importan el contenedor. -->

| Ruta / Resource | Tipo | Página (`src/pages/`) | Componente Contenedor | Roles permitidos |
| :--- | :--- | :--- | :--- | :--- |
| `/login` | Pública | `LoginPage.tsx` | `LoginContainer` | Público |
| `/account/change-password` | Protegida | `ChangePasswordPage.tsx` | `ChangePasswordForm` (vía contenedor) | Jefe, Supervisor, Responsable de ruta, Usuario |

> Inputs ≥16px en iOS (evita zoom de Safari); áreas táctiles ≥44px; tokens del theme (índigo), cero hex literales; errores de campo con el componente `FieldError` compartido (`src/shared/`) alimentado por Zod.

---

## 4. Configuración y DevSecOps

### Gestión de Secretos
- **Backend (`backend/.env.example`):**
  - `JWT_SIGNING_KEY` — clave de firma de SimpleJWT (Secret Manager en producción).
  - `CORS_ALLOWED_ORIGINS` — origen del frontend (dominio de Vercel; nunca `*` con credenciales).
  - `AUTH_COOKIE_DOMAIN` — dominio de la cookie de refresh (`.midominio.com` si subdominios; vacío en local).
  - `AUTH_COOKIE_SAMESITE` — `Lax` (subdominios mismo root) o `None` (cross-site de plataforma).
  - `LOGIN_RATELIMIT` — umbral de intentos de login (constante centralizada, no literal).
- **Frontend (`frontend/.env.example`):**
  - `VITE_API_BASE_URL` — base del backend (solo valor no sensible).

### Seguridad Proactiva
- **Análisis Estático Backend:** `ruff`, `mypy --strict`, `bandit` limpios en `apps/accounts/`.
- **Análisis Estático Frontend:** `eslint` y `tsc --noEmit` limpios en `src/features/auth/`.
- **SCA (Dependencias):** `pip-audit`, `npm audit`/Dependabot y `trivy` sobre las nuevas dependencias y la imagen.
- **Estrategia de tokens / CSRF:** access en memoria (cabecera `Authorization` → endpoints de negocio inmunes a CSRF); refresh en cookie `httpOnly` + `Secure`, `Path` acotado a `/auth`. Si el despliegue queda cross-site (`SameSite=None`), añadir protección CSRF double-submit en `refresh` y `logout`. `CORS_ALLOW_CREDENTIALS = True`. **Decisión registrada en README/ADR** con la recomendación de migrar a subdominios del dominio propio.
- **`SIMPLE_JWT`:** access 15 min, refresh 7 d, rotación activada, blacklist tras rotación.
- **Política de contraseñas:** validadores de Django (longitud, similitud, comunes); mensajes en español por `LANGUAGE_CODE`.

---

## 5. Cambios Estructurales

### Nuevas Dependencias
<!-- djangorestframework-simplejwt ya viene del bootstrap (F0); aquí se habilita su app de blacklist. -->

| Paquete | Versión | Entorno | Justificación |
| :--- | :--- | :--- | :--- |
| `rest_framework_simplejwt.token_blacklist` | (incluido en djangorestframework-simplejwt, ya pineado) | Backend | App de blacklist para logout, rotación y la desactivación de F3. Se añade a `INSTALLED_APPS`, no es dependencia nueva. |
| `django-ratelimit` | pineada en `uv.lock` | Backend | Rate limiting del endpoint de login (declarado en el stack del config). |

### Migraciones de Base de Datos
Migración inicial de `accounts` (CreateModel `User`) + migraciones de `token_blacklist`. Es la primera del proyecto; no hay datos existentes ni data migration. Reverse funcional verificado con `migrate accounts zero`.
