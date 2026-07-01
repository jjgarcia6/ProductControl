# Change: add-system-settings — Fase 8

**Capability:** `system-settings` (inicia) · modifica `access-control` (registro de módulo + parche de perfiles semilla) · **Depende de:** F1 (auth), F2 (access-control) · **Desbloquea:** F11 (kardex), F13 (merma)
**Fuente de verdad:** `openspec/config.yaml`. Ante conflicto, manda el `config.yaml`.
**Requerimientos:** 14.2.

> **Cómo usar este archivo.** Consolida los cuatro artefactos del change. Cada sección de primer nivel mapea a un archivo dentro de `openspec/changes/add-system-settings/`:
> - `## 1) PROPOSAL` → `proposal.md`
> - `## 2) SPECS` → dos deltas: `specs/system-settings/spec.md` y `specs/access-control/spec.md`
> - `## 3) DESIGN` → `design.md`
> - `## 4) TASKS` → `tasks.md`
>
> La `## 5) MODIFICACIONES PUNTUALES` NO es un artículo del change dir: son ediciones exactas sobre archivos existentes del repo (`apps/authz/catalog.py`, `openspec/config.yaml`, `config/urls.py`, `config/settings/base.py`). Se aplican como *diffs* dirigidos, no como regeneración.
>
> Requirements en RFC 2119 (MUST/MUST NOT/SHALL); Scenarios en español (DADO/CUANDO/ENTONCES). Código e identificadores en inglés; documentación en español.

---

## 1) PROPOSAL → proposal.md

### Intent

Entregar los **parámetros globales del sistema** como un singleton editable, con los dos **toggles de costeo** (nominal / efectivo) activables de forma independiente. El toggle es un **filtro de presentación**: ambos costos se calculan y persisten SIEMPRE en paralelo (invariante de doble costeo); el flag solo determina qué base **muestran** los reportes y dashboards. F8 solo almacena y protege esos flags; la lógica que los lee vive en kardex (F11), merma (F13) y reportes (F23). Solo el Jefe edita; el Supervisor consulta.

### Scope (qué cambia)

- **Singleton de configuración** (`SystemSettings`): fila única garantizada a nivel de base de datos, con `costing_nominal_enabled` y `costing_effective_enabled` (ambos `True` por defecto). Sin máquina de estado, sin soft delete.
- **Invariante nuevo — al menos una base activa:** el sistema MUST rechazar dejar ambas bases desactivadas (400).
- **API de configuración:** `GET` (retrieve del singleton) y `PATCH` (update de los toggles). Sin `POST`/`DELETE`.
- **Autorización (usa el mecanismo de F2):** nuevo módulo `system-settings` con acciones `read`/`update`; el **Jefe** lo lleva con `read`+`update`, el **Supervisor** solo `read`. Se propaga tanto a instalaciones nuevas (seed) como a entornos ya sembrados (data migration de parche).
- **Auditoría del cambio:** el `PATCH` registra un evento de auditoría (usuario/fecha/campo/valor anterior/valor nuevo) usando el mecanismo `@audit` del bootstrap.

### Decisiones de modelado (validadas)

- **Singleton a nivel de DB, no por convención:** campo centinela `lock` (`BooleanField`, `unique=True`, `editable=False`, default `True`) + `CheckConstraint(lock=True)`. Garantiza exactamente una fila; imposible crear una segunda ni por ORM ni por SQL directo.
- **El toggle es filtro de presentación, no de cálculo:** consistente con el invariante *doble costeo en paralelo*. F8 NO recalcula, NO cascada, NO interactúa con período. Por eso F8 depende de F1/F2 y **no** de F9.
- **Excepción explícita a la política de soft delete (3 clases):** un singleton de configuración no es catálogo (clase 2), ni documento con estado (clase 1), ni ficha (clase 3). No se borra nunca; hereda solo `TimeStampedModel`.
- **"Solo el Jefe edita" = permiso de perfil (Opción A):** la fuente única de autorización sigue siendo `authz.Profile` (principio bloqueado). No se introduce un segundo eje por `role`. El Jefe lleva `system-settings.update` por su perfil semilla; el riesgo residual (que un perfil a medida reciba `update`) se acepta conscientemente.
- **Consumo por otras fases:** service `get_settings()` retorna el singleton para lectura directa de kardex/merma/reports, **sin** pasar por los permisos del usuario final (esas fases lo consultan como regla de negocio, no como acción de UI).

### Impacto en el modelo de datos (antes que UI — DIP)

- Nueva app `system_settings`. Tabla `system_settings` (una sola fila) con `costing_nominal_enabled`, `costing_effective_enabled`, `lock` (centinela único) y marcas de tiempo. Migración reversible.
- **Data migration (misma app):** siembra la fila única con ambos toggles en `True`.
- **Data migration en `authz`:** parchea idempotentemente los perfiles semilla EXISTENTES (`JEFE` += `read`,`update`; `SUPERVISOR` += `read`) sobre `system-settings`. Necesaria porque `seed_system_profiles()` usa `get_or_create(defaults=...)` y NO actualiza perfiles ya creados. Reversible (retira la clave `system-settings` de esos perfiles).
- Módulo `system-settings` y sus acciones registrados en el catálogo de `access-control` (F2).

### Flujo del usuario (UI)

- **Roles afectados:** el **Jefe** (perfil con `system-settings` en `read`+`update`) ve y edita los toggles. El **Supervisor** (`read`) los ve en **solo lectura** (controles deshabilitados). El **Responsable de ruta** y el **Usuario** no ven ni acceden la pantalla (gating por perfil).
- Ruta protegida nueva en `system-settings`; pantalla con dos interruptores. Estados vacío/carga/error/éxito requeridos; el error de "al menos una base activa" se muestra como **aviso general** (no atado a un campo). Tokens del theme; sin hex literales.

### Cadena de trazabilidad

No se altera la cadena de trazabilidad (Ingreso → Kardex → Entrega → Cobro / Ingreso → CxP → Pago). `system-settings` es configuración global: no genera movimientos de Kardex, documentos ni saldos. Solo **provee** los flags que kardex/merma/reports consumirán en fases posteriores.

### Fuera de alcance

- **La lectura del flag en cálculos/reportes** (qué base se muestra en rentabilidad, dashboards y Kardex) → F11, F13, F23. En F8 el flag solo se almacena.
- **Cualquier otro parámetro global** (umbrales de alerta de caducidad, defaults de merma, plazos, etc.) → pertenece a su propia capability. YAGNI estricto: F8 solo lleva los dos toggles de costeo.
- **Prohibiciones estrictas (heredadas de la plantilla):** persistencia SOLO PostgreSQL vía Django ORM (sin SQL raw); operaciones multi-tabla en `transaction.atomic()` con rollback total; cero colores hardcodeados (solo tokens del theme, claro y oscuro); credenciales SOLO por `.env`/GCP Secret Manager; sin refactorizaciones ajenas al dominio (YAGNI).

### Verificación de invariantes

- **Soft delete (3 clases):** N/A — singleton de configuración. Excepción documentada; hereda solo `TimeStampedModel`.
- **Período cerrado:** no aplica (sin fecha ni documento). Por eso F8 no depende de F9.
- **Kardex append-only / FIFO / cuadre / snapshot / nota de crédito:** no se tocan.
- **Doble costeo en paralelo:** intacto. F8 **almacena** los flags; el cálculo paralelo sigue siendo invariante. Se **añade** el sub-invariante "al menos una base activa" (ver `## 5`).
- **Contrato de errores uniforme:** ambas bases en `False` → 400 en `non_field_errors` (validación cruzada, no atada a un campo). Sin sesión → 401; sin permiso → 403 `{detail}` genérico.

### Riesgos y rollback

- **Riesgo 1 — el parche de perfiles en entornos ya sembrados.** Editar `SYSTEM_PROFILES` NO alcanza a perfiles preexistentes (`get_or_create` no actualiza). Sin la data migration de parche, el Jefe de un entorno F1–F7 ya corrido **no** podría editar la configuración. Mitigación: data migration idempotente que fusiona la clave `system-settings` en `permissions` de `JEFE`/`SUPERVISOR` sin pisar otros permisos.
- **Riesgo 2 — el singleton.** Un seed que corra dos veces o un test que cree una segunda fila rompería la unicidad. Mitigación: `CheckConstraint(lock=True)` + `unique=True` en `lock` + `get_or_create(lock=True)` en `get_settings()`; la siembra es idempotente.
- **Criterio de aborto (verificable):** abortar si (a) `authz` (F2) no está migrado —el módulo y el parche de perfiles lo requieren—, o (b) la migración inversa (`migrate authz <anterior>` y `migrate system_settings zero`) falla tras 2 intentos de corrección, o (c) los tests de los Scenarios no quedan en verde, o (d) tras seed queda más de una fila en `system_settings`.
- **Plan de rollback:** revertir en orden inverso: primero la data migration de `authz` (retira `system-settings` de los perfiles semilla), luego `migrate system_settings zero` (elimina tabla + fila). Ambas reversibles; sin dependencias de datos de negocio.

---

## 2) SPECS

### 2.1 → specs/system-settings/spec.md

# Delta para la capability `system-settings`

## ADDED Requirements

### Requirement: Configuración global como singleton
El sistema MUST exponer una única fila de configuración global, recuperable sin identificador. El sistema MUST NOT permitir crear ni eliminar filas de configuración. Los errores MUST seguir el contrato uniforme.

#### Scenario: Recuperar la configuración
- DADO un usuario autorizado con `system-settings` en `read`
- CUANDO solicita la configuración global
- ENTONCES el sistema responde 200 con los toggles de costeo actuales

#### Scenario: La configuración es única
- DADO que la configuración ya existe (sembrada)
- CUANDO se ejecuta la siembra de nuevo
- ENTONCES el sistema conserva una sola fila de configuración

### Requirement: Toggles de costeo independientes
Cada base de costeo (`costing_nominal_enabled`, `costing_effective_enabled`) MUST poder activarse o desactivarse de forma independiente mediante `PATCH` parcial.

#### Scenario: Desactivar solo la base efectiva
- DADO ambas bases activas
- CUANDO el Jefe desactiva únicamente la base efectiva
- ENTONCES el sistema persiste `costing_effective_enabled=false` y conserva `costing_nominal_enabled=true`

#### Scenario: Reactivar una base
- DADO la base nominal desactivada y la efectiva activa
- CUANDO el Jefe reactiva la base nominal
- ENTONCES el sistema persiste ambas bases activas

### Requirement: Al menos una base de costeo activa
El sistema MUST rechazar toda operación que dejaría ambas bases de costeo desactivadas simultáneamente.

#### Scenario: Intentar desactivar ambas bases
- DADO solo una base de costeo activa
- CUANDO el Jefe intenta desactivar también la base restante
- ENTONCES el sistema responde **400** con `{campo: [mensajes]}` en `non_field_errors`
- Y el frontend MUST mostrar el mensaje como aviso general (no atado a un campo)

### Requirement: Solo el Jefe edita; el Supervisor consulta
La edición de la configuración MUST estar restringida a perfiles con `system-settings` en `update`. La lectura MUST estar disponible para perfiles con `system-settings` en `read`.

#### Scenario: El Jefe edita
- DADO un Jefe con `system-settings` en `update`
- CUANDO modifica un toggle de costeo válido
- ENTONCES el sistema aplica el cambio y responde 200

#### Scenario: El Supervisor consulta la configuración
- DADO un Supervisor con `system-settings` en `read` (sin `update`)
- CUANDO recupera la configuración
- ENTONCES el sistema responde 200 con los toggles
- Y el frontend MUST mostrar los controles en solo lectura (deshabilitados)

#### Scenario: El Supervisor no puede editar la configuración
- DADO un Supervisor con `system-settings` en `read` (sin `update`)
- CUANDO intenta modificar un toggle
- ENTONCES el sistema responde **403** con `{detail}` genérico

#### Scenario: Sin sesión
- DADO un usuario sin sesión activa
- CUANDO intenta recuperar o modificar la configuración
- ENTONCES el sistema responde **401**
- Y el frontend MUST redirigir al login

### Requirement: Auditoría del cambio de configuración
Toda modificación de la configuración MUST registrar un evento de auditoría con usuario, fecha/hora, campo, valor anterior y valor nuevo.

#### Scenario: Cambiar un toggle deja rastro
- DADO un Jefe autorizado
- CUANDO desactiva una base de costeo
- ENTONCES el sistema registra un evento de auditoría con el campo, el valor anterior y el valor nuevo
- Y el usuario que realizó el cambio

### 2.2 → specs/access-control/spec.md

# Delta para la capability `access-control`

## ADDED Requirements

### Requirement: Módulo `system-settings` en el catálogo de permisos
El catálogo de permisos de `access-control` MUST incluir el módulo `system-settings` con las acciones `read` y `update`. Los perfiles semilla MUST otorgar `system-settings` en `read`+`update` al perfil `JEFE` y en `read` al perfil `SUPERVISOR`, tanto en instalaciones nuevas (seed) como en entornos ya sembrados (data migration idempotente). La autorización efectiva (403/401) se especifica en el delta de `system-settings` y MUST NOT duplicarse aquí (DRY).

#### Scenario: El catálogo registra el módulo en instalaciones nuevas
- DADO un entorno sin sembrar
- CUANDO se ejecuta la siembra de perfiles del sistema
- ENTONCES el perfil `JEFE` obtiene `system-settings` en `read` y `update`
- Y el perfil `SUPERVISOR` obtiene `system-settings` en `read`

#### Scenario: El parche no pisa permisos en entornos ya sembrados
- DADO un entorno con `JEFE` y `SUPERVISOR` ya sembrados sin `system-settings`
- CUANDO se aplica la data migration de parche
- ENTONCES `JEFE` gana `system-settings` en `read` y `update` conservando sus permisos previos
- Y `SUPERVISOR` gana `system-settings` en `read` conservando sus permisos previos

#### Scenario: La reversión retira solo la clave añadida
- DADO los perfiles semilla parcheados con `system-settings`
- CUANDO se revierte la data migration de parche
- ENTONCES el sistema retira la clave `system-settings` de `JEFE` y `SUPERVISOR`
- Y conserva intactos los demás permisos de cada perfil

---

## 3) DESIGN → design.md

### Capa de datos

- **App `system_settings`**:
  - `SystemSettings(TimeStampedModel)`:
    - `costing_nominal_enabled` (`BooleanField`, default `True`)
    - `costing_effective_enabled` (`BooleanField`, default `True`)
    - `lock` (`BooleanField`, default `True`, `unique=True`, `editable=False`) — centinela del singleton.
    - `CheckConstraint(check=Q(lock=True), name="system_settings_singleton_lock")`.
  - **NO** hereda `SoftDeleteModel` (excepción documentada: singleton de configuración).
- **Data migration (`system_settings`):** crea la fila única (`lock=True`, ambos toggles `True`).
- **Data migration (`authz`):** fusiona `system-settings` en `permissions` de los perfiles semilla existentes (`JEFE` → `[read, update]`, `SUPERVISOR` → `[read]`), idempotente y reversible.
- Migraciones reversibles en ambas apps.

**Tablas e índices / constraints**

| Tabla | Índice / Constraint | Tipo | Justificación |
| :--- | :--- | :--- | :--- |
| `system_settings` | `lock` | unique | segunda fila imposible (singleton) |
| `system_settings` | `Q(lock=True)` | check constraint | `lock` no puede ser distinto de `True` |

**Impacto en invariantes del sistema**

- **Período cerrado:** no aplica — sin documentos con fecha.
- **Kardex FIFO / append-only:** no se toca.
- **Doble costeo:** los flags que gobiernan la **presentación** de cada base. El cálculo paralelo permanece invariante; F8 no recalcula. Se añade el sub-invariante "al menos una base activa".
- **Cuadre de ruta / snapshot / nota de crédito:** no aplican.
- **Soft delete (3 clases):** N/A — singleton (excepción explícita).
- **Trazabilidad:** no se altera.

### Capa de API

- **Contrato OpenAPI primero:** endpoints de retrieve y update del singleton, anotados con `drf-spectacular`; regenerar `schema.yml`.
- **Permisos por perfil:** registrar el módulo `system-settings` en `apps/authz/catalog.py`; proteger los endpoints con `HasModulePermission` de F2 vía `required_permissions` (`GET` → `("system-settings","read")`, `PATCH` → `("system-settings","update")`).
- **Lógica en services:** la validación "al menos una base activa", la obtención del singleton y la auditoría viven en `apps/system_settings/services.py`; el view es delgado.
- **Serializers Write/Read separados:** `SystemSettingsReadSerializer` (salida) y `SystemSettingsUpdateSerializer` (entrada, `partial`, con `validate()` cruzado que rechaza ambas bases en `False` → `non_field_errors`). `lock` NUNCA se expone. Cada campo con `help_text` para el OpenAPI.
- **Auditoría:** el service de update aplica el mecanismo `@audit` del bootstrap sobre los campos de toggle.

**Diccionario de datos vivo**

| Entidad | Campo | Tipo (Py / TS) | Descripción | Restricciones |
| :--- | :--- | :--- | :--- | :--- |
| `SystemSettings` | `costing_nominal_enabled` | `bool / boolean` | muestra costo nominal en reportes | no ambos `false` |
| `SystemSettings` | `costing_effective_enabled` | `bool / boolean` | muestra costo efectivo en reportes | no ambos `false` |

**Endpoints de DRF**

| Verbo | Ruta | Write | Read | Códigos HTTP | Roles (perfil) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/system-settings` | — | `SystemSettingsRead` | 200/401/403 | Jefe, Supervisor |
| `PATCH` | `/system-settings` | `SystemSettingsUpdate` | `SystemSettingsRead` | 200/400/401/403 | Jefe |

> El recurso es un singleton: la ruta no lleva `id`. El view resuelve la instancia vía `get_settings()`.

**Servicios de negocio**

| Servicio | Método | Responsabilidad única | Transaccional |
| :--- | :--- | :--- | :--- |
| `system_settings/services.py` | `get_settings()` | retornar el singleton (`get_or_create(lock=True)`); consumo directo de otras fases | No |
| `system_settings/services.py` | `update_settings()` | validar "≥1 base activa", aplicar toggles, auditar el cambio | Sí |

### Capa de frontend

- **Pantalla de configuración** en `src/features/system-settings/`: dos interruptores (nominal / efectivo). El Jefe edita; el Supervisor los ve deshabilitados (solo lectura).
- El error cruzado "al menos una base activa" se muestra como **aviso general** (banner/toast), no mapeado a un control.
- Zod generado del OpenAPI; gating por perfil (`system-settings.read/update`); estados vacío/carga/error/éxito; tokens del theme; toggles accesibles (rol, foco, contraste AA claro/oscuro).

**Árbol de directorios de la feature** (solo lo que este cambio crea)

```
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

**Contrato público (`system-settings/index.ts`)**

```typescript
export { SystemSettingsContainer } from './components/SystemSettingsContainer';
export { useSystemSettings } from './hooks/useSystemSettings';
export type { SystemSettingsType } from './types/system-settings.types';
```

**Custom hooks**

| Hook | Responsabilidad única | Endpoint / resource | Refine hook |
| :--- | :--- | :--- | :--- |
| `useSystemSettings` | leer y actualizar el singleton | `/system-settings` | `useCustom` (GET) + `useCustomMutation` (PATCH) |

> Al ser singleton sin `id`, se usa `useCustom`/`useCustomMutation` (no `useOne`/`useUpdate` de recurso con id).

**Rutas / páginas (`src/pages/`)**

| Ruta | Tipo | Página | Contenedor | Perfil (canDo) |
| :--- | :--- | :--- | :--- | :--- |
| `/system-settings` | Protegida (`lazy`) | `SystemSettingsPage.tsx` | `SystemSettingsContainer` | `system-settings.read` (ver) / `update` (editar) |

- Ruta declarada en `App.tsx` con `<Authenticated>` + `ForcePasswordChangeGuard` y `lazy(() => import(...))` (**no** array `resources` de Refine, per convención del proyecto); gating en componente con `usePermissions().canDo('system-settings', acción)`. Página *dumb*.

### Seguridad

- Lectura y edición por perfil (F2). El Supervisor no puede editar (403 verificado en test). `lock` nunca se expone en la API. Sin datos sensibles adicionales.
- **Gestión de secretos:** sin variables de entorno nuevas (backend ni frontend); nada que añadir a `.env.example` ni a GCP Secret Manager.

### Qué NO se hace (YAGNI)

Sin recálculo ni cascada de costeo, sin interacción con período, sin otros parámetros globales, sin historial de versiones de configuración más allá del log de auditoría, sin endpoint de creación/borrado.

---

## 4) TASKS → tasks.md

> Orden obligatorio del `config.yaml`: Contrato (OpenAPI) → Migraciones Django → Backend (services) → Frontend → Seguridad → Pruebas. Cada tarea nombra el archivo/módulo exacto. Definition of done global: todos los gates del pipeline en verde localmente antes de declarar el change completo.

### A. Contrato y modelo (OpenAPI + datos)
- [ ] A.1 Crear la app `system_settings` y el modelo `SystemSettings` (singleton: `lock` unique + `CheckConstraint(lock=True)`; `costing_nominal_enabled`/`costing_effective_enabled` default `True`; hereda solo `TimeStampedModel`, sin soft delete).
- [ ] A.2 Definir `SystemSettingsReadSerializer` y `SystemSettingsUpdateSerializer` (partial, `validate()` cruzado "≥1 base activa" → `non_field_errors`; `lock` nunca expuesto).
- [ ] A.3 Registrar el módulo `system-settings` y sus acciones (`read`, `update`) en `apps/authz/catalog.py`; añadirlo a los perfiles semilla `JEFE` (`read`,`update`) y `SUPERVISOR` (`read`) en `SYSTEM_PROFILES`.
- [ ] A.4 Añadir la app a `LOCAL_APPS` (`config/settings/base.py`) y la ruta a `config/urls.py` (`system-settings/`).
- [ ] A.5 Anotar los endpoints con `drf-spectacular` y regenerar `schema.yml`.

### B. Migraciones
- [ ] B.1 `makemigrations system_settings`; confirmar reversibilidad (upgrade + downgrade) del modelo y del constraint.
- [ ] B.2 Data migration en `system_settings`: sembrar la fila única (`lock=True`, ambos toggles `True`), reversible.
- [ ] B.3 Data migration en `authz`: parchear idempotentemente los perfiles semilla existentes (`JEFE` += `read`,`update`; `SUPERVISOR` += `read` sobre `system-settings`) sin pisar otros permisos; reverse retira solo la clave `system-settings`.
- [ ] B.4 `migrate` y verificar arranque limpio; confirmar que queda exactamente una fila en `system_settings`.

### C. Backend (services + vistas)
- [ ] C.1 Implementar `get_settings()` en `apps/system_settings/services.py` (`get_or_create(lock=True)`).
- [ ] C.2 Implementar `update_settings()`: validar "≥1 base activa", aplicar toggles y auditar el cambio con `@audit` del bootstrap (campo/valor anterior/valor nuevo/usuario). Transaccional.
- [ ] C.3 Implementar el view delgado (retrieve + partial update del singleton), protegido con `HasModulePermission` y `required_permissions` (`GET`→read, `PATCH`→update); registrar la ruta.
- [ ] C.4 Verificar que todos los errores salen por el contrato uniforme (400 `non_field_errors`, 401/403 `{detail}`).

### D. Frontend
- [ ] D.1 Regenerar tipos + Zod desde `schema.yml` (`npm run codegen`).
- [ ] D.2 Construir `SystemSettingsContainer` + `SystemSettingsForm` (dos toggles) y el hook `useSystemSettings` en `src/features/system-settings/`.
- [ ] D.3 Gating por perfil: Jefe edita, Supervisor en solo lectura (controles deshabilitados); ocultar la entrada para RUTA/USUARIO.
- [ ] D.4 Error cruzado "≥1 base activa" como aviso general (no atado a control); estados vacío/carga/error/éxito; tokens del theme; toggles accesibles (foco, rol, contraste AA).

### E. Seguridad (no negociable)
- [ ] E.1 Verificar que el `PATCH` respeta el permiso `update` (Supervisor → 403; sin sesión → 401); cubrir en tests.
- [ ] E.2 Análisis estático de los módulos afectados: `ruff check` + `mypy --strict` (backend), `eslint` + `tsc` (frontend). Corregir todo.
- [ ] E.3 `bandit` sobre `apps/system_settings`; verificar que `lock` no se expone y que no hay secretos ni colores hardcodeados en el diff.
- [ ] E.4 Contraste WCAG AA de la pantalla nueva en modo claro y oscuro (toggles, estado deshabilitado del Supervisor).

### F. Pruebas (gate)
- [ ] F.1 Tests de backend en `apps/system_settings/tests/` cubriendo todos los Scenarios (retrieve; singleton único tras re-seed; desactivar una base; reactivar; ambas en `false` → 400 `non_field_errors`; Jefe edita → 200; Supervisor lee → 200, edita → 403; sin sesión → 401; auditoría registra campo/valor anterior/nuevo/usuario).
- [ ] F.2 Test de la data migration de `authz` (parche idempotente: los perfiles semilla existentes ganan `system-settings` sin perder permisos previos; reverse lo retira).
- [ ] F.3 Tests de frontend (Vitest + RTL) de los toggles (render, solo lectura para Supervisor, aviso de error cruzado, estados carga/error).
- [ ] F.4 Ejecutar y dejar en verde: `ruff`, `mypy --strict`, `bandit`, `pip-audit`, `pytest` (cobertura ≥80%); `eslint`, `tsc`, `npm audit`, `vitest`, E2E (`playwright` incl. WebKit). Confirmar antes de declarar el change completo.

---

## 5) MODIFICACIONES PUNTUALES (archivos existentes del repo)

> Aplicar como *diffs* dirigidos. NO regenerar los archivos completos.

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
> El seed (`get_or_create`) cubre instalaciones **nuevas**. Los entornos ya sembrados se cubren con la **data migration B.3** en `authz`.

### 5.2 `openspec/config.yaml` — invariantes del sistema

Reemplazar la línea del doble costeo por una versión que explicita la semántica de presentación y el mínimo de una base:
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
