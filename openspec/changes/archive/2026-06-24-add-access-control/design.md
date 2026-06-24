# Diseño Técnico: add-access-control

## 1. Capa de Datos (PostgreSQL + Django ORM)

> **App `authz`** (no `access_control`): nombre corto en inglés, SRP, y evita colisionar con los
> permisos nativos de Django (`django.contrib.auth`). La capability OpenSpec es `access-control`.

### Tablas e Índices

| Tabla | Índice / Constraint | Tipo | Justificación |
| :--- | :--- | :--- | :--- |
| `profiles` | `name` | `partial-unique` (`WHERE deleted_at IS NULL`) | Nombre único entre perfiles vivos; soft delete clase 2 permite reutilizar el nombre de un perfil dado de baja. |
| `profiles` | `deleted_at` | `btree` | El manager por defecto filtra por `deleted_at IS NULL`; índice para no escanear la tabla. |
| `accounts_user` | `profile_id` | `fk` (`on_delete=PROTECT`) | Asignación usuario→perfil; PROTECT impide borrar un perfil en uso (refuerza la baja de catálogo). |

### Modelo Django

```python
# Modelo Django — Tabla: profiles  (app: authz)
# Base: SoftDeleteModel (F1, apps.common.models) que ya hereda TimeStampedModel.
# (Las clases reales se llaman ...Model, no ...Mixin.)

import uuid
from django.db import models
from apps.common.models import SoftDeleteModel


class Profile(SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text="Nombre único del perfil")
    description = models.CharField(max_length=255, blank=True, help_text="Descripción opcional")
    # permissions: {modulo: [accion, ...]} validado contra apps/authz/catalog.py
    permissions = models.JSONField(default=dict, help_text="Permisos por (módulo, acción) del catálogo")
    # visible_sensitive_fields: ["recurso.campo", ...] validado contra el registro de campos sensibles
    visible_sensitive_fields = models.JSONField(
        default=list, help_text="Campos sensibles que el perfil puede ver"
    )
    auto_approval = models.BooleanField(default=False, help_text="Capacidad de auto-aprobación")

    class Meta:
        db_table = "profiles"
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                condition=models.Q(deleted_at__isnull=True),
                name="uq_profile_name_active",
            )
        ]


# Cambio en accounts.User (F1): se añade el FK al perfil.
# class User(AbstractUser):
#     role = models.CharField(...)            # F1 — clasificación nominal
#     profile = models.ForeignKey(
#         "authz.Profile", null=True, on_delete=models.PROTECT, related_name="users",
#         help_text="Perfil que gobierna la autorización (fuente de verdad, no el role)",
#     )
```

> **Decisión de almacenamiento (KISS/YAGNI):** los permisos y los campos visibles se guardan como
> `JSONField` validados contra el catálogo central, **no** en tablas normalizadas
> `ProfilePermission`/`ProfileField`. El catálogo (`catalog.py`) es la única fuente de la estructura;
> normalizar añadiría dos tablas y joins sin un segundo caso de uso que lo justifique (proyecto de un
> dev). La validación de claves contra el catálogo vive en el serializer/servicio.

### Migración Django

```
# Archivo: apps/authz/migrations/0001_initial.py
#   operations: CreateModel(Profile) + AddConstraint(uq_profile_name_active)
# Archivo: apps/authz/migrations/0002_seed_system_profiles.py
#   operations: RunPython(seed_system_profiles, remove_system_profiles)   # reverse REQUIRED
# Archivo: apps/accounts/migrations/000X_add_profile_fk.py
#   operations: AddField(User.profile, FK->authz.Profile, null=True, on_delete=PROTECT)
#   + RunPython(backfill_user_profiles, noop_reverse)  # backfillea cada user a su perfil homónimo
#
# Generar:  python manage.py makemigrations authz accounts
# Aplicar:  python manage.py migrate
# Reverse:  python manage.py migrate authz zero   (elimina seed + tabla; reversible)
```

### Impacto en Invariantes del Sistema
- **Período cerrado:** N/A — `Profile` es catálogo sin fecha de documento.
- **Kardex FIFO / append-only:** No se afecta. No se tocan saldos, lotes ni movimientos.
- **Doble costeo:** No se afecta. (F2 entrega el *mecanismo* de invisibilidad del campo costo; el campo concreto es F12.)
- **Cuadre de ruta:** N/A.
- **Snapshot inmutable de entrega:** N/A.
- **Nota de crédito vinculada:** N/A.
- **Soft delete (3 clases):** `Profile` = **clase 2** (catálogo): `deleted_at` + manager filtrado + índice único parcial. `User` conserva su modelo de F1 (no soft delete).
- **Trazabilidad:** No se altera Ingreso → Kardex → Entrega → Cobro / Ingreso → CxP → Pago.

---

## 2. Capa de API y Contratos (Fuente de Verdad)

### Diccionario de Datos Vivo

| Entidad | Campo | Tipo (Py / TS) | Descripción (Uso y Propósito) | Restricciones |
| :--- | :--- | :--- | :--- | :--- |
| `Profile` | `id` | `UUID / string` | Identificador del perfil | PK, read-only |
| `Profile` | `name` | `str / string` | Nombre único del perfil | unique (activos), max 100, requerido |
| `Profile` | `description` | `str / string` | Descripción opcional | blank, max 255 |
| `Profile` | `permissions` | `dict / Record<string,string[]>` | Permisos por módulo→acciones | claves ∈ catálogo |
| `Profile` | `visible_sensitive_fields` | `list / string[]` | Campos sensibles visibles (`"recurso.campo"`) | valores ∈ registro |
| `Profile` | `auto_approval` | `bool / boolean` | Capacidad de auto-aprobación | default `false` |
| `User` | `profile` | `UUID / string` | Perfil asignado (autoridad de autorización) | FK, null en DB, PROTECT |

### Backend: Serializers DRF

```python
# apps/authz/serializers.py
# ProfileReadSerializer  — salida (contrato de lectura)
# ProfileWriteSerializer — entrada (validación: name único + permissions/fields ∈ catálogo)
# AssignProfileSerializer — entrada del endpoint de asignación (solo profile_id)
# SensitiveFieldsMixin   — mixin que OMITE del output los campos no visibles para el perfil

from rest_framework import serializers
from apps.authz.models import Profile


class SensitiveFieldsMixin:
    """Elimina del representation los campos sensibles que el perfil del usuario no puede ver.
    No los marca read-only: los omite por completo (clave + valor)."""

    sensitive_fields: dict[str, str] = {}  # {field_name: "recurso.campo"} declarado por serializer

    def to_representation(self, instance):
        data = super().to_representation(instance)
        profile = getattr(self.context.get("request").user, "profile", None)
        visible = set(getattr(profile, "visible_sensitive_fields", []) or [])
        for field_name, registry_key in self.sensitive_fields.items():
            if registry_key not in visible:
                data.pop(field_name, None)
        return data


class ProfileReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["id", "name", "description", "permissions",
                  "visible_sensitive_fields", "auto_approval"]


class ProfileWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["name", "description", "permissions",
                  "visible_sensitive_fields", "auto_approval"]
    # validate_permissions / validate_visible_sensitive_fields: claves ∈ catalog.py (400 si no)


class AssignProfileSerializer(serializers.Serializer):
    profile_id = serializers.UUIDField(help_text="Perfil activo a asignar al usuario")
```

### Frontend: Tipos generados (Zod + TypeScript)

```typescript
// Generado desde el OpenAPI de DRF con `npm run codegen` — NO editar a mano.
// profileSchema (Zod) y ProfileType = z.infer<typeof profileSchema>
// Los campos sensibles de OTROS recursos (p. ej. cost en F12) se generan como OPCIONALES
//   (.optional()) porque el serializer puede omitirlos según el perfil; el front MUST tolerar su
//   ausencia sin romper. UserIdentityType extiende la identidad de F1 con `profile`.
```

> **Contrato OpenAPI — campos opcionales:** como el serializer omite campos según perfil, un mismo
> recurso puede responder con o sin un campo sensible. El `schema.yml` MUST declarar esos campos como
> **opcionales** (`required: false`), de modo que el tipo/Zod generado los marque opcionales y el
> front no asuma su presencia.

### Endpoints de DRF

| Verbo | Ruta | Write Serializer | Read Serializer | Códigos HTTP | Roles |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/authz/profiles` | — | `ProfileReadSerializer` | `200/401/403` | Jefe, Supervisor (permiso `access-control:read`) |
| `GET` | `/authz/profiles/{id}` | — | `ProfileReadSerializer` | `200/401/403/404` | Jefe, Supervisor |
| `POST` | `/authz/profiles` | `ProfileWriteSerializer` | `ProfileReadSerializer` | `201/400/401/403` | Jefe |
| `POST` | `/authz/users/{id}/assign-profile` | `AssignProfileSerializer` | `UserIdentityReadSerializer` | `200/400/401/403/404` | Jefe |
| `GET` | `/auth/me` *(modificado de F1)* | — | `UserIdentityReadSerializer` (+`profile`) | `200/401` | todos |

> No se diseña CRUD completo: no hay `PUT/PATCH/DELETE` de perfiles en F2 (la edición/baja desde UI es
> F3). `POST /authz/profiles` se incluye porque el seed y los tests requieren creación, y el escenario
> de "nombre duplicado" la valida; las transiciones administrativas plenas se difieren.

### Servicio de Negocio

| Servicio | Método | Responsabilidad única | Transaccional |
| :--- | :--- | :--- | :--- |
| `authz/services.py` | `resolve_permission(profile, module, action)` | Resuelve si el perfil permite `(módulo, acción)` → bool | No |
| `authz/services.py` | `visible_fields_for(profile, resource)` | Construye el set de campos visibles del perfil para un recurso | No |
| `authz/services.py` | `assign_profile(user, profile)` | Asigna un perfil a un usuario (con `@audit("UPDATE", "User")`) | Sí |
| `authz/services.py` | `seed_system_profiles()` | Crea/actualiza idempotentemente los 4 perfiles semilla | Sí |

> **Permission classes** (`apps/authz/permissions.py`): `HasModulePermission` lee `(module, action)`
> declarados en el view y delega en `resolve_permission`; al denegar devuelve `403 {detail}` genérico.

---

## 3. Capa de Presentación (UI — React + Refine)

> **Sin pantallas nuevas en F2.** No hay administración de perfiles (es F3). Esta fase **extiende la
> feature `auth`** existente para consumir el perfil y exponer helpers de gating como **defensa
> secundaria** (la autoritativa es el backend). Solo se listan los archivos que F2 crea o modifica.

### Árbol de Directorios de la Feature

```
src/features/auth/                       # feature existente (F1) — se EXTIENDE
├── hooks/
│   └── usePermissions.ts                # NUEVO: canDo(module,action) / canSee(resource,field)
├── store/
│   └── session.store.ts                 # MODIFICADO: la sesión incluye `profile`
├── types/
│   └── identity.types.ts                # MODIFICADO: re-exporta UserIdentityType (+profile) generado
└── index.ts                             # MODIFICADO: exporta usePermissions
```

### Contrato Público (`index.ts`)

```typescript
// src/features/auth/index.ts — exports explícitos (no export *)
export { usePermissions } from './hooks/usePermissions';
export { useSessionStore } from './store/session.store';
export type { UserIdentityType } from './types/identity.types';
```

### Custom Hooks (`hooks/`)

| Hook | Responsabilidad única | Endpoint / resource | Refine hook |
| :--- | :--- | :--- | :--- |
| `usePermissions` | Expone `canDo(module, action)` y `canSee(resource, field)` derivados del perfil de la sesión | `GET /auth/me` / resource `auth` | `useGetIdentity` |

> El gating se aplica en componentes **ya existentes** (oculta acciones/columnas). No se crean
> componentes ni páginas nuevas; por eso no hay tablas de "Componentes" ni de "Resources/Páginas".
> Los 403 se manejan como aviso limpio (`{detail}`) en el `notificationProvider` de F1.

### Resources y Páginas (`src/pages/`)

| Ruta / Resource | Tipo | Página (`src/pages/`) | Componente Contenedor | Roles permitidos |
| :--- | :--- | :--- | :--- | :--- |
| — | — | (ninguna nueva en F2) | — | — |

---

## 4. Configuración y DevSecOps

### Gestión de Secretos
- **Backend:** No se introducen variables de entorno nuevas (reutiliza la firma JWT de F1). Nada que
  añadir a `backend/.env.example`.
- **Frontend:** Sin nuevas variables `VITE_*`.

### Seguridad Proactiva
- **Análisis Estático Backend:** `ruff`, `mypy --strict` y `bandit` limpios en `apps/authz/` y en el
  cambio de `apps/accounts/`. Especial atención: el `SensitiveFieldsMixin` MUST omitir (no enmascarar)
  y los 403 MUST devolver `{detail}` genérico sin filtrar qué permiso faltó.
- **Análisis Estático Frontend:** `eslint` y `tsc` limpios en `src/features/auth/`.
- **SCA (Dependencias):** Sin dependencias nuevas previstas; si se añadiera alguna, `pip-audit`
  (Python) y `npm audit` (Node) deben quedar limpios. **Trivy** escanea la imagen Docker del backend
  en CI (no hay cambios en el `Dockerfile` en esta fase, pero el gate se mantiene).

---

## 5. Cambios Estructurales

### Nuevas Dependencias
Ninguna. El motor de autorización se implementa con permission classes y serializers de DRF (ya en el
stack); no se añade ninguna librería RBAC externa (KISS/YAGNI).

### Ajuste del pipeline de codegen (Frontend)
`openapi-zod-client@1.18.3` emite records al estilo **Zod v3** (`z.record(value)`), pero el proyecto
fija **Zod v4**, donde `z.record` exige clave y valor. El `DictField` de `permissions` es el primer
tipo-mapa que pasa por el codegen y dispara la incompatibilidad. Se añade un paso fijo y determinista
al script `codegen` de `package.json` (`node codegen/fix-zod-v4.mjs`) que reescribe `z.record(` →
`z.record(z.string(), ` sobre el `zod.ts` generado. No es edición manual del artefacto (es parte del
pipeline) ni una dependencia nueva (usa builtins de Node). Reaparecerá en cada fase con tipos-mapa.

### Ajuste de infraestructura compartida (Backend)
`apps/common/models.py` (F1): se generalizan `SoftDeleteQuerySet`/`SoftDeleteManager` con un `TypeVar`
acotado para que los catálogos que hereden el mixin obtengan managers tipados a su clase (lo exige
`mypy --strict`; `Profile` es el primer consumidor). Cambio de tipado, sin cambio de comportamiento
ni de esquema; la suite de `apps/common` se reverifica intacta.

### Migraciones de Base de Datos
- `authz`: `CreateModel(Profile)` + constraint único parcial + data migration de seed (con `reverse_code`).
- `accounts`: `AddField(User.profile)` (FK nullable, PROTECT) + data migration de backfill a perfiles
  homónimos. Ambas reversibles (`migrate authz zero` / `migrate accounts <anterior>`).
