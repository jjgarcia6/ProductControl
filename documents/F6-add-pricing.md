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

### Fuera de alcance

- **Inmutabilidad del precio en la entrega** (snapshot al pasar a GENERADO) → F16 (`deliveries`). La regla 3.3 —no se cambia el precio sobre una entrega emitida; se descarta y se regenera— se implementa allí. En F6 la lista es editable libremente.
- **Efecto del tipo descarte** (precio reducido para producto próximo a vencer, marca de venta de descarte en la entrega) → F16. En F6 el tipo es solo un atributo de la lista.

### Verificación de invariantes

- Soft delete **clase 2** (catálogo). Precios decimales en USD.
- No toca Kardex, período, costeo ni documentos (es maestro).
- Errores por el contrato uniforme; permisos por perfil (F2).

### Criterio de aborto (verificable)

Si `directory.Ficha` (F4) o `products.Product` (F5) no están migrados, abortar: la lista necesita productos para fijar precios y la ficha para asignarse.

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
- ENTONCES el sistema responde con un error de conflicto del contrato uniforme

#### Scenario: Precio negativo
- CUANDO se intenta fijar un precio negativo
- ENTONCES el sistema responde 400 con `{campo: [mensajes]}` en el campo del precio

### Requirement: Baja de lista en uso
Una lista asignada a una o más fichas MUST NOT poder darse de baja sin reasignar antes a esas fichas.

#### Scenario: Baja de una lista sin clientes
- DADO una lista sin fichas asignadas
- CUANDO se da de baja
- ENTONCES el sistema la marca como eliminada y deja de listarla

#### Scenario: Baja de una lista asignada
- DADO una lista asignada a al menos una ficha
- CUANDO se intenta darla de baja
- ENTONCES el sistema responde con un error del contrato uniforme indicando que está en uso

### 2.2 → specs/directory/spec.md

# Delta para la capability `directory`

## ADDED Requirements

### Requirement: Asignación de lista de precios a un cliente
Una ficha con rol cliente MAY tener una lista de precios asignada (a lo sumo una). El sistema MUST NOT permitir asignar una lista a una ficha sin rol cliente. La asignación la realiza un perfil autorizado.

#### Scenario: Asignar una lista a un cliente
- DADO una ficha con rol cliente y una lista existente
- CUANDO un perfil autorizado le asigna la lista
- ENTONCES la ficha queda con esa lista asignada

#### Scenario: Asignar una lista a una ficha sin rol cliente
- DADO una ficha que no tiene rol cliente
- CUANDO se intenta asignarle una lista de precios
- ENTONCES el sistema responde 400 con `{campo: [mensajes]}` indicando que la ficha no es cliente

---

## 3) DESIGN → design.md

### Capa de datos

- **App `pricing`**:
  - `PriceList`: `name` (único parcial entre vivas), `type` (choices NORMAL/DESCARTE). Soft delete clase 2.
  - `PriceListItem`: `price_list` (FK), `product` (FK a `products.Product`, `on_delete=PROTECT`), `price` (Decimal `max_digits=12, decimal_places=2`, no negativo). `UniqueConstraint(price_list, product)`.
- **Modifica `directory.Ficha`**: `price_list` (FK a `pricing.PriceList`, `null=True, blank=True, on_delete=PROTECT`). PROTECT es la segunda defensa de la regla "no baja en uso"; la primera es la validación en service.
- Migración reversible en `pricing` y en `directory` (el campo nuevo).

### Capa de API

- **Contrato OpenAPI primero:** endpoints de listas, de ítems de precio y de asignación de lista a ficha, anotados con `drf-spectacular`; regenerar `schema.yml`.
- **Permisos por perfil:** registrar el módulo `PRICING` y sus acciones en `apps/authz/catalog.py`; proteger los endpoints con la permission class de F2.
- **Lógica en services:** la integridad asignación↔rol (la ficha debe ser cliente), la unicidad (lista, producto) y la regla de baja en uso viven en `apps/pricing/services.py` (y la asignación, en el service de directory que ya existe); viewsets delgados.

### Capa de frontend

- **Pantallas de listas** en `src/features/pricing/`: lista con su tipo, y la grilla de productos con precio (agregar/editar/quitar ítems).
- **Asignación de lista** integrada en el formulario de ficha (feature `directory`): selector de lista visible solo cuando la ficha tiene rol cliente.
- Precios como decimales (2 lugares); Zod generado del OpenAPI; gating por perfil; estados vacío/carga/error/éxito; tokens del theme; `FieldError` compartido; inputs numéricos ≥16px iOS.

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

### E. Seguridad
- [ ] E.1 Verificar que la asignación de lista y la edición de precios respetan los permisos por perfil (F2).

### F. Pruebas (gate)
- [ ] F.1 Tests de backend en `apps/pricing/tests/` cubriendo todos los Scenarios (crear lista normal/descarte; nombre duplicado; precio por producto; producto duplicado en lista → conflicto; precio negativo → 400; baja de lista sin/con clientes; asignación a cliente; asignación a ficha sin rol cliente → 400).
- [ ] F.2 Tests de frontend (Vitest + RTL) de la grilla de precios y del selector de lista en la ficha.
- [ ] F.3 Ejecutar y dejar en verde: `ruff`, `mypy --strict`, `bandit`, `pip-audit`, `pytest` (cobertura ≥80%); `eslint`, `tsc`, `npm audit`, `vitest`. Confirmar antes de declarar el change completo.
