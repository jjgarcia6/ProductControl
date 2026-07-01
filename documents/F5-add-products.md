# Change: add-products — Fase 5

**Capability:** `products` (inicia) · **Depende de:** F1 (auth), F2 (access-control) · **Desbloquea:** F6, F7, F11, F13, F15
**Fuente de verdad:** `openspec/config.yaml`. Ante conflicto, manda el `config.yaml`.
**Requerimientos:** 4.1, 4.3, 16.2.

> **Cómo usar este archivo.** Consolida los cuatro artefactos del change. Cada sección de primer nivel mapea a un archivo dentro de `openspec/changes/add-products/`:
> - `## 1) PROPOSAL` → `proposal.md`
> - `## 2) SPECS` → `specs/products/spec.md` (delta)
> - `## 3) DESIGN` → `design.md`
> - `## 4) TASKS` → `tasks.md`
>
> Requirements en RFC 2119 (MUST/MUST NOT/SHALL); Scenarios en español (DADO/CUANDO/ENTONCES). Código e identificadores en inglés; documentación en español.

---

## 1) PROPOSAL → proposal.md

### Intent

Entregar el catálogo de productos: categorías (que definen caducidad, tipo de ingreso y la estructura del rango de merma), productos y la tabla de unidades de medida con base en libras. Es maestro de inventario: lo consumen Kardex (F11), Merma (F13), Ingresos (F12), Pedidos/Entregas (F15/F16) y Precios (F6).

### Scope (qué cambia)

- **Categoría** (`Category`): nombre, días de caducidad (default 7), tipo de ingreso (gaveta o peso) y la **estructura del rango de merma** proporcional (mínimo, máximo, cantidad de referencia).
- **Producto** (`Product`): nombre, categoría, unidad de medida.
- **Unidad de medida** (`UnitOfMeasure`): nombre, símbolo y factor de conversión a la base (libras = 1). Se siembran **libras** (base) y **kilogramos**.
- Soft delete clase 2 para los tres catálogos.

### Decisiones de modelado (validadas)

- **Rango de merma proporcional:** `merma_min`, `merma_max` y `reference_qty` (default 100 lb). Los tres valores **nullable** hasta que el cliente los provea (pendiente #1); la estructura no se bloquea.
- **Unidades sembradas:** libras (factor 1) y kilogramos. La conversión es estructura para uso futuro; **no** se aplica en esta fase.
- **Unicidad por el service (409):** la unicidad de nombre de los tres catálogos la gobiernan los `services` con `Conflict` (409), sin `UniqueValidator` de DRF — consistente con el patrón de F4 (`apps/directory/services.py`, `apps/credit/services.py`). La baja de categoría con productos vivos también es 409. Solo la validación de choices (tipo de ingreso) y de FK existente (categoría/unidad) permanece como 400 de serializer.
- **Auditoría de escrituras:** create/update/baja de los tres catálogos se auditan con `@audit(action, entity)` (`CREATE`/`UPDATE`/`SOFT_DELETE`), igual que `authz.Profile` y `directory.Ficha`.

### Impacto en el modelo de datos (antes que UI — DIP)

- Tablas `Category`, `Product`, `UnitOfMeasure` (app `products`), todas con soft delete clase 2 (`deleted_at`, manager que filtra, índices únicos parciales entre vivos). Migración reversible.
- Data migration que siembra las unidades base (libras, kilogramos).
- Módulo `PRODUCTS` y sus acciones registrados en el catálogo de `access-control` (F2).

### Fuera de alcance

- **Listas de precios** (4.2) → F6 (`pricing`). El producto no lleva precio aquí.
- **Valores numéricos del rango de merma** → pendiente cliente #1 (la estructura no se bloquea).
- **Aplicación y costeo de la merma** (fórmulas nominal/efectivo, merma valorizada) → F13 (`merma`). F5 solo deja los parámetros.
- **Aplicación de los factores de conversión** → uso futuro; aquí solo se registran.

### Verificación de invariantes

- Soft delete **clase 2** (catálogos): `deleted_at` + manager que filtra + unicidad parcial.
- Pesos como **decimales en libras** (unidad base). No toca Kardex, período, costeo ni documentos (es maestro).
- Errores por el contrato uniforme; permisos por perfil (F2).

### Criterio de aborto (verificable)

Si el catálogo de módulos/acciones de `access-control` (F2, `apps/authz/catalog.py`) no está disponible, abortar: el módulo `PRODUCTS` no puede registrarse ni protegerse por perfil sin él.

---

## 2) SPECS → specs/products/spec.md

# Delta para la capability `products`

## ADDED Requirements

### Requirement: Categoría de producto
La categoría MUST registrar un nombre único entre categorías vivas, los días de caducidad desde el ingreso (default 7), el tipo de ingreso (gaveta o peso) y la estructura del rango de merma: mínimo, máximo y cantidad de referencia (default 100). Los valores del rango de merma MAY quedar sin definir hasta que el cliente los provea. Los pesos MUST expresarse como decimales en libras. Los errores MUST seguir el contrato uniforme.

#### Scenario: Crear una categoría
- DADO un nombre único, días de caducidad y un tipo de ingreso válido
- CUANDO se crea la categoría
- ENTONCES el sistema la persiste con la estructura del rango de merma disponible para configurarse
- Y registra la operación en `audit_log` con acción `CREATE`

#### Scenario: Categoría sin valores de merma definidos
- DADO una categoría cuyos valores de rango de merma aún no se conocen
- CUANDO se crea la categoría sin esos valores
- ENTONCES el sistema la persiste con el rango de merma sin definir

#### Scenario: Nombre de categoría duplicado
- DADO una categoría viva con un nombre
- CUANDO se intenta crear otra categoría con el mismo nombre
- ENTONCES el sistema responde 409 con `{detail}` indicando que ya existe una categoría con ese nombre (la unicidad la gobierna el service)

#### Scenario: Tipo de ingreso inválido
- CUANDO se intenta crear una categoría con un tipo de ingreso distinto de gaveta o peso
- ENTONCES el sistema responde 400 con `{campo: [mensajes]}` en el campo del tipo de ingreso

### Requirement: Producto
El producto MUST registrar un nombre único entre productos vivos, una categoría existente y una unidad de medida existente.

#### Scenario: Crear un producto
- DADO una categoría y una unidad de medida existentes
- CUANDO se crea el producto con un nombre único
- ENTONCES el sistema lo persiste asociado a su categoría y unidad

#### Scenario: Producto con categoría inexistente
- CUANDO se intenta crear un producto con una categoría que no existe
- ENTONCES el sistema responde 400 con `{campo: [mensajes]}` en el campo de la categoría

### Requirement: Unidad de medida
La unidad de medida MUST registrar nombre, símbolo y un factor de conversión a la unidad base (libras = 1). Tras la inicialización MUST existir la unidad base (libras) y kilogramos. Los factores de conversión se almacenan para uso futuro y no se aplican en esta fase.

#### Scenario: Unidades base disponibles tras la inicialización
- DADO un sistema recién inicializado
- CUANDO se siembran las unidades de medida
- ENTONCES existen libras (factor 1) y kilogramos con su factor de conversión

### Requirement: Baja lógica de catálogos
Categorías, productos y unidades MUST usar soft delete clase 2 (baja con `deleted_at`, exclusión de los listados por defecto, unicidad parcial entre vivos). Una categoría con productos vivos asociados MUST NOT poder darse de baja sin tratar antes esos productos.

#### Scenario: Baja de una categoría sin productos
- DADO una categoría sin productos vivos asociados
- CUANDO se da de baja
- ENTONCES el sistema la marca como eliminada (`deleted_at`) y deja de listarla
- Y registra la operación en `audit_log` con acción `SOFT_DELETE`

#### Scenario: Baja de una categoría con productos
- DADO una categoría con al menos un producto vivo
- CUANDO se intenta darla de baja
- ENTONCES el sistema responde 409 con `{detail}` indicando que tiene productos asociados

---

## 3) DESIGN → design.md

### Capa de datos

- **App `products`**. Las tres entidades heredan el modelo de soft delete clase 2 (`deleted_at`, manager que filtra los vivos, índices únicos parciales `WHERE deleted_at IS NULL`).
- **`Category`**:
  - `name` (único parcial entre vivos), `shelf_life_days` (int, default 7), `intake_type` (choices GAVETA/PESO).
  - Rango de merma: `merma_min`, `merma_max` (Decimal, nullable), `reference_qty` (Decimal, default 100). Pesos en libras (Decimal con precisión consistente, p. ej. `max_digits=12, decimal_places=3`).
- **`Product`**: `name` (único parcial), `category` (FK, `on_delete=PROTECT`), `unit_of_measure` (FK, `on_delete=PROTECT`).
- **`UnitOfMeasure`**: `name`, `symbol`, `conversion_factor` (Decimal = número de libras equivalente a 1 unidad; libras = 1, kilogramos ≈ 2.20462). Sembrada por data migration.
- Migraciones reversibles; la data migration de unidades es idempotente.

### Capa de API

- **Contrato OpenAPI primero:** endpoints CRUD de categorías, productos y unidades, anotados con `drf-spectacular`; regenerar `schema.yml`.
- **Permisos por perfil:** registrar el módulo `PRODUCTS` y sus acciones en `apps/authz/catalog.py`; proteger los endpoints con la permission class de F2.
- **Lógica en services:** la unicidad de nombre (entre vivos, `Conflict` 409, sin `UniqueValidator`), la regla de baja de categoría con productos (409) y la integridad de FK viven en `apps/products/services.py`; viewsets delgados. Las escrituras (create/update/baja) se decoran con `@audit(action, entity)`. Listados excluyen los eliminados por defecto (manager).

### Capa de frontend

- **Pantallas de catálogo** en `src/features/products/`: categorías (con días de caducidad, tipo de ingreso y los campos del rango de merma), productos (con selección de categoría y unidad) y unidades de medida.
- Validación Zod (generada del OpenAPI); pesos como decimales. La estructura del rango de merma se muestra editable aunque sus valores estén vacíos (pendiente del cliente).
- Gating por perfil; estados vacío/carga/error/éxito; tokens del theme; `FieldError` compartido; inputs numéricos ≥16px iOS (pesos decimales).

### Seguridad

- Acceso por perfil (F2). Sin datos sensibles en este catálogo.

### Qué NO se hace (YAGNI)

Sin precios (F6), sin aplicación ni costeo de merma (F13), sin aplicar factores de conversión (uso futuro), sin variantes/SKU ni atributos extra de producto no pedidos.

---

## 4) TASKS → tasks.md

> Orden obligatorio del `config.yaml`: Contrato (OpenAPI) → Migraciones Django → Backend (services) → Frontend → Seguridad → Pruebas. Cada tarea nombra el archivo/módulo exacto. Definition of done global: todos los gates del pipeline en verde localmente antes de declarar el change completo.

### A. Contrato y modelo (OpenAPI + datos)
- [ ] A.1 Crear la app `products` y los modelos `Category`, `Product`, `UnitOfMeasure` (soft delete clase 2; rango de merma con `merma_min`/`merma_max`/`reference_qty`; FK con `PROTECT`).
- [ ] A.2 Definir serializers de las tres entidades en `apps/products/serializers.py` (unicidad, validación de tipo de ingreso, FK existentes).
- [ ] A.3 Registrar el módulo `PRODUCTS` y sus acciones en `apps/authz/catalog.py`.
- [ ] A.4 Anotar los endpoints con `drf-spectacular` y regenerar `schema.yml`.

### B. Migraciones
- [ ] B.1 `makemigrations products`; confirmar reversibilidad.
- [ ] B.2 Data migration idempotente que siembra las unidades base (libras factor 1, kilogramos).
- [ ] B.3 `migrate` y verificar arranque limpio.

### C. Backend (services + vistas)
- [ ] C.1 Implementar en `apps/products/services.py` la unicidad de nombre entre vivos (`Conflict` 409, sin `UniqueValidator`) y la regla de baja de categoría con productos vivos (409). Decorar create/update/baja con `@audit(action, entity)` (`CREATE`/`UPDATE`/`SOFT_DELETE`).
- [ ] C.2 Implementar los viewsets delgados de categoría, producto y unidad, protegidos por la permission class de F2 (módulo `PRODUCTS`); registrar rutas. Listados excluyen eliminados por defecto.
- [ ] C.3 Verificar que todos los errores salen por el contrato uniforme.

### D. Frontend
- [ ] D.1 Regenerar tipos + Zod desde `schema.yml` (`npm run codegen`).
- [ ] D.2 Construir las pantallas de categorías (con caducidad, tipo de ingreso y rango de merma), productos y unidades en `src/features/products/`.
- [ ] D.3 Gating por perfil; estados vacío/carga/error/éxito; tokens del theme; `FieldError` compartido; inputs numéricos ≥16px iOS.

### E. Seguridad
- [ ] E.1 Verificar que las acciones del catálogo respetan los permisos por perfil (F2).

### F. Pruebas (gate)
- [ ] F.1 Tests de backend en `apps/products/tests/` cubriendo todos los Scenarios (crear categoría; categoría sin valores de merma; nombre duplicado; tipo de ingreso inválido; crear producto; categoría inexistente; unidades sembradas con factores; baja de categoría sin/con productos).
- [ ] F.2 Tests de frontend (Vitest + RTL) de los formularios de categoría y producto.
- [ ] F.3 Ejecutar y dejar en verde: `ruff`, `mypy --strict`, `bandit`, `pip-audit`, `pytest` (cobertura ≥80%); `eslint`, `tsc`, `npm audit`, `vitest`. Confirmar antes de declarar el change completo.
