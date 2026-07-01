# Propuesta: add-products

> **Fase 5.** Capability `products` (inicia) · **Depende de:** F1 (auth), F2 (access-control) ·
> **Desbloquea:** F6, F7, F11, F13, F15 · **Requerimientos:** 4.1, 4.3, 16.2.
> **Fuente de verdad:** `openspec/config.yaml`. Ante conflicto, manda el `config.yaml`.

## 1. El Problema o Necesidad de Negocio

El sistema todavía no tiene un catálogo de productos. Sin él no hay sobre qué registrar inventario:
un Ingreso de mercadería necesita un producto y su unidad, el Kardex necesita la categoría para
estructurar movimientos y plazos de caducidad, la Merma necesita los parámetros del rango por
categoría, y los Precios necesitan productos a los cuales asociar listas.

`products` es el **maestro de inventario**: categorías (que definen caducidad, tipo de ingreso y la
estructura del rango de merma), productos y la tabla de unidades de medida con base en libras. Es
precondición dura de F6 (pricing), F7 (bulk-import), F11 (kardex), F13 (merma) y F15 (orders). Es
prioritario porque ninguna fase de operación o financiera puede avanzar sin él.

## 2. Alcance Crítico

### In-Scope (Lo que se va a construir)

- **Categoría** (`Category`): nombre único entre vivas, días de caducidad (default 7), tipo de ingreso
  (GAVETA/PESO) y la **estructura** del rango de merma proporcional (`merma_min`, `merma_max`,
  `reference_qty` default 100 lb). Los valores de merma son **nullable** hasta que el cliente los
  provea (pendiente #1); la estructura no se bloquea.
- **Producto** (`Product`): nombre único entre vivos, categoría existente (FK) y unidad de medida
  existente (FK).
- **Unidad de medida** (`UnitOfMeasure`): nombre, símbolo y factor de conversión a la base (libras = 1).
  Se siembran **libras** (factor 1) y **kilogramos**. La conversión es estructura para uso futuro;
  **no** se aplica en esta fase.
- **Soft delete clase 2** para los tres catálogos (`deleted_at` + manager que filtra + unicidad parcial
  entre vivos). La unicidad de nombre y la baja bloqueada por dependencias las gobierna el **service**
  con `Conflict` (409), igual que F4.
- **Autorización:** módulo `products` registrado en el catálogo de `access-control` (F2) con las
  acciones `read/create/update`.
- **Contratos de datos:** serializers DRF write/read de las tres entidades → OpenAPI; el frontend
  **genera** tipos TS + Zod desde el schema.
- **Frontend:** pantallas de catálogo (categorías, productos, unidades) en `src/features/products/`.

### Out-of-Scope (Prohibiciones Estrictas)

- **Backend:** Toda persistencia MUST ser PostgreSQL vía Django ORM. Sin SQL raw salvo justificación explícita.
- **Backend:** Las transacciones multi-tabla (escritura + auditoría) MUST usar `transaction.atomic()` con rollback total.
- **Backend:** Los tres catálogos MUST heredar `SoftDeleteModel` (soft delete clase 2); MUST NOT modelarse como documentos con máquina de estado ni como append-only.
- **Backend:** La unicidad de nombre MUST gobernarse en `services.py` con `Conflict` (409); MUST NOT usarse `UniqueValidator`/`UniqueTogetherValidator` de DRF (patrón establecido en F4).
- **Frontend:** Los colores hardcodeados MUST NOT usarse; todo estilo MUST usar tokens del theme (shadcn/Tailwind) con modo claro y oscuro.
- **Seguridad:** Las credenciales MUST NOT almacenarse en el código; MUST gestionarse vía `.env` / GCP Secret Manager.
- **Alcance:** Las **listas de precios** (4.2) quedan para F6; el producto no lleva precio aquí. Los **valores numéricos** del rango de merma quedan pendientes del cliente (#1). La **aplicación y costeo** de la merma quedan para F13. La **aplicación** de los factores de conversión es uso futuro. No se crea CRUD completo "por si acaso" (YAGNI): solo lo necesario para maestro de inventario.

## 3. Evaluación de Impacto

### Modelo de Datos (PostgreSQL)

- **Tres tablas nuevas** en la app `products`: `products_categories`, `products_products`,
  `products_units_of_measure`. Las tres heredan `SoftDeleteModel` (clase 2): `deleted_at` + manager
  que filtra + **índice único parcial** sobre `name` (`WHERE deleted_at IS NULL`).
- **FK con `on_delete=PROTECT`:** `Product.category` → `Category`, `Product.unit_of_measure` →
  `UnitOfMeasure`. PROTECT impide borrar a nivel ORM una categoría/unidad con productos; la baja
  lógica con dependencias se bloquea además en el service (409, mensaje en español).
- **Pesos como `DecimalField`** (nunca `FloatField`): `merma_min`/`merma_max`/`reference_qty` en libras;
  `conversion_factor` con precisión suficiente para kilogramos.
- **Migración** reversible (CreateModel + AddConstraint) y **data migration idempotente** (con
  `reverse_code`) que siembra las unidades base (libras, kilogramos).

### Lógica de Negocio y API

- **Endpoints CRUD** de categorías, productos y unidades, derivados del flujo de mantenimiento del
  catálogo (no hay máquina de estado): list/retrieve/create/update/destroy. `destroy` es soft delete.
- **`apps/products/services.py`** concentra la unicidad de nombre (409 `Conflict`, sin `UniqueValidator`),
  la regla de baja de categoría con productos vivos (409) y la integridad de FK. Las escrituras
  (create/update/baja) se decoran con `@audit(action, entity)`. Los ViewSets son delgados y delegan.
- **No** se modifica FIFO, costeo, merma valorizada, CxC ni CxP: este cambio solo entrega maestro.

### Flujo del Usuario (UI)

- Recursos nuevos en Refine bajo `src/features/products/`: listados y formularios de **categorías**
  (caducidad, tipo de ingreso, campos del rango de merma), **productos** (selección de categoría y
  unidad) y **unidades de medida**. Rutas protegidas.
- Roles afectados: el acceso lo decide el **perfil** (F2), no el `role` nominal; las acciones
  `read/create/update` del módulo `products` gobiernan ver/crear/editar/dar de baja.
- Cada pantalla cubre los estados vacío/carga/error/éxito; inputs numéricos ≥16px en iOS (pesos
  decimales); áreas táctiles ≥44px; colores solo desde tokens del theme.

### Cadena de Trazabilidad

No se altera la cadena de trazabilidad (Ingreso → Kardex → Entrega → Cobro / Ingreso → CxP → Pago).
`products` es maestro: las fases que consumen este catálogo (F11, F13, F12, F15/F16) construyen la
trazabilidad sobre él, pero F5 no genera movimientos de Kardex ni documentos.

## 4. Riesgos y Rollback

### Riesgo Principal

La **integridad referencial de la baja**: dar de baja una categoría o unidad referenciada por
productos vivos dejaría productos huérfanos o inconsistentes. Se mitiga en dos capas: `on_delete=PROTECT`
en el ORM y la verificación explícita en el service (409 antes de marcar `deleted_at`). Riesgo
secundario: que la unicidad parcial entre vivos permita reutilizar el nombre de un registro dado de
baja — comportamiento **deseado** para catálogos clase 2, validado por test.

### Criterio de Aborto

Abortar si el catálogo de módulos/acciones de `access-control` (F2, `apps/authz/catalog.py`) no está
disponible: sin él, el módulo `products` no puede registrarse ni protegerse por perfil. Condición
verificable: `apps.authz.catalog.PERMISSION_CATALOG` no importable o sin las acciones `read/create/update`.
Abortar también si la migración inversa (`migrate products zero`) falla tras 2 intentos de corrección.

### Plan de Rollback

La migración estructural es reversible (Django genera el reverse de CreateModel/AddConstraint). La data
migration de unidades incluye `reverse_code` que elimina solo las filas sembradas (idempotente). No hay
recálculo de saldos ni datos derivados que limpiar: al ser maestro recién creado, revertir la migración
deja el sistema en el estado previo a F5.
