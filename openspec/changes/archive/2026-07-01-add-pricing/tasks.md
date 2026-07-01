# Tareas: add-pricing

<!-- Orden de fases REQUIRED: Contrato → Migraciones → Backend → Frontend → Seguridad → Pruebas. -->
<!-- No avanzar a la siguiente fase si hay ítems sin completar en la anterior. -->
<!-- Definition of done global: todos los gates del pipeline en verde localmente antes de cerrar el change. -->

## Fase 0: Contrato y Sincronización Inicial

- [x] **0.1** Backend — Crear `backend/apps/pricing/serializers.py` con `PriceListWriteSerializer`/
  `PriceListReadSerializer` y `PriceListItemWriteSerializer`/`PriceListItemReadSerializer`. Añadir
  `AssignPriceListSerializer` (entrada) en `backend/apps/directory/serializers.py` con salida
  `FichaReadSerializer`. Cada campo con `help_text`. `price` con `DecimalField(max_digits=12,
  decimal_places=2)` (nunca `FloatField`). La unicidad NO se valida aquí (la gobierna el service): NO
  usar `UniqueValidator`/`UniqueTogetherValidator`.
- [x] **0.2** Backend — Anotar los endpoints con `drf-spectacular` y regenerar el OpenAPI:
  `uv run python manage.py spectacular --file schema.yml`. Verificar que expone `PriceList`,
  `PriceListItem` y la acción `assign-price-list`.
- [x] **0.3** Frontend — Regenerar tipos + Zod desde `../backend/schema.yml`: `npm run codegen`.
  Re-exportarlos en `frontend/src/features/pricing/types/pricing.types.ts`. NO escribir Zod a mano.
- [x] **0.4** Global — Confirmar que no hacen falta variables nuevas en `backend/.env.example` ni
  `frontend/.env.example` (este change no introduce ninguna).

## Fase 1: Modelo de Datos y Migraciones

- [x] **1.1** Crear `backend/apps/pricing/models.py`: `PriceList` heredando `SoftDeleteModel` +
  `TimeStampedModel` (clase 2) con `name`, `type` (`PriceListType`: `NORMAL`/`DESCARTE`) y
  `UniqueConstraint(name)` parcial (`condition=Q(deleted_at__isnull=True)`). `PriceListItem` con FK
  `price_list` (`CASCADE`), FK `product` (`products.Product`, `PROTECT`), `price`
  (`DecimalField`, `MinValueValidator(0)`) y `UniqueConstraint(price_list, product)`.
- [x] **1.2** Modificar `backend/apps/directory/models.py`: añadir `Ficha.price_list`
  (`ForeignKey("pricing.PriceList", null=True, blank=True, on_delete=PROTECT, related_name="fichas")`).
- [x] **1.3** Generar migraciones: `uv run python manage.py makemigrations pricing directory`.
  Revisar los archivos generados (CreateModel + AddConstraint en `pricing`; AddField en `directory`).
- [x] **1.4** Aplicar: `uv run python manage.py migrate`. Verificar tablas/columnas/constraints.
- [x] **1.5** Probar el reverse: `migrate directory <anterior>` y `migrate pricing zero`; verificar que
  revierte sin errores. Luego re-aplicar: `migrate`.

## Fase 2: Lógica de Negocio y API (Backend)

- [x] **2.1** Crear `backend/apps/pricing/services.py`: `create_price_list`/`update_price_list`
  (unicidad de nombre entre vivas → `Conflict` 409), `set_price_list_item` (unicidad (lista, producto)
  → 409; precio ≥ 0 → 400), `soft_delete_price_list` (baja bloqueada si tiene fichas asignadas → 409).
  Usar `transaction.atomic()` y el decorator `@audit(action, entity)`. Excepciones tipadas (sin
  `except Exception`).
- [x] **2.2** Extender `backend/apps/directory/services.py`: `assign_price_list` con integridad
  asignación↔rol cliente (400 si la ficha no tiene rol cliente). `@audit` + `transaction.atomic()`.
- [x] **2.3** Crear `backend/apps/pricing/views.py`: `APIView` list/create + detail para listas e ítems
  (viewsets delgados que delegan en services), protegidos por `HasModulePermission` con
  `required_permissions` del módulo `PRICING`. Añadir la acción `assign-price-list` sobre la ficha en
  `backend/apps/directory/views.py` (permiso `directory.update`).
- [x] **2.4** Registrar rutas en `backend/apps/pricing/urls.py` (prefijo `/pricing`) y la nueva acción
  en `backend/apps/directory/urls.py`. Incluir `pricing.urls` en el router raíz.
- [x] **2.5** Registrar el módulo `PRICING` y sus acciones (`read/create/update`) en
  `backend/apps/authz/catalog.py` (aditivo, sin tocar el seed existente).

## Fase 3: Integración de Datos (Frontend — Hooks)

- [x] **3.1** Crear `frontend/src/features/pricing/hooks/usePriceLists.ts` y `usePriceListItems.ts`
  envolviendo `useList`/`useCreate`/`useUpdate`/`useDelete` de Refine. NO montar TanStack Query aparte.
- [x] **3.2** Crear `frontend/src/features/directory/hooks/useAssignPriceList.ts` con
  `useCustomMutation` (`PATCH /directory/fichas/{id}/assign-price-list`).
- [x] **3.3** Validar en los hooks que la respuesta cumple el schema Zod generado en Fase 0 antes de
  exponer los datos; lanzar error descriptivo si no coincide.

## Fase 4: Componentes y Páginas (Frontend — UI)

- [x] **4.1** Crear `frontend/src/features/pricing/components/PriceListsContainer.tsx`: consume los
  hooks de Fase 3; cubre estados vacío/carga/error/éxito.
- [x] **4.2** Crear los presentacionales `PriceListForm.tsx` y `PriceItemsGrid.tsx` en
  `features/pricing/components/`: solo props; RHF + `zodResolver`; precios decimales (2 lugares); todo
  color desde tokens del theme (cero hex); inputs numéricos ≥16px iOS; `FieldError` compartido.
- [x] **4.3** Crear `frontend/src/features/directory/components/PriceListSelect.tsx`: selector de lista
  visible solo si la ficha tiene rol cliente; integrado en el formulario de ficha existente.
- [x] **4.4** Actualizar `frontend/src/features/pricing/index.ts` con las exportaciones explícitas.
- [x] **4.5** Crear `frontend/src/pages/PriceListsPage.tsx` (Dumb Page: importa y renderiza
  `PriceListsContainer`).
- [x] **4.6** Declarar la ruta protegida en `App.tsx` (`<Authenticated>` + `ForcePasswordChangeGuard`,
  `lazy(() => import(...))`); gating en componente con `usePermissions().canDo('PRICING', acción)`.

## Fase 5: Seguridad y DevSecOps

- [x] **5.1** Backend — `uv run ruff check backend/apps/pricing backend/apps/directory` y
  `uv run mypy .` (strict). Corregir todo.
- [x] **5.2** Backend — `uv run bandit -c pyproject.toml -r apps/pricing`. Corregir MEDIUM+.
- [x] **5.3** Frontend — `npm run lint` y `npm run typecheck` sobre `features/pricing` y el selector de
  `directory`. Corregir todo.
- [x] **5.4** Global — Verificar que no hay secretos ni colores hardcodeados en el diff; asignación y
  edición/baja de precios respetan los permisos por perfil (F2); cubrir 401/403.
- [x] **5.5** UI — Contraste WCAG AA en las pantallas nuevas (grilla de precios, selector de lista) en
  modo claro y oscuro.

## Fase 6: Pruebas y Validación Final

- [x] **6.1** Backend — `backend/apps/pricing/tests/`: crear lista `NORMAL`/`DESCARTE`; nombre duplicado
  → 409; precio por producto; producto duplicado en lista → 409; precio negativo → 400; baja de lista
  sin/con clientes (409); sin autorización → 401/403. `backend/apps/directory/tests/`: asignar a
  cliente; asignar a ficha sin rol cliente → 400; sin autorización → 401/403. Cobertura ≥80%.
- [x] **6.2** Frontend — Vitest + RTL: grilla de precios y selector de lista en la ficha; estados
  vacío/carga/error y feedback de error mapeado al campo.
- [x] **6.3** E2E — `npx playwright test` incluyendo WebKit (Safari/iOS): flujo de alta de precio e
  inputs numéricos decimales.
- [x] **6.4** Integración — Verificar reversibilidad de la migración (reverse + migrate sin pérdida) y
  ausencia de warnings de React en consola.
- [x] **6.5** Definition of done — Todos los gates en verde localmente: `ruff`, `mypy`, `bandit`,
  `pip-audit`, `pytest`; `eslint`, `tsc`, `npm audit`, `vitest`, `playwright`. Antes de cerrar el change.
