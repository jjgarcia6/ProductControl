# Change: add-pricing — Fase 6

**Capability:** `pricing` (inicia) · modifica `directory` · **Depende de:** F4 (directory), F5 (products) · **Desbloquea:** F16
**Fuente de verdad:** `openspec/config.yaml`. Ante conflicto, manda el `config.yaml`.
**Requerimientos:** 4.2.

> **Cómo usar este archivo.** Consolida los cuatro artefactos del change. Cada sección de primer nivel mapea a un archivo dentro de `openspec/changes/add-pricing/`:
> - `## 1) PROPOSAL` → `proposal.md`
> - `## 2) SPECS` → dos deltas: `specs/pricing/spec.md`, `specs/directory/spec.md`
> - `## 3) DESIGN` → `design.md`
> - `## 4) TASKS` → `tasks.md`
>
> Requirements en RFC 2119 (MUST/MUST NOT/SHALL); Scenarios en español (DADO/CUANDO/ENTONCES). Código e identificadores en inglés; documentación en español.

---

## 1) PROPOSAL → proposal.md

### Intent

Entregar las listas de precios y su asignación a clientes. Cada lista (normal o descarte) fija el precio de los productos que se venden bajo ella; una ficha de cliente tiene una lista asignada, que determinará el precio de sus entregas. Completa el FK ficha→lista que se difirió en F4. Es precondición de las entregas (F16).

### Scope (qué cambia)

- **Lista de precios** (`PriceList`): nombre, tipo (normal o descarte). Soft delete clase 2.
- **Precio por producto en lista** (`PriceListItem`): un precio por (lista, producto).
- **Asignación de lista a ficha de cliente:** completa `directory` con el FK `price_list` (una lista por ficha), realizada por un perfil autorizado (supervisor/jefe).

### Decisiones de modelado (validadas)

- **Una lista por cliente:** FK simple `price_list` (nullable) en la Ficha, no una relación múltiple. El tipo de esa lista (normal/descarte) determinará después si la entrega es venta de descarte.
- **Integridad asignación↔rol:** solo una ficha con rol **cliente** puede tener lista asignada.

### Impacto en el modelo de datos (antes que UI — DIP)

- Tablas `PriceList` y `PriceListItem` (app `pricing`), soft delete clase 2. `unique(price_list, product)`. Migración reversible.
- `directory.Ficha` gana `price_list` (FK nullable a `pricing.PriceList`, `on_delete=PROTECT`). Migración sobre `directory`.
- Módulo `PRICING` y sus acciones registrados en el catálogo de `access-control` (F2).

### Flujo del usuario (UI)

- **Roles afectados:** el **Jefe** y el **Supervisor** (perfiles con el módulo `PRICING` en read/create/update) gestionan listas y precios; la asignación de lista a la ficha la realiza un perfil autorizado (supervisor/jefe) desde el formulario de Directorio. El **Responsable de ruta** y el **Usuario** no ven ni operan estas pantallas (gating por perfil).
- Rutas protegidas nuevas en `pricing`; el selector de lista se integra en la pantalla existente de ficha (Directorio), visible solo si la ficha tiene rol cliente. Estados vacío/carga/error/éxito requeridos; tokens del theme; sin hex literales.

### Cadena de trazabilidad

No se altera la cadena de trazabilidad (Ingreso → Kardex → Entrega → Cobro / Ingreso → CxP → Pago). `pricing` es maestro: la lista solo **provee** el precio que la entrega (F16) consumirá y congelará en su snapshot. En F6 no se generan movimientos de Kardex, documentos ni saldos.

### Fuera de alcance

- **Inmutabilidad del precio en la entrega** (snapshot al pasar a GENERADO) → F16 (`deliveries`). La regla 3.3 —no se cambia el precio sobre una entrega emitida; se descarta y se regenera— se implementa allí. En F6 la lista es editable libremente.
- **Efecto del tipo descarte** (precio reducido para producto próximo a vencer, marca de venta de descarte en la entrega) → F16. En F6 el tipo es solo un atributo de la lista.
- **Prohibiciones estrictas (heredadas de la plantilla):** persistencia SOLO PostgreSQL vía Django ORM (sin SQL raw); operaciones multi-tabla en `transaction.atomic()` con rollback total; catálogos heredan el mixin de soft delete (clase 2); cero colores hardcodeados (solo tokens del theme, claro y oscuro); credenciales SOLO por `.env`/GCP Secret Manager, nunca en el repo; sin refactorizaciones ajenas al dominio (YAGNI).

### Verificación de invariantes

- Soft delete **clase 2** (catálogo). Precios decimales en USD.
- No toca Kardex, período, costeo ni documentos (es maestro).
- Errores por el contrato uniforme; permisos por perfil (F2).

### Riesgos y rollback

- **Riesgo principal:** la migración `AddField` de `price_list` (FK con `on_delete=PROTECT`) sobre `directory.Ficha` es aditiva y nullable, pero debe ser **reversible** sobre una tabla `directory` que ya contiene datos de F4; un reverse que no restaure el estado previo bloquearía el rollback.
- **Criterio de aborto (verificable):** abortar si (a) `directory.Ficha` (F4) o `products.Product` (F5) no están migrados —la lista necesita productos para fijar precios y la ficha para asignarse—, o (b) la migración inversa (`migrate directory <anterior>` y `migrate pricing zero`) falla tras 2 intentos de corrección, o (c) los tests de los Scenarios no quedan en verde.
- **Plan de rollback:** ambas migraciones (`pricing` y el `AddField` en `directory`) tienen reverse estándar de Django; no se requiere data migration (campos nuevos, sin backfill). Revertir en orden inverso: primero `directory` al estado anterior, luego `pricing zero`.

---

## 2) SPECS

### 2.1 → specs/pricing/spec.md

# Delta para la capability `pricing`

## ADDED Requirements

### Requirement: Lista de precios
La lista MUST tener un nombre único entre listas vivas y un tipo (normal o descarte). Usa soft delete clase 2. Los errores MUST seguir el contrato uniforme.

#### Scenario: Crear una lista normal y una de descarte
- DADO un nombre único
- CUANDO se crea una lista de tipo normal y otra de tipo descarte
- ENTONCES el sistema las persiste con su tipo

#### Scenario: Nombre de lista duplicado
- DADO una lista viva con un nombre
- CUANDO se intenta crear otra lista con el mismo nombre
- ENTONCES el sistema responde 400 con `{campo: [mensajes]}` en el campo del nombre

### Requirement: Precio de producto en lista
Cada par (lista, producto) MUST tener a lo sumo un precio. El precio MUST ser un decimal no negativo.

#### Scenario: Agregar un producto con su precio
- DADO una lista y un producto existentes
- CUANDO se agrega el producto a la lista con un precio válido
- ENTONCES el sistema persiste el precio para ese par

#### Scenario: Producto duplicado en la misma lista
- DADO un producto ya presente en una lista
- CUANDO se intenta agregarlo de nuevo a la misma lista
- ENTONCES el sistema responde **409 Conflict** con `{detail}` del contrato uniforme
- Y el frontend MUST mostrar el mensaje al usuario indicando el duplicado

#### Scenario: Precio negativo
- CUANDO se intenta fijar un precio negativo
- ENTONCES el sistema responde **400** con `{campo: [mensajes]}` en el campo del precio
- Y el frontend MUST mapear el mensaje al campo del precio en el formulario

#### Scenario: Gestionar precios sin autorización
- DADO un usuario sin el módulo `PRICING` en su perfil (o sin sesión activa)
- CUANDO intenta crear/editar una lista o un precio
- ENTONCES el sistema responde **401** (sin sesión) o **403** (`{detail}` genérico) según corresponda
- Y el frontend MUST redirigir al login (401) u ocultar/deshabilitar la acción (403)

### Requirement: Baja de lista en uso
Una lista asignada a una o más fichas MUST NOT poder darse de baja sin reasignar antes a esas fichas.

#### Scenario: Baja de una lista sin clientes
- DADO una lista sin fichas asignadas
- CUANDO se da de baja
- ENTONCES el sistema la marca como eliminada y deja de listarla

#### Scenario: Baja de una lista asignada
- DADO una lista asignada a al menos una ficha
- CUANDO se intenta darla de baja
- ENTONCES el sistema responde **409 Conflict** con `{detail}` indicando que está en uso
- Y el frontend MUST mostrar el mensaje señalando que hay fichas que dependen de la lista

### 2.2 → specs/directory/spec.md

# Delta para la capability `directory`

## ADDED Requirements

### Requirement: Asignación de lista de precios a un cliente
Una ficha con rol cliente MAY tener una lista de precios asignada (a lo sumo una). El sistema MUST NOT permitir asignar una lista a una ficha sin rol cliente. La asignación la realiza un perfil autorizado.

#### Scenario: Asignar una lista a un cliente
- DADO una ficha con rol cliente y una lista existente
- CUANDO un perfil autorizado le asigna la lista
- ENTONCES la ficha queda con esa lista asignada
- Y el frontend MUST mostrar una notificación de éxito usando tokens del theme

#### Scenario: Asignar una lista a una ficha sin rol cliente
- DADO una ficha que no tiene rol cliente
- CUANDO se intenta asignarle una lista de precios
- ENTONCES el sistema responde **400** con `{campo: [mensajes]}` indicando que la ficha no es cliente
- Y el frontend MUST mapear el mensaje al campo de la lista en el formulario

#### Scenario: Asignar una lista sin autorización
- DADO un usuario sin el módulo `directory` en update (o sin sesión activa)
- CUANDO intenta asignar una lista a una ficha
- ENTONCES el sistema responde **401** (sin sesión) o **403** (`{detail}` genérico) según corresponda
- Y el frontend MUST redirigir al login (401) u ocultar/deshabilitar el selector (403)

---

## 3) DESIGN → design.md

### Capa de datos

- **App `pricing`**:
  - `PriceList`: `name` (único parcial entre vivas), `type` (choices NORMAL/DESCARTE). Soft delete clase 2.
  - `PriceListItem`: `price_list` (FK), `product` (FK a `products.Product`, `on_delete=PROTECT`), `price` (Decimal `max_digits=12, decimal_places=2`, no negativo). `UniqueConstraint(price_list, product)`.
- **Modifica `directory.Ficha`**: `price_list` (FK a `pricing.PriceList`, `null=True, blank=True, on_delete=PROTECT`). PROTECT es la segunda defensa de la regla "no baja en uso"; la primera es la validación en service.
- Migración reversible en `pricing` y en `directory` (el campo nuevo).

**Tablas e índices / constraints**

| Tabla | Índice / Constraint | Tipo | Justificación |
| :--- | :--- | :--- | :--- |
| `price_lists` | `name` WHERE `deleted_at IS NULL` | unique parcial | nombre único entre listas vivas (soft delete clase 2) |
| `price_list_items` | `(price_list_id, product_id)` | unique compound | a lo sumo un precio por (lista, producto) |
| `price_list_items` | `product_id` → `products.product` | fk `PROTECT` | no borrar un producto con precios asociados |
| `directory_fichas` | `price_list_id` → `price_lists.price_list` | fk `PROTECT` nullable | 2.ª defensa "no baja de lista en uso"; 1 lista por ficha |

**Impacto en invariantes del sistema**

- **Período cerrado:** no aplica — `pricing` no crea documentos con fecha.
- **Kardex FIFO / append-only:** no se toca.
- **Doble costeo:** no se toca (el costeo es de F15; el precio de venta es independiente del costo).
- **Cuadre de ruta:** no aplica.
- **Snapshot inmutable de entrega:** no aplica en F6; la lista es la **fuente** del precio que F16 congelará.
- **Nota de crédito vinculada:** no aplica.
- **Soft delete (3 clases):** `PriceList`/`PriceListItem` = **clase 2** (catálogo, `deleted_at` + manager filtrado). `directory.Ficha` conserva su **clase 3** (estado INACTIVO).
- **Trazabilidad:** no se altera.

### Capa de API

- **Contrato OpenAPI primero:** endpoints de listas, de ítems de precio y de asignación de lista a ficha, anotados con `drf-spectacular`; regenerar `schema.yml`.
- **Permisos por perfil:** registrar el módulo `PRICING` y sus acciones en `apps/authz/catalog.py`; proteger los endpoints con la permission class de F2.
- **Lógica en services:** la integridad asignación↔rol (la ficha debe ser cliente), la unicidad (lista, producto) y la regla de baja en uso viven en `apps/pricing/services.py` (y la asignación, en el service de directory que ya existe); viewsets delgados.
- **Serializers Write/Read separados** por recurso (`...WriteSerializer` para entrada validada, `...ReadSerializer` para salida); cada campo con `help_text` para el OpenAPI. `price` como `DecimalField(max_digits=12, decimal_places=2)`, nunca float.

**Diccionario de datos vivo**

| Entidad | Campo | Tipo (Py / TS) | Descripción | Restricciones |
| :--- | :--- | :--- | :--- | :--- |
| `PriceList` | `name` | `str / string` | nombre visible de la lista | único entre vivas, requerido |
| `PriceList` | `type` | `str / enum` | naturaleza de la lista | `NORMAL` \| `DESCARTE` |
| `PriceListItem` | `price_list` | `UUID / string` | lista a la que pertenece el precio | FK requerido |
| `PriceListItem` | `product` | `UUID / string` | producto tarifado | FK `PROTECT`, único por lista |
| `PriceListItem` | `price` | `Decimal / number` | precio de venta en USD | `>= 0`, 2 decimales |
| `Ficha` | `price_list` | `UUID / string \| null` | lista asignada al cliente | nullable, solo si rol cliente |

**Endpoints de DRF**

| Verbo | Ruta | Write | Read | Códigos HTTP | Roles (perfil) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET/POST` | `/pricing/price-lists` | `PriceListWrite` | `PriceListRead` | 200/201/400/401/403/409 | Jefe, Supervisor |
| `GET/PATCH/DELETE` | `/pricing/price-lists/{id}` | `PriceListWrite` | `PriceListRead` | 200/204/400/401/403/409 | Jefe, Supervisor |
| `GET/POST` | `/pricing/price-lists/{id}/items` | `PriceListItemWrite` | `PriceListItemRead` | 200/201/400/401/403/409 | Jefe, Supervisor |
| `PATCH/DELETE` | `/pricing/price-list-items/{id}` | `PriceListItemWrite` | `PriceListItemRead` | 200/204/400/401/403 | Jefe, Supervisor |
| `PATCH` | `/directory/fichas/{id}/assign-price-list` | `AssignPriceListWrite` | `FichaRead` | 200/400/401/403 | Jefe, Supervisor |

**Servicios de negocio**

| Servicio | Método | Responsabilidad única | Transaccional |
| :--- | :--- | :--- | :--- |
| `pricing/services.py` | `create_price_list()` / `update` | persistir lista, nombre único entre vivas | Sí |
| `pricing/services.py` | `set_price_list_item()` | unicidad (lista, producto) + precio ≥ 0 (409/400) | Sí |
| `pricing/services.py` | `soft_delete_price_list()` | bloquear baja si tiene fichas asignadas (409) | Sí |
| `directory/services.py` | `assign_price_list()` | integridad asignación↔rol cliente (400) | Sí |

### Capa de frontend

- **Pantallas de listas** en `src/features/pricing/`: lista con su tipo, y la grilla de productos con precio (agregar/editar/quitar ítems).
- **Asignación de lista** integrada en el formulario de ficha (feature `directory`): selector de lista visible solo cuando la ficha tiene rol cliente.
- Precios como decimales (2 lugares); Zod generado del OpenAPI; gating por perfil; estados vacío/carga/error/éxito; tokens del theme; `FieldError` compartido; inputs numéricos ≥16px iOS.

**Árbol de directorios de la feature** (solo lo que este cambio crea/modifica)

```
src/features/pricing/
├── components/
│   ├── PriceListsContainer.tsx    # orquesta hooks + subcomponentes
│   ├── PriceListForm.tsx          # presentacional: alta/edición de lista
│   └── PriceItemsGrid.tsx         # presentacional: grilla producto/precio
├── hooks/
│   ├── usePriceLists.ts
│   └── usePriceListItems.ts
├── types/
│   └── pricing.types.ts           # re-exporta tipos generados del OpenAPI
└── index.ts                       # contrato público explícito
src/features/directory/            # MODIFICA
└── components/PriceListSelect.tsx # selector en el form de ficha (solo rol cliente)
```

**Contrato público (`pricing/index.ts`)**

```typescript
export { PriceListsContainer } from './components/PriceListsContainer';
export { usePriceLists } from './hooks/usePriceLists';
export { usePriceListItems } from './hooks/usePriceListItems';
export type { PriceListType, PriceListItemType } from './types/pricing.types';
```

**Custom hooks**

| Hook | Responsabilidad única | Endpoint / resource | Refine hook |
| :--- | :--- | :--- | :--- |
| `usePriceLists` | listar/crear/editar/baja de listas | `/pricing/price-lists` | `useList`/`useCreate`/`useUpdate`/`useDelete` |
| `usePriceListItems` | ítems de precio de una lista | `/pricing/price-lists/{id}/items` | `useList`/`useCreate`/`useUpdate`/`useDelete` |
| `useAssignPriceList` | asignar lista a la ficha | `PATCH /directory/fichas/{id}/assign-price-list` | `useCustomMutation` |

**Rutas / páginas (`src/pages/`)**

| Ruta | Tipo | Página | Contenedor | Perfil (canDo) |
| :--- | :--- | :--- | :--- | :--- |
| `/pricing/price-lists` | Protegida (`lazy`) | `PriceListsPage.tsx` | `PriceListsContainer` | `PRICING.read/create/update` |

- Rutas declaradas en `App.tsx` con `<Authenticated>` + `ForcePasswordChangeGuard` y `lazy(() => import(...))` (**no** array `resources` de Refine, per convención del proyecto); gating en componente con `usePermissions().canDo('PRICING', acción)`. Páginas *dumb*.

### Seguridad

- Acceso y asignación por perfil (F2). Sin datos sensibles adicionales.

### Qué NO se hace (YAGNI)

Sin snapshot de precio en la entrega ni marca de descarte (F16), sin múltiples listas por cliente, sin vigencias/temporalidad de precios, sin descuentos por volumen.

---

## 4) TASKS → tasks.md

> Orden obligatorio del `config.yaml`: Contrato (OpenAPI) → Migraciones Django → Backend (services) → Frontend → Seguridad → Pruebas. Cada tarea nombra el archivo/módulo exacto. Definition of done global: todos los gates del pipeline en verde localmente antes de declarar el change completo.

### A. Contrato y modelo (OpenAPI + datos)
- [ ] A.1 Crear la app `pricing` y los modelos `PriceList` (soft delete clase 2, tipo) y `PriceListItem` (FK lista, FK producto PROTECT, precio no negativo, `unique(lista, producto)`).
- [ ] A.2 Añadir `price_list` (FK nullable, PROTECT) al modelo `directory.Ficha`.
- [ ] A.3 Definir serializers de lista, de ítem de precio y de asignación de lista (con validación de rol cliente) en sus apps.
- [ ] A.4 Registrar el módulo `PRICING` y sus acciones en `apps/authz/catalog.py`.
- [ ] A.5 Anotar los endpoints con `drf-spectacular` y regenerar `schema.yml`.

### B. Migraciones
- [ ] B.1 `makemigrations pricing directory`; confirmar reversibilidad (upgrade + downgrade).
- [ ] B.2 `migrate` y verificar arranque limpio.

### C. Backend (services + vistas)
- [ ] C.1 Implementar en `apps/pricing/services.py` la unicidad (lista, producto), la validación de precio no negativo y la regla de baja de lista en uso (error de conflicto del contrato uniforme).
- [ ] C.2 Implementar la asignación de lista a ficha con la integridad de rol cliente (en el service de `directory`).
- [ ] C.3 Implementar los viewsets delgados de lista, ítem y asignación, protegidos por la permission class de F2 (módulo `PRICING`); registrar rutas.
- [ ] C.4 Verificar que todos los errores salen por el contrato uniforme.

### D. Frontend
- [ ] D.1 Regenerar tipos + Zod desde `schema.yml` (`npm run codegen`).
- [ ] D.2 Construir las pantallas de listas de precios y su grilla de productos/precios en `src/features/pricing/`.
- [ ] D.3 Integrar el selector de lista en el formulario de ficha (solo visible si la ficha tiene rol cliente).
- [ ] D.4 Gating por perfil; estados vacío/carga/error/éxito; tokens del theme; `FieldError` compartido; inputs numéricos ≥16px iOS.

### E. Seguridad (no negociable)
- [ ] E.1 Verificar que la asignación de lista y la edición/baja de precios respetan los permisos por perfil (F2); cubrir 401/403 en tests.
- [ ] E.2 Análisis estático de los módulos afectados: `ruff check` + `mypy --strict` (backend), `eslint` + `tsc` (frontend). Corregir todo.
- [ ] E.3 `bandit` sobre `apps/pricing`; verificar que no hay secretos ni colores hardcodeados en el diff.
- [ ] E.4 Contraste WCAG AA de las pantallas nuevas en modo claro y oscuro (grilla de precios, selector de lista).

### F. Pruebas (gate)
- [ ] F.1 Tests de backend en `apps/pricing/tests/` cubriendo todos los Scenarios (crear lista normal/descarte; nombre duplicado → 400; precio por producto; producto duplicado en lista → 409; precio negativo → 400; baja de lista sin/con clientes → 409; asignación a cliente; asignación a ficha sin rol cliente → 400; sin autorización → 401/403).
- [ ] F.2 Tests de frontend (Vitest + RTL) de la grilla de precios y del selector de lista en la ficha (incluye estados vacío/carga/error y feedback de error mapeado al campo).
- [ ] F.3 Ejecutar y dejar en verde: `ruff`, `mypy --strict`, `bandit`, `pip-audit`, `pytest` (cobertura ≥80%); `eslint`, `tsc`, `npm audit`, `vitest`, E2E (`playwright` incl. WebKit). Confirmar antes de declarar el change completo.
