# Tareas: add-products

<!-- Orden de fases REQUIRED: Contrato → Migraciones → Backend → Frontend → Seguridad → Pruebas. -->
<!-- No avanzar a la siguiente fase si hay ítems sin completar en la anterior. -->
<!-- Definition of done global: todos los gates del pipeline en verde localmente antes de cerrar el change. -->

## Fase 0: Contrato y Sincronización Inicial

- [x] **0.1** Backend — Crear `backend/apps/products/serializers.py` con `CategoryWriteSerializer`/
  `CategoryReadSerializer`, `ProductWriteSerializer`/`ProductReadSerializer`,
  `UnitOfMeasureWriteSerializer`/`UnitOfMeasureReadSerializer`. Cada campo con `help_text`. Pesos y
  `conversion_factor` con `DecimalField` (nunca `FloatField`). La unicidad NO se valida aquí (la
  gobierna el service): NO usar `UniqueValidator`/`UniqueTogetherValidator`.
- [x] **0.2** Backend — Anotar los endpoints con `drf-spectacular` y regenerar el OpenAPI:
  `uv run python manage.py spectacular --file schema.yml`. Verificar que expone las tres entidades.
- [x] **0.3** Frontend — Regenerar tipos + Zod desde `../backend/schema.yml`: `npm run codegen`.
  Re-exportarlos en `frontend/src/features/products/types/products.types.ts`. NO escribir Zod a mano.
- [x] **0.4** Global — Confirmar que no hacen falta variables nuevas en `backend/.env.example` ni
  `frontend/.env.example` (este change no introduce ninguna).

## Fase 1: Modelo de Datos y Migraciones

- [x] **1.1** Crear `backend/apps/products/models.py`: `UnitOfMeasure`, `Category`, `Product` heredando
  `SoftDeleteModel` (clase 2). `IntakeType` (`GAVETA`/`PESO`). `Category` con `shelf_life_days`
  (default 7), `merma_min`/`merma_max` (nullable), `reference_qty` (default 100). `Product` con FK
  `category`/`unit_of_measure` `on_delete=PROTECT`. `UniqueConstraint` PARCIAL sobre `name`
  (`condition=Q(deleted_at__isnull=True)`) en las tres tablas. Registrar la app en `INSTALLED_APPS`.
- [x] **1.2** Generar migración: `uv run python manage.py makemigrations products` (`0001_initial`).
- [x] **1.3** Crear la data migration `0002_seed_base_units.py` con `RunPython(seed, unseed)`:
  `seed` hace `get_or_create` de libras (factor 1) y kilogramos (factor 2.204623) — idempotente;
  `unseed` (reverse) hace `hard_delete` solo de esas dos filas. Nunca dejar `reverse_code` en noop.
- [x] **1.4** Aplicar: `uv run python manage.py migrate`. Probar el reverse:
  `uv run python manage.py migrate products zero` y re-aplicar. Verificar que arranca limpio.

## Fase 2: Lógica de Negocio y API (Backend)

- [x] **2.1** Crear `backend/apps/products/services.py`: `create_*`/`update_*` con la unicidad de nombre
  entre vivos (`Conflict` 409, excluyendo el propio pk al editar) y validación de FK; `deactivate_category`/
  `deactivate_unit` que lanzan `Conflict` 409 si hay productos vivos asociados; `deactivate_product`.
  Cada escritura en `transaction.atomic()` y decorada con `@audit(action, entity)`
  (`CREATE`/`UPDATE`/`SOFT_DELETE`). Sin capturar `Exception` genérico.
- [x] **2.2** Registrar el módulo `products` en `backend/apps/authz/catalog.py`:
  añadir `MODULE_PRODUCTS = "products"` a `PERMISSION_CATALOG` con `{read, create, update}`. NO tocar
  el seed de perfiles ni los campos sensibles.
- [x] **2.3** Crear `backend/apps/products/views.py`: `APIView` delgados (un par list/create + detail
  por recurso; GET/POST/PATCH/DELETE) que delegan en los services; el DELETE invoca la baja lógica.
  Proteger con la permission class por perfil de F2 vía `required_permissions` por método (módulo
  `products`: `read`/`create`/`update`; el DELETE usa `update`). Convención establecida en F1–F4.
- [x] **2.4** Registrar rutas en `backend/apps/products/urls.py` bajo `/products`
  (`categories`, `products`, `units`) e incluirlas en el router raíz.

## Fase 3: Integración de Datos (Frontend — Hooks)

- [x] **3.1** Crear `useCategories.ts`, `useProducts.ts`, `useUnits.ts` en
  `frontend/src/features/products/hooks/`: envolver `useList`/`useOne`/`useCreate`/`useUpdate`/`useDelete`
  de Refine con `resource` descriptivo. NO montar TanStack Query en paralelo.
- [x] **3.2** Validar en cada hook que la respuesta cumple el schema Zod generado en Fase 0 antes de
  exponer los datos; lanzar error descriptivo si no coincide.

## Fase 4: Componentes y Páginas (Frontend — UI)

- [x] **4.1** Crear los contenedores `CategoryList.tsx`, `ProductList.tsx`, `UnitList.tsx` en
  `features/products/components/`: consumen los hooks de Fase 3; cubren estados vacío/carga/error/éxito.
- [x] **4.2** Crear los presentacionales `CategoryForm.tsx` (caducidad, tipo de ingreso, rango de merma
  con valores opcionales), `ProductForm.tsx` (selección de categoría y unidad) y `UnitForm.tsx`: reciben
  solo props; React Hook Form + `zodResolver`; todo color desde tokens del theme (cero hex); áreas
  táctiles ≥44px; inputs numéricos ≥16px en iOS (pesos decimales).
- [x] **4.3** Actualizar `frontend/src/features/products/index.ts` con las exportaciones explícitas.
- [x] **4.4** Crear las dumb pages `CategoriesPage.tsx`, `ProductsPage.tsx`, `UnitsPage.tsx` en
  `frontend/src/pages/products/`: importan y renderizan el contenedor; sin estado ni fetch directos.
- [x] **4.5** Declarar las rutas protegidas en `App.tsx` (`<Authenticated>` + `ForcePasswordChangeGuard`)
  con `lazy(() => import(...))`, consistente con F1–F4 (NO un array `resources` de Refine). El gating
  por perfil (módulo `products`) se resuelve en el contenedor con `usePermissions().canDo(...)`.

## Fase 5: Seguridad y DevSecOps

- [x] **5.1** Backend — `uv run ruff check apps/products` y `uv run mypy apps/products` (strict). Corregir todo.
- [x] **5.2** Backend — `uv run bandit -c pyproject.toml -r apps/products`. Resolver toda alerta ≥ MEDIUM.
- [x] **5.3** Frontend — `npm run lint` y `npm run typecheck` sobre `src/features/products/`. Corregir todo.
- [x] **5.4** Global — Verificar que no hay secretos ni credenciales en el código nuevo.
- [x] **5.5** Dependencias — `uv run pip-audit` y `npm audit --audit-level=moderate` (sin deps nuevas, igual gate).
- [x] **5.6** UI — Validar contraste WCAG AA en los formularios y listados nuevos en modo claro y oscuro.

## Fase 6: Pruebas y Validación Final

- [x] **6.1** Backend — `backend/apps/products/tests/` cubriendo todos los Scenarios del spec:
  crear categoría (+audit `CREATE`); categoría sin valores de merma; tipo de ingreso inválido (400);
  nombre de categoría duplicado (409); crear sin perfil autorizado (403); crear producto; categoría
  inexistente (400); nombre de producto duplicado (409); unidades sembradas idempotentes con factores;
  baja de categoría sin productos (+audit `SOFT_DELETE`); baja de categoría con productos (409);
  reutilización del nombre tras baja. Ejecutar con Postgres local
  (`DATABASE_URL=...localhost:5433... uv run pytest apps/products`).
- [x] **6.2** Frontend — `CategoryForm`/`ProductForm` (Vitest + RTL): flujo de éxito, feedback de error
  (400 mapeado al campo, 409 como aviso) y estados vacío/carga/error. Accesibilidad básica (roles ARIA).
- [x] **6.3** E2E — `npx playwright test` incluyendo WebKit (Safari/iOS): validar el alta de categoría y
  producto y los inputs numéricos decimales.
- [x] **6.4** Integración — Sin operaciones bloqueantes que choquen con el timeout de Cloud Run; sin
  errores/warnings en consola; migración reversible verificada (Fase 1.4).
- [x] **6.5** Definition of done — Todos los gates (backend y frontend) en verde, ejecutados localmente,
  antes de declarar el change completo. Cobertura ≥80% global.
