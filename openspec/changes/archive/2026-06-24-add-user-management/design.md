# Diseño Técnico: add-user-management

## 1. Capa de Datos (PostgreSQL + Django ORM)

### Tablas e Índices

| Tabla | Índice / Constraint | Tipo | Justificación |
| :--- | :--- | :--- | :--- |
| `accounts_user` | `must_change_password` | columna `boolean not null default false` | Sin índice: no se filtra por este campo; se lee del registro ya cargado por id en autenticación. |
| `accounts_user` | `username` (existente, F1) | `unique` | Identificador único del usuario; el escenario de duplicado (400) se apoya en él. |
| `authz_profile` | `deleted_at` (existente, F2) | `partial-unique` sobre `name WHERE deleted_at IS NULL` | Soft delete clase 2 ya definido en F2; F3 no lo altera, solo lo consume en la baja. |

### Modelo Django

```python
# Modelo Django — Tabla: accounts_user (MODIFICA el modelo de F1; no se crea tabla nueva)
# Mixins existentes de F1 (AbstractUser + TimeStampedMixin). NO es catálogo: sin SoftDeleteMixin.

class User(AbstractUser):           # F1; F2 añadió FK profile
    # ... campos de F1/F2 ...
    must_change_password = models.BooleanField(
        default=False,
        help_text="Obliga al usuario a cambiar su contraseña en el primer acceso tras un reset administrativo.",
    )
```

`authz.Profile` ya existe (F2): F3 **no añade modelo**; añade endpoints de administración y la regla
de baja con usuarios asignados. La auditoría usa el modelo de log + el decorador `@audit` del
bootstrap; no se crea modelo nuevo.

### Migración Django

```
# Archivo: accounts/migrations/000X_user_must_change_password.py
# operations: AddField(model_name="user", name="must_change_password", BooleanField(default=False))
# Generar con: python manage.py makemigrations accounts
# Aplicar con:  python manage.py migrate
# Reverse de prueba: python manage.py migrate accounts <migracion_anterior>   # elimina la columna, sin pérdida de datos
```

### Impacto en Invariantes del Sistema

- **Período cerrado:** No aplica — F3 no crea documentos con fecha.
- **Kardex FIFO / append-only:** No se afecta — F3 no genera movimientos de Kardex.
- **Doble costeo:** No se afecta.
- **Cuadre de ruta:** No se afecta.
- **Snapshot inmutable de entrega:** No se afecta.
- **Nota de crédito vinculada:** No se afecta.
- **Soft delete (3 clases):** `Profile` = catálogo (soft delete clase 2, ya en F2); `User` = ficha de identidad → se **desactiva** (`is_active=False`), no se borra ni usa `deleted_at`.
- **Trazabilidad:** No se altera Ingreso → Kardex → Entrega → Cobro / Ingreso → CxP → Pago.

---

## 2. Capa de API y Contratos (Fuente de Verdad)

### Diccionario de Datos Vivo

| Entidad | Campo | Tipo (Py / TS) | Descripción (Uso y Propósito) | Restricciones |
| :--- | :--- | :--- | :--- | :--- |
| `User` | `username` | `str / string` | Identificador único de acceso (F1). | Unique, requerido |
| `User` | `profile` | `UUID / string` | Perfil que resuelve la autorización (F2). | FK `authz.Profile` activo, requerido |
| `User` | `role` | `str / string` | Rol nominal sincronizado al perfil (no autoriza). | Enum de roles del sistema |
| `User` | `is_active` | `bool / boolean` | Estado de activación; `False` impide autenticar. | Default `True` |
| `User` | `must_change_password` | `bool / boolean` | Flag de cambio forzado en el primer acceso. | Default `False`, not null |
| `ResetPassword` (write) | `temporary_password` | `str / string` | Contraseña temporal definida por el admin (opcional). | Write-only, cumple política; mutuamente excluyente con `generate` |
| `ResetPassword` (write) | `generate` | `bool / boolean` | Si `True`, el sistema genera la temporal. | Default `False` |
| `ResetPassword` (read) | `temporary_password` | `str / string` | Temporal generada, devuelta una sola vez. | Read-only, solo en la respuesta del reset |

### Backend: Serializers DRF

```python
# Entrada (write) y salida (read) separadas. Cada campo con help_text para el OpenAPI.
# UserAdminWriteSerializer  — crear/editar usuario (username, profile, datos básicos)
# UserAdminReadSerializer   — salida (sin password; expone is_active, profile, must_change_password)
# ResetPasswordWriteSerializer — temporary_password (write-only, opcional) XOR generate
# ResetPasswordReadSerializer  — temporary_password generada (read-only, una sola vez)
# ProfileAdminWriteSerializer  — permisos por (módulo, acción) del catálogo + flags (editar)
# (La asignación de perfil reutiliza el serializer/endpoint assign-profile de F2, extendido en services.)
# El ViewSet NO contiene lógica: delega en services/.
```

### Frontend: Tipos generados (Zod + TypeScript)

```typescript
// Generado desde el OpenAPI de DRF con `npm run codegen` — NO editar a mano.
// userAdminSchema, resetPasswordSchema, profileAdminSchema (Zod) + z.infer<>.
// La asignación de perfil reutiliza el assignProfileSchema generado en F2.
// Formularios con React Hook Form + zodResolver(...).
```

### Endpoints de DRF

| Verbo | Ruta | Write Serializer | Read Serializer | Códigos HTTP | Roles (perfil) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/auth/users` | — | `UserAdminRead` | `200/403` | Jefe |
| `POST` | `/auth/users` | `UserAdminWrite` | `UserAdminRead` | `201/400/403` | Jefe |
| `PATCH` | `/auth/users/{id}` | `UserAdminWrite` | `UserAdminRead` | `200/400/403/404` | Jefe |
| `POST` | `/auth/users/{id}/deactivate` | — | `UserAdminRead` | `200/403/404` | Jefe |
| `POST` | `/auth/users/{id}/reactivate` | — | `UserAdminRead` | `200/403/404` | Jefe |
| `POST` | `/auth/users/{id}/reset-password` | `ResetPasswordWrite` | `ResetPasswordRead` | `200/400/403/404` | Jefe |
| `POST` | `/authz/users/{id}/assign-profile` *(F2, extendido)* | `AssignProfileWrite` (F2) | `UserAdminRead` | `200/400/403/404` | Jefe |
| `PATCH` | `/authz/profiles/{id}` | `ProfileAdminWrite` | `ProfileRead` (F2) | `200/400/403/404` | Jefe |
| `DELETE` | `/authz/profiles/{id}` | — | — | `204/403/404/409` | Jefe |

> `POST /authz/profiles` (crear), `GET /authz/profiles` (listar) y `POST /authz/users/{id}/assign-profile`
> ya existen en F2. F3 **completa** `PATCH` (editar permisos) y `DELETE` (baja) de perfiles, y **extiende
> el comportamiento** de `assign-profile` (sincronizar `role` + blacklist de refresh) sin crear un
> endpoint nuevo de cambio de perfil. Ver `## MODIFIED Requirements` en el delta de access-control.

### Servicio de Negocio

| Servicio | Método | Responsabilidad única | Transaccional |
| :--- | :--- | :--- | :--- |
| `apps/accounts/services.py` | `create_user()` | Crea usuario, asigna perfil, sincroniza `role`. | Sí |
| `apps/accounts/services.py` | `update_user()` | Edita datos básicos del usuario. | Sí |
| `apps/accounts/services.py` | `reset_password()` | Fija temporal (dada o generada), activa flag, blacklist de refresh. | Sí |
| `apps/accounts/services.py` | `deactivate_user()` / `reactivate_user()` | Cambia `is_active`; al desactivar, blacklist de refresh. | Sí |
| `apps/authz/services.py` | `assign_profile()` *(F2, extendido)* | Cambia perfil, **sincroniza `role` + blacklist de refresh** (delta de F3). | Sí |
| `apps/authz/services.py` | `update_profile_permissions()` | Persiste permisos por (módulo, acción) del catálogo + flags. | Sí |
| `apps/authz/services.py` | `deactivate_profile()` | Soft delete clase 2 validando que no haya usuarios asignados. | Sí |

> Todos los métodos aplican `@audit(action, entity)`. F3 no tiene cálculo financiero: no hay
> funciones puras en `utils/`.

> **Decisión de autorización (KISS):** los endpoints admin de F3 reutilizan el módulo de permisos
> `access-control` de F2 con sus acciones `read/create/update`, en vez de introducir un módulo
> `user-management` nuevo (que obligaría a una data migration mutando los perfiles semilla de F2). El
> perfil Jefe ya posee `read/create/update`; Supervisor (solo `read`) y Usuario (sin permisos) caen
> en 403, que es justo lo que exigen los scenarios. La baja de perfil (soft-delete = cambio de
> estado) mapea a `update`. Así F3 no toca el catálogo ni el seed: el único cambio de datos es el
> campo `must_change_password`.

---

## 3. Capa de Presentación (UI — React + Refine)

### Árbol de Directorios de las Features

```
src/features/users/
├── components/
│   ├── UsersAdminConsole.tsx     # Contenedor: orquesta hooks y sub-componentes
│   ├── UserForm.tsx              # Presentacional: alta/edición (RHF + zodResolver)
│   └── ResetPasswordDialog.tsx   # Presentacional: reset + muestra temporal una vez
├── hooks/
│   ├── useUsersList.ts           # useList de Refine
│   ├── useUserMutations.ts       # useCreate/useUpdate
│   └── useUserAdminActions.ts    # useCustomMutation: deactivate/reactivate/reset/assign-profile
├── types/
│   └── users.types.ts            # Re-exporta tipos generados del OpenAPI
└── index.ts                      # Contrato público

src/features/profiles/
├── components/
│   ├── ProfilesAdminConsole.tsx  # Contenedor
│   ├── PermissionMatrix.tsx      # Presentacional: matriz (módulo × acción) + flags
│   └── ProfileForm.tsx           # Presentacional
├── hooks/
│   ├── useProfilesList.ts        # useList
│   └── useProfileAdminActions.ts # useUpdate (editar) / useCustomMutation (baja)
├── types/
│   └── profiles.types.ts
└── index.ts

src/features/auth/                # MODIFICA F1
└── components/
    └── ForcePasswordChangeGuard.tsx  # Bloquea navegación si me.must_change_password
```

### Custom Hooks

| Hook | Responsabilidad única | Endpoint / resource | Refine hook |
| :--- | :--- | :--- | :--- |
| `useUsersList` | Listar usuarios. | `GET /auth/users` / `users` | `useList` |
| `useUserMutations` | Crear / editar usuario. | `POST·PATCH /auth/users` / `users` | `useCreate` / `useUpdate` |
| `useUserAdminActions` | Acciones de ciclo de vida (deactivate/reactivate/reset; asignar perfil vía endpoint de F2). | `POST /auth/users/{id}/...` · `POST /authz/users/{id}/assign-profile` | `useCustomMutation` |
| `useProfilesList` | Listar perfiles. | `GET /authz/profiles` / `profiles` | `useList` |
| `useProfileAdminActions` | Editar permisos / dar de baja. | `PATCH·DELETE /authz/profiles/{id}` | `useUpdate` / `useCustomMutation` |

### Resources y Páginas (`src/pages/`)

| Ruta / Resource | Tipo | Página | Componente Contenedor | Roles permitidos |
| :--- | :--- | :--- | :--- | :--- |
| `/admin/users` | Protegida | `UsersAdminPage.tsx` | `UsersAdminConsole` | Jefe |
| `/admin/profiles` | Protegida | `ProfilesAdminPage.tsx` | `ProfilesAdminConsole` | Jefe |
| `/auth/change-password` | Protegida | (F1) | (F1) + `ForcePasswordChangeGuard` | Todos (forzado si flag) |

> El gating por perfil se resuelve en el `accessControlProvider` de Refine (F2). El
> `ForcePasswordChangeGuard` consume `GET /auth/me`: si `must_change_password`, redirige a
> `/auth/change-password` y bloquea toda otra ruta. Estados vacío/carga/error/éxito obligatorios;
> cero hex literales; inputs ≥16px iOS; áreas táctiles ≥44px.

---

## 4. Configuración y DevSecOps

### Gestión de Secretos

- **Backend:** F3 **no introduce variables de entorno nuevas**. La generación de contraseñas temporales usa el RNG criptográfico de la stdlib; no hay claves nuevas. Las temporales MUST NOT loggearse.
- **Frontend:** Sin variables `VITE_*` nuevas.

### Seguridad Proactiva

- **Backend:** `ruff`, `mypy --strict`, `bandit` limpios en `apps/accounts` y `apps/authz`.
- **Frontend:** `eslint` y `tsc` limpios en `src/features/users`, `src/features/profiles` y el guard de auth.
- **SCA:** F3 no añade dependencias; `pip-audit` y `npm audit` deben seguir limpios.

---

## 5. Cambios Estructurales

### Nuevas Dependencias

Ninguna. F3 se resuelve con la stack existente (DRF, SimpleJWT, Refine, RHF + Zod).

### Migraciones de Base de Datos

`AddField accounts.User.must_change_password` (boolean, default `False`, not null). Reverse funcional
(elimina la columna). No requiere data migration: el default cubre las filas existentes.
