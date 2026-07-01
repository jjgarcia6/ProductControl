# Tareas: add-system-settings

<!-- Orden REQUIRED: Contrato → Migraciones → Backend → Frontend → Seguridad → Pruebas. -->
<!-- Cada tarea nombra el archivo/módulo exacto. DoD: todos los gates del pipeline en verde -->
<!-- localmente antes de declarar el change completo. -->

## Fase 0: Contrato y Modelo (OpenAPI + datos)

- [x] **0.1** Crear la app `system_settings` y el modelo `SystemSettings` en
  `backend/apps/system_settings/models.py` (singleton: `lock` unique + `CheckConstraint(lock=True)`;
  `costing_nominal_enabled`/`costing_effective_enabled` default `True`; hereda solo `TimeStampedModel`,
  sin soft delete).
- [x] **0.2** Definir `SystemSettingsReadSerializer` y `SystemSettingsUpdateSerializer` en
  `backend/apps/system_settings/serializers.py` (partial, `validate()` cruzado "≥1 base activa" →
  `non_field_errors`; `lock` nunca expuesto; `help_text` por campo).
- [x] **0.3** Registrar el módulo `system-settings` y sus acciones (`read`, `update`) en
  `backend/apps/authz/catalog.py`; añadirlo a los perfiles semilla `JEFE` (`read`,`update`) y
  `SUPERVISOR` (`read`) en `SYSTEM_PROFILES` (ver §5.1 del diseño).
- [x] **0.4** Añadir `"apps.system_settings"` a `LOCAL_APPS` (`config/settings/base.py`) y la ruta a
  `config/urls.py` (`system-settings/`).
- [x] **0.5** Anotar los endpoints con `drf-spectacular` y regenerar `schema.yml`.

## Fase 1: Migraciones Django

- [x] **1.1** `makemigrations system_settings`; confirmar reversibilidad (upgrade + downgrade) del
  modelo y del constraint.
- [x] **1.2** Data migration en `system_settings`: sembrar la fila única (`lock=True`, ambos toggles
  `True`) con `RunPython(forwards, backwards)`; reverse elimina la fila.
- [x] **1.3** Data migration en `authz`: parchear idempotentemente los perfiles semilla existentes
  (`JEFE` += `read`,`update`; `SUPERVISOR` += `read` sobre `system-settings`) sin pisar otros
  permisos; reverse retira solo la clave `system-settings`.
- [x] **1.4** `migrate` y verificar arranque limpio; confirmar que queda exactamente una fila en
  `system_settings`. Probar el reverse (`migrate authz <anterior>` y `migrate system_settings zero`)
  y re-aplicar.

## Fase 2: Lógica de Negocio y API (Backend)

- [x] **2.1** Implementar `get_settings()` en `backend/apps/system_settings/services.py`
  (`get_or_create(lock=True)`).
- [x] **2.2** Implementar `update_settings()`: validar "≥1 base activa", aplicar toggles y auditar el
  cambio con `@audit` del bootstrap (campo/valor anterior/valor nuevo/usuario). `transaction.atomic()`.
- [x] **2.3** Implementar el view delgado (retrieve + partial update del singleton) en
  `backend/apps/system_settings/views.py`, protegido con `HasModulePermission` y `required_permissions`
  (`GET`→read, `PATCH`→update); registrar la ruta en `backend/apps/system_settings/urls.py`.
- [x] **2.4** Verificar que todos los errores salen por el contrato uniforme (400 `non_field_errors`,
  401/403 `{detail}`).

## Fase 3: Integración de Datos (Frontend — Hooks)

- [x] **3.1** Regenerar tipos + Zod desde `schema.yml` (`npm run codegen`).
- [x] **3.2** Crear el hook `useSystemSettings` en
  `frontend/src/features/system-settings/hooks/useSystemSettings.ts`: `useCustom` (GET) +
  `useCustomMutation` (PATCH); validar la respuesta contra el schema Zod generado.

## Fase 4: Componentes y Páginas (Frontend — UI)

- [x] **4.1** Construir `SystemSettingsContainer` (orquesta el hook; estados vacío/carga/error/éxito) y
  `SystemSettingsForm` (dos toggles, presentacional) en
  `frontend/src/features/system-settings/components/`.
- [x] **4.2** Gating por perfil: Jefe edita, Supervisor en solo lectura (controles deshabilitados);
  ocultar la entrada para RUTA/USUARIO con `usePermissions().canDo('system-settings', acción)`.
- [x] **4.3** Error cruzado "≥1 base activa" como aviso general (no atado a control); tokens del theme;
  toggles accesibles (foco, rol, contraste AA); áreas táctiles ≥44px. Actualizar el contrato público
  `index.ts`.
- [x] **4.4** Crear la página *dumb* `SystemSettingsPage.tsx` en `frontend/src/pages/` y declarar la
  ruta protegida en `App.tsx` (`<Authenticated>` + `ForcePasswordChangeGuard` + `lazy(...)`).

## Fase 5: Seguridad y DevSecOps

- [x] **5.1** Verificar que el `PATCH` respeta el permiso `update` (Supervisor → 403; sin sesión →
  401); cubrir en tests.
- [x] **5.2** Análisis estático: `ruff check` + `mypy --strict` sobre `apps/system_settings` (backend),
  `eslint` + `tsc` sobre `src/features/system-settings` (frontend). Corregir todo.
- [x] **5.3** `bandit` sobre `apps/system_settings`; verificar que `lock` no se expone y que no hay
  secretos ni colores hardcodeados en el diff. `pip-audit` / `npm audit`.
- [x] **5.4** Contraste WCAG AA de la pantalla nueva en modo claro y oscuro (toggles, estado
  deshabilitado del Supervisor).

## Fase 6: Pruebas y Validación Final

- [x] **6.1** Tests de backend en `backend/apps/system_settings/tests/` cubriendo todos los Scenarios
  (retrieve; singleton único tras re-seed; desactivar una base; reactivar; ambas en `false` → 400
  `non_field_errors`; Jefe edita → 200; Supervisor lee → 200; Supervisor edita → 403; sin sesión →
  401; auditoría registra campo/valor anterior/nuevo/usuario).
- [x] **6.2** Test de la data migration de `authz` (parche idempotente: los perfiles semilla existentes
  ganan `system-settings` sin perder permisos previos; reverse lo retira).
- [x] **6.3** Tests de frontend (Vitest + RTL) de los toggles (render, solo lectura para Supervisor,
  aviso de error cruzado, estados carga/error).
- [x] **6.4** Ejecutar y dejar en verde: `ruff`, `mypy --strict`, `bandit`, `pip-audit`, `pytest`
  (cobertura ≥80%); `eslint`, `tsc`, `npm audit`, `vitest`, E2E (`playwright` incl. WebKit).
- [x] **6.5** Definition of done — todos los gates del pipeline (backend y frontend) en verde,
  ejecutados localmente, antes de declarar el change completo.
