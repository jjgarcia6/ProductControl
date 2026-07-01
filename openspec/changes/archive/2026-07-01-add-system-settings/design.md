# Diseño Técnico: add-system-settings

<!-- DIP: las capas se diseñan de abajo hacia arriba: Datos → API → UI. -->

## 1. Capa de Datos (PostgreSQL + Django ORM)

### Tablas e Índices

| Tabla | Índice / Constraint | Tipo | Justificación |
| :--- | :--- | :--- | :--- |
| `system_settings` | `lock` | unique | segunda fila imposible (singleton) |
| `system_settings` | `Q(lock=True)` | check constraint | `lock` no puede ser distinto de `True` |

### Modelo Django

- **App `system_settings`** — `SystemSettings(TimeStampedModel)`:
  - `costing_nominal_enabled` (`BooleanField`, default `True`) — muestra costo nominal en reportes.
  - `costing_effective_enabled` (`BooleanField`, default `True`) — muestra costo efectivo en reportes.
  - `lock` (`BooleanField`, default `True`, `unique=True`, `editable=False`) — centinela del
    singleton.
  - `CheckConstraint(check=Q(lock=True), name="system_settings_singleton_lock")`.
- **NO** hereda `SoftDeleteModel` (excepción documentada: singleton de configuración; no es catálogo,
  documento ni ficha). Hereda solo `TimeStampedModel`.

### Migración Django

- `makemigrations system_settings`: `CreateModel` + `AddConstraint`. Reversible (upgrade + downgrade).
- **Data migration (`system_settings`):** `RunPython(forwards, backwards)` crea la fila única
  (`lock=True`, ambos toggles `True`); reverse elimina la fila.
- **Data migration (`authz`):** `RunPython(forwards, backwards)` fusiona `system-settings` en
  `permissions` de los perfiles semilla existentes (`JEFE` → `[read, update]`, `SUPERVISOR` →
  `[read]`), idempotente; reverse retira solo la clave `system-settings` sin pisar otros permisos.

### Impacto en Invariantes del Sistema

- **Período cerrado:** N/A — sin documentos con fecha (por eso F8 no depende de F9).
- **Kardex FIFO / append-only:** no se toca.
- **Doble costeo:** los flags gobiernan la **presentación** de cada base. El cálculo paralelo
  permanece invariante; F8 no recalcula. Se añade el sub-invariante "al menos una base activa".
- **Cuadre de ruta / snapshot / nota de crédito:** no aplican.
- **Soft delete (3 clases):** N/A — singleton (excepción explícita; hereda solo `TimeStampedModel`).
- **Trazabilidad:** no se altera.

---

## 2. Capa de API y Contratos

### Diccionario de Datos Vivo

| Entidad | Campo | Tipo (Py / TS) | Descripción | Restricciones |
| :--- | :--- | :--- | :--- | :--- |
| `SystemSettings` | `costing_nominal_enabled` | `bool / boolean` | muestra costo nominal en reportes | no ambos `false` |
| `SystemSettings` | `costing_effective_enabled` | `bool / boolean` | muestra costo efectivo en reportes | no ambos `false` |

> `lock` es interno (centinela del singleton) y MUST NOT exponerse en la API.

### Backend: Serializers DRF

- `SystemSettingsReadSerializer` (salida): expone los dos toggles + marcas de tiempo; nunca `lock`.
- `SystemSettingsUpdateSerializer` (entrada, `partial`): `validate()` cruzado que rechaza ambas bases
  en `False` → `non_field_errors`. Cada campo con `help_text` para el OpenAPI.
- El view/serializer NO contiene lógica de negocio: delega en `services.py`.

### Frontend: Tipos generados (Zod + TypeScript)

- `SystemSettings` (Zod + TS) se GENERA del OpenAPI de DRF con `npm run codegen`. MUST NOT escribirse
  a mano. El formulario usa React Hook Form + `zodResolver`.

### Endpoints de DRF

| Verbo | Ruta | Write | Read | Códigos HTTP | Roles (perfil) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/system-settings` | — | `SystemSettingsRead` | 200/401/403 | Jefe, Supervisor |
| `PATCH` | `/system-settings` | `SystemSettingsUpdate` | `SystemSettingsRead` | 200/400/401/403 | Jefe |

> El recurso es un singleton: la ruta no lleva `id`. El view resuelve la instancia vía
> `get_settings()`. Protegido con `HasModulePermission` (F2) y `required_permissions` por método
> (`GET` → `("system-settings","read")`, `PATCH` → `("system-settings","update")`).

### Servicio de Negocio

| Servicio | Método | Responsabilidad única | Transaccional |
| :--- | :--- | :--- | :--- |
| `system_settings/services.py` | `get_settings()` | retornar el singleton (`get_or_create(lock=True)`); consumo directo de otras fases | No |
| `system_settings/services.py` | `update_settings()` | validar "≥1 base activa", aplicar toggles, auditar con `@audit` | Sí |

---

## 3. Capa de Presentación (UI — React + Refine)

### Árbol de Directorios de la Feature

```text
src/features/system-settings/
├── components/
│   ├── SystemSettingsContainer.tsx   # orquesta hook + subcomponente
│   └── SystemSettingsForm.tsx        # presentacional: los dos toggles
├── hooks/
│   └── useSystemSettings.ts
├── types/
│   └── system-settings.types.ts      # re-exporta tipos generados del OpenAPI
└── index.ts                          # contrato público explícito
```

### Contrato Público (`index.ts`)

```typescript
export { SystemSettingsContainer } from './components/SystemSettingsContainer';
export { useSystemSettings } from './hooks/useSystemSettings';
export type { SystemSettingsType } from './types/system-settings.types';
```

### Custom Hooks

| Hook | Responsabilidad única | Endpoint / resource | Refine hook |
| :--- | :--- | :--- | :--- |
| `useSystemSettings` | leer y actualizar el singleton | `/system-settings` | `useCustom` (GET) + `useCustomMutation` (PATCH) |

> Al ser singleton sin `id`, se usa `useCustom`/`useCustomMutation` (no `useOne`/`useUpdate` de
> recurso con id).

### Resources y Páginas (`src/pages/`)

| Ruta | Tipo | Página | Contenedor | Perfil (canDo) |
| :--- | :--- | :--- | :--- | :--- |
| `/system-settings` | Protegida (`lazy`) | `SystemSettingsPage.tsx` | `SystemSettingsContainer` | `system-settings.read` (ver) / `update` (editar) |

- Ruta declarada en `App.tsx` con `<Authenticated>` + `ForcePasswordChangeGuard` y
  `lazy(() => import(...))` (**no** array `resources` de Refine, per convención del proyecto en
  `config.yaml`); gating en componente con `usePermissions().canDo('system-settings', acción)`. Página
  *dumb*.
- El error cruzado "al menos una base activa" se muestra como **aviso general** (banner/toast), no
  mapeado a un control. Estados vacío/carga/error/éxito; tokens del theme; toggles accesibles (rol,
  foco, contraste AA claro/oscuro); áreas táctiles ≥44px.

---

## 4. Configuración y DevSecOps

### Gestión de Secretos

- Sin variables de entorno nuevas (backend ni frontend); nada que añadir a `.env.example` ni a GCP
  Secret Manager.

### Seguridad Proactiva

- **Backend:** salida limpia de `ruff`, `mypy --strict` y `bandit` sobre `apps/system_settings`.
  Verificar que `lock` no se expone en la API.
- **Frontend:** salida limpia de `eslint` y `tsc` sobre `src/features/system-settings`.
- **SCA:** sin dependencias nuevas; se corren `pip-audit` y `npm audit` igualmente.

---

## 5. Cambios Estructurales — Modificaciones puntuales

> Ediciones dirigidas sobre archivos existentes del repo (aplicar como *diffs*, NO regenerar).

### 5.1 `apps/authz/catalog.py`

**a) Módulos** — tras `MODULE_BULK_IMPORT`:

```python
MODULE_SYSTEM_SETTINGS = "system-settings"  # F8: parámetros globales (toggles de costeo)
```

**b) `PERMISSION_CATALOG`** — añadir la entrada:

```python
    MODULE_SYSTEM_SETTINGS: frozenset({ACTION_READ, ACTION_UPDATE}),
```

**c) `SYSTEM_PROFILES`** — añadir el módulo a los perfiles semilla (solo lo que cambia):

```python
    "JEFE": {
        "name": "Jefe",
        "permissions": {
            MODULE_ACCESS_CONTROL: [ACTION_READ, ACTION_CREATE, ACTION_UPDATE],
            MODULE_SYSTEM_SETTINGS: [ACTION_READ, ACTION_UPDATE],   # F8
        },
        "auto_approval": True,
    },
    "SUPERVISOR": {
        "name": "Supervisor",
        "permissions": {
            MODULE_ACCESS_CONTROL: [ACTION_READ],
            MODULE_SYSTEM_SETTINGS: [ACTION_READ],                  # F8
        },
        "auto_approval": False,
    },
```

> El seed (`get_or_create`) cubre instalaciones **nuevas**. Los entornos ya sembrados se cubren con la
> **data migration** en `authz` (tarea B.3).

### 5.2 `openspec/config.yaml` — invariantes del sistema

Reemplazar la línea del doble costeo por una versión que explicita la semántica de presentación y el
mínimo de una base:

```yaml
  - Doble costeo en paralelo: costo nominal (peso de factura) y costo efectivo (peso real tras
    merma). Ambas bases se calculan y persisten SIEMPRE; el toggle de `system-settings` es un
    filtro de PRESENTACIÓN que decide qué base muestran reportes/dashboards. Al menos una base
    MUST permanecer activa (no se pueden desactivar ambas).
```

### 5.3 `config/urls.py`

Tras la ruta de `bulk-import`:

```python
    # System settings (F8): parámetros globales (toggles de costeo). Singleton.
    path("system-settings/", include("apps.system_settings.urls")),
```

### 5.4 `config/settings/base.py`

En `LOCAL_APPS`, tras `"apps.bulk_import"`:

```python
    "apps.system_settings",
```
