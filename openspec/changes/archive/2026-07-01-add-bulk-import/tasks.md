# Tareas: add-bulk-import

<!-- Orden de fases REQUIRED: Contrato → Migraciones → Backend → Frontend → Seguridad → Pruebas. -->
<!-- No avanzar a la siguiente fase si hay ítems sin completar en la anterior. -->
<!-- Definition of done global: todos los gates del pipeline en verde localmente antes de cerrar el change. -->

## Fase 0: Contrato y Sincronización Inicial
- [x] **0.1** Backend — Crear la app `bulk_import` y definir la forma del reporte en
  `backend/apps/bulk_import/serializers.py`: `RowReportSerializer` e `ImportResultSerializer` (salida), con
  `help_text` en cada campo. No hay `WriteSerializer` propio.
- [x] **0.2** Backend — Registrar el módulo `bulk-import` y sus acciones (`create`) en `backend/apps/authz/catalog.py`.
- [x] **0.3** Backend — Anotar los endpoints con `drf-spectacular` (incluido el reporte) y regenerar `backend/schema.yml`.
- [x] **0.4** Frontend — Regenerar tipos + Zod desde `schema.yml` (`npm run codegen`) en `frontend/src/features/bulk-import/types/`.
- [x] **0.5** Global — Confirmar que no hay variables de entorno nuevas (`.env.example` sin cambios).

## Fase 1: Modelo de Datos y Migraciones
- [x] **1.1** Verificar que no se requieren modelos nuevos (proceso stateless); sin `makemigrations`. Si se
  añadiera un registro de auditoría de importación, su migración MUST ser reversible (`reverse_code`).

## Fase 2: Lógica de Negocio y API (Backend)
- [x] **2.1** Implementar el parser en `backend/apps/bulk_import/parsers.py`: CSV (stdlib) y Excel (`openpyxl`)
  → filas normalizadas conservando el número de fila; aplicar el límite de filas (constante central).
- [x] **2.2** Implementar en `backend/apps/bulk_import/services.py` `validate_rows` (delega en los serializers
  de dominio `Ficha` F4 / `Product` F5 y marca `valid/skipped/error`; dedup por clave natural contra registros vivos).
- [x] **2.3** Implementar `commit_import` en `services.py`: commit atómico all-or-nothing (`transaction.atomic`)
  con `@audit(action, entity)` y conteos de insertadas/omitidas.
- [x] **2.4** Implementar los endpoints en `backend/apps/bulk_import/views.py` (productos y fichas con flag
  `dry_run`, y plantilla descargable), delgados, protegidos por `HasModulePermission` (módulo `bulk-import`);
  errores por fila con el contrato uniforme. Registrar rutas en `backend/apps/bulk_import/urls.py`.

## Fase 3: Integración de Datos (Frontend — Hooks)
- [x] **3.1** Crear `useImportDryRun` y `useImportCommit` en `frontend/src/features/bulk-import/hooks/` con
  `useCustomMutation` de Refine (sin TanStack paralelo).
- [x] **3.2** Validar en el hook que la respuesta cumple el schema Zod generado en Fase 0 antes de exponer los datos.

## Fase 4: Componentes y Páginas (Frontend — UI)
- [x] **4.1** Crear `ImportWizard.tsx` (contenedor) en `frontend/src/features/bulk-import/components/`:
  selección de entidad, descarga de plantilla, carga de archivo; cubrir estados vacío/carga/error/éxito.
- [x] **4.2** Crear `ImportReportTable.tsx` (presentacional): tabla fila/estado/errores por campo; reutilizar el
  componente de errores por campo; confirmar habilitado solo sin filas en error; tokens del theme (cero hex); ≥44px.
- [x] **4.3** Actualizar el contrato público `frontend/src/features/bulk-import/index.ts` (exports explícitos).
- [x] **4.4** Crear la página `BulkImportPage.tsx` en `frontend/src/pages/` (Dumb Page: solo renderiza `ImportWizard`).
- [x] **4.5** Registrar la ruta protegida `/bulk-import` con `lazy(() => import(...))`; gating con
  `usePermissions().canDo("bulk-import", "create")`.

## Fase 5: Seguridad y DevSecOps
- [x] **5.1** Restringir la importación server-side a perfiles con el módulo `bulk-import` (Jefe/Supervisor);
  `ruff` + `mypy --strict` limpios en `backend/apps/bulk_import/`.
- [x] **5.2** `bandit -r backend/apps/bulk_import/`; validar tipo y tamaño del archivo; procesar en memoria sin persistirlo.
- [x] **5.3** Frontend — `eslint frontend/src/features/bulk-import/` y `tsc --noEmit` limpios.
- [x] **5.4** Verificar que no hay secretos en el código; contraste WCAG AA en modo claro y oscuro.

## Fase 6: Pruebas y Validación Final
- [x] **6.1** Tests de backend en `backend/apps/bulk_import/tests/` cubriendo todos los Scenarios (dry-run
  válido/inválido → `200` sin persistir; commit sin errores → `201`; commit con fila inválida → `400`, nada
  persiste; re-ejecución idempotente; lote mixto nuevas/duplicadas; validación delegada con mensajes de dominio;
  categoría inexistente; fichas con roles múltiples; límite de filas/formato → `400`; `401`/`403`). Probar CSV y Excel.
- [x] **6.2** Test de idempotencia explícito: importar dos veces el mismo archivo no cambia los conteos de la base.
- [x] **6.3** Tests de frontend (Vitest + RTL) del asistente y de la tabla de reporte (éxito/error/estados/ARIA).
- [x] **6.4** Integración — sin operaciones síncronas que choquen con el timeout de Cloud Run; sin errores/warnings de consola.
- [x] **6.5** Definition of done — dejar en verde: `ruff`, `mypy --strict`, `bandit`, `pip-audit`, `pytest`
  (cobertura ≥80%); `eslint`, `tsc`, `npm audit`, `vitest`. Confirmar antes de declarar el change completo.
