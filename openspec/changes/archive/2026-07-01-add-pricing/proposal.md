# Propuesta: add-pricing

> **Fase 6.** Capability `pricing` (inicia) · modifica `directory` · **Depende de:** F4 (directory),
> F5 (products) · **Desbloquea:** F16 (deliveries) · **Requerimientos:** 4.2.
> **Fuente de verdad:** `openspec/config.yaml`. Ante conflicto, manda el `config.yaml`.

## 1. El Problema o Necesidad de Negocio

El sistema tiene productos (F5) y fichas de terceros (F4), pero todavía no puede fijar **a qué precio
se vende cada producto** ni **qué precio aplica a cada cliente**. Sin eso, las entregas (F16) no
tienen de dónde tomar el precio: el FK `ficha → lista de precios` quedó deliberadamente diferido en
F4 a la espera de esta fase.

`pricing` entrega las **listas de precios** y su **asignación a clientes**. Cada lista (normal o de
descarte) fija el precio de los productos que se venden bajo ella; una ficha de cliente tiene una
lista asignada que determinará el precio de sus entregas. Es precondición dura de F16 (deliveries):
sin lista asignada, una entrega no puede valorizarse. Es prioritario porque ninguna venta puede
registrarse sin un precio de referencia.

## 2. Alcance Crítico

### In-Scope (Lo que se va a construir)

- **Lista de precios** (`PriceList`): nombre único entre vivas y tipo (`NORMAL`/`DESCARTE`). Soft
  delete clase 2. CRUD acotado gobernado por el service (unicidad de nombre y baja bloqueada por uso).
- **Precio por producto en lista** (`PriceListItem`): un precio (Decimal, USD, ≥ 0) por (lista,
  producto). Agregar/editar/quitar ítems.
- **Asignación de lista a ficha de cliente:** completa `directory.Ficha` con el FK `price_list` (una
  lista por ficha), realizada por un perfil autorizado (Supervisor/Jefe), solo sobre fichas con rol
  cliente.
- **Contratos nuevos:** serializers Write/Read para `PriceList`, `PriceListItem` y la asignación;
  tipos + Zod generados del OpenAPI. Módulo `PRICING` registrado en el catálogo de `access-control`.

### Out-of-Scope (Prohibiciones Estrictas)

- **Backend:** persistencia SOLO PostgreSQL vía Django ORM; sin SQL raw. Operaciones multi-tabla en
  `transaction.atomic()` con rollback total.
- **Backend:** `PriceList`/`PriceListItem` heredan el soft delete de catálogo (clase 2). `directory.Ficha`
  conserva su clase 3 (estado INACTIVO); este change NO la convierte.
- **Frontend:** cero colores hardcodeados; todo estilo por tokens del theme (claro y oscuro).
- **Seguridad:** sin credenciales en el repo; secretos por `.env`/GCP Secret Manager.
- **Dominio (diferido a F16):** **inmutabilidad del precio en la entrega** (snapshot al pasar a
  GENERADO — regla 3.3: no se cambia el precio de una entrega emitida, se descarta y regenera) y el
  **efecto del tipo descarte** (precio reducido, marca de venta de descarte en rentabilidad). En F6 la
  lista es editable libremente y el tipo es solo un atributo.
- **Calidad:** sin refactorizaciones ajenas al dominio (YAGNI); sin múltiples listas por cliente, sin
  vigencias/temporalidad de precios, sin descuentos por volumen.

## 3. Evaluación de Impacto

### Modelo de Datos (PostgreSQL)

- **Nueva app `pricing`** con dos tablas:
  - `price_lists`: `name` (unique parcial entre vivas, `deleted_at IS NULL`), `type` (`NORMAL`/`DESCARTE`).
    Hereda `SoftDeleteModel` (clase 2) + `TimeStampedModel`.
  - `price_list_items`: FK `price_list`, FK `product` (`products.Product`, `on_delete=PROTECT`),
    `price` (`DecimalField(max_digits=12, decimal_places=2)`, ≥ 0). `UniqueConstraint(price_list, product)`.
- **Modifica `directory.Ficha`:** nuevo `price_list` (FK a `pricing.PriceList`, `null=True, blank=True,
  on_delete=PROTECT`). `PROTECT` es la 2.ª defensa de "no baja de lista en uso"; la 1.ª es la
  validación en service.
- **Migraciones reversibles:** `pricing/0001` (CreateModel) y `directory/000N` (AddField aditivo,
  nullable, sin backfill). No se afectan índices/constraints existentes de F4/F5.
- **Invariantes:** no se impacta Kardex, FIFO, snapshot de entrega ni trazabilidad (`pricing` es maestro).

### Lógica de Negocio y API

- **Endpoints DRF nuevos** (derivados del uso, no CRUD ciego): listas, ítems de precio y la acción
  `assign-price-list` sobre la ficha. Viewsets delgados; toda regla en `services.py`.
- **Servicios:** `apps/pricing/services.py` gobierna la unicidad de nombre (409), la unicidad
  (lista, producto) (409), el precio ≥ 0 (400) y la baja bloqueada por uso (409). `apps/directory/services.py`
  gana la asignación con integridad asignación↔rol cliente (400). Uniqueness gobernada en service
  (`Conflict`), no por `UniqueValidator`/`UniqueTogetherValidator` (consistente con F4/F5).
- No se toca FIFO, costeo, merma, CxC ni CxP.

### Flujo del Usuario (UI)

- **Roles afectados:** **Jefe** y **Supervisor** (perfiles con el módulo `PRICING`) gestionan listas y
  precios y realizan la asignación de lista a la ficha. **Responsable de ruta** y **Usuario** no ven ni
  operan estas pantallas (gating por perfil con `usePermissions().canDo`).
- **Rutas protegidas nuevas** en `pricing` (grilla de listas + productos/precios). El **selector de
  lista** se integra en el formulario de ficha existente (feature `directory`), visible solo si la
  ficha tiene rol cliente. Estados vacío/carga/error/éxito; tokens del theme; inputs numéricos ≥16px iOS.

### Cadena de Trazabilidad

No se altera la cadena de trazabilidad (Ingreso → Kardex → Entrega → Cobro / Ingreso → CxP → Pago).
`pricing` es maestro: la lista solo **provee** el precio que la entrega (F16) consumirá y congelará en
su snapshot. En F6 no se generan movimientos de Kardex, documentos ni saldos.

## 4. Riesgos y Rollback

### Riesgo Principal

La migración `AddField` de `price_list` (FK `PROTECT`) sobre `directory.Ficha` es aditiva y nullable,
pero debe ser **reversible** sobre una tabla `directory` que ya contiene datos de F4. Un reverse que no
restaure el estado previo bloquearía el rollback y dejaría la FK huérfana.

### Criterio de Aborto

Abortar si (a) `directory.Ficha` (F4) o `products.Product` (F5) no están migrados —la lista necesita
productos para fijar precios y la ficha para asignarse—; o (b) la migración inversa (`migrate directory
<anterior>` y `migrate pricing zero`) falla tras 2 intentos de corrección; o (c) los tests de los
Scenarios no quedan en verde.

### Plan de Rollback

Ambas migraciones (`pricing` y el `AddField` en `directory`) tienen reverse estándar de Django; no se
requiere data migration (campos nuevos, sin backfill). Revertir en orden inverso: primero `directory`
al estado anterior, luego `migrate pricing zero`.
