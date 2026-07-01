# Diseño Técnico: add-pricing

> Identificadores técnicos en inglés; documentación en español. Los valores del enum de dominio (tipo
> de lista) se persisten con códigos en español MAYÚSCULAS (`NORMAL`/`DESCARTE`), consistente con la
> convención de F4/F5. `pricing` es maestro: no toca Kardex, período, costeo ni documentos.

## 1. Capa de Datos (PostgreSQL + Django ORM)

### Tablas e Índices

| Tabla | Índice / Constraint | Tipo | Justificación |
| :--- | :--- | :--- | :--- |
| `price_lists` | `name` WHERE `deleted_at IS NULL` | `partial-unique` | Nombre único solo entre listas vivas (soft delete clase 2: el nombre se reutiliza tras baja). |
| `price_lists` | `deleted_at` | `btree` | El manager filtra vivos por `deleted_at IS NULL` (provisto por `SoftDeleteModel`). |
| `price_list_items` | `(price_list_id, product_id)` | `compound-unique` | A lo sumo un precio por (lista, producto). |
| `price_list_items` | `product_id` → `products_products` | `fk PROTECT` | No borrar un producto con precios asociados. |
| `directory_fichas` | `price_list_id` → `price_lists` | `fk PROTECT (nullable)` | Una lista por ficha; 2.ª defensa de "no baja de lista en uso". |

### Modelo Django

```python
# App: pricing — Tablas: price_lists, price_list_items
# Mixins: TimeStampedModel (siempre) + SoftDeleteModel (catálogo, clase 2)

class PriceListType(models.TextChoices):
    NORMAL = "NORMAL", "Normal"
    DESCARTE = "DESCARTE", "Descarte"

class PriceList(SoftDeleteModel, TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120, help_text="Nombre visible de la lista")
    type = models.CharField(max_length=8, choices=PriceListType.choices,
                            help_text="Naturaleza de la lista: NORMAL o DESCARTE")

    class Meta:
        db_table = "price_lists"
        constraints = [
            models.UniqueConstraint(fields=["name"], condition=Q(deleted_at__isnull=True),
                                    name="uq_price_list_name_alive"),
        ]

class PriceListItem(TimeStampedModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    price_list = models.ForeignKey(PriceList, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="+")
    price = models.DecimalField(max_digits=12, decimal_places=2,
                                validators=[MinValueValidator(Decimal("0"))],
                                help_text="Precio de venta en USD (>= 0)")

    class Meta:
        db_table = "price_list_items"
        constraints = [
            models.UniqueConstraint(fields=["price_list", "product"], name="uq_price_list_product"),
        ]

# App: directory — MODIFICA directory.Ficha (sin cambiar su clase 3 / estado INACTIVO)
#   price_list = models.ForeignKey("pricing.PriceList", null=True, blank=True,
#                                  on_delete=models.PROTECT, related_name="fichas")
```

### Migración Django

```
# pricing/migrations/0001_initial.py     -> CreateModel PriceList, PriceListItem + AddConstraint
# directory/migrations/000N_ficha_price_list.py -> AddField Ficha.price_list (nullable, PROTECT)
# Generar:  uv run python manage.py makemigrations pricing directory
# Aplicar:  uv run python manage.py migrate
# Reverse:  uv run python manage.py migrate directory <anterior>  &&  migrate pricing zero
# Sin RunPython: campos nuevos, sin backfill. Reverse estándar de Django.
```

### Impacto en Invariantes del Sistema

- **Período cerrado:** no aplica — `pricing` no crea documentos con fecha.
- **Kardex FIFO / append-only:** no se toca.
- **Doble costeo:** no se toca (el costeo es de F15; el precio de venta es independiente del costo).
- **Cuadre de ruta:** no aplica.
- **Snapshot inmutable de entrega:** no aplica en F6; la lista es la **fuente** del precio que F16 congelará.
- **Nota de crédito vinculada:** no aplica.
- **Soft delete (3 clases):** `PriceList`/`PriceListItem` = **clase 2** (catálogo, `deleted_at` + manager
  filtrado). `directory.Ficha` conserva su **clase 3** (estado INACTIVO); este change NO la altera.
- **Trazabilidad:** no se altera.

---

## 2. Capa de API y Contratos (Fuente de Verdad)

### Diccionario de Datos Vivo

| Entidad | Campo | Tipo (Py / TS) | Descripción | Restricciones |
| :--- | :--- | :--- | :--- | :--- |
| `PriceList` | `name` | `str / string` | Nombre visible de la lista | Único entre vivas, requerido |
| `PriceList` | `type` | `str / enum` | Naturaleza de la lista | `NORMAL` \| `DESCARTE` |
| `PriceListItem` | `price_list` | `UUID / string` | Lista a la que pertenece el precio | FK requerido |
| `PriceListItem` | `product` | `UUID / string` | Producto tarifado | FK `PROTECT`, único por lista |
| `PriceListItem` | `price` | `Decimal / number` | Precio de venta en USD | `>= 0`, 2 decimales |
| `Ficha` | `price_list` | `UUID / string \| null` | Lista asignada al cliente | Nullable, solo si rol cliente |

### Backend: Serializers DRF

```python
# PriceListWriteSerializer / PriceListReadSerializer
# PriceListItemWriteSerializer / PriceListItemReadSerializer
# AssignPriceListSerializer (write: price_list) -> FichaReadSerializer (salida, feature directory)
# Cada campo con help_text para el OpenAPI. price = DecimalField(max_digits=12, decimal_places=2).
# La unicidad NO se valida en el serializer (la gobierna el service): NO UniqueValidator /
# UniqueTogetherValidator (consistente con F4/F5).
```

### Frontend: Tipos generados (Zod + TypeScript)

```typescript
// Generado desde el OpenAPI de DRF (npm run codegen) — NO editar a mano.
// priceListSchema, priceListItemSchema (Zod) y sus z.infer<> re-exportados en
// src/features/pricing/types/pricing.types.ts. Formularios con RHF + zodResolver.
```

### Endpoints de DRF

| Verbo | Ruta | Write | Read | Códigos HTTP | Roles (perfil) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET/POST` | `/pricing/price-lists` | `PriceListWrite` | `PriceListRead` | 200/201/400/401/403/409 | Jefe, Supervisor |
| `GET/PATCH/DELETE` | `/pricing/price-lists/{id}` | `PriceListWrite` | `PriceListRead` | 200/204/400/401/403/409 | Jefe, Supervisor |
| `GET/POST` | `/pricing/price-lists/{id}/items` | `PriceListItemWrite` | `PriceListItemRead` | 200/201/400/401/403/409 | Jefe, Supervisor |
| `PATCH/DELETE` | `/pricing/price-list-items/{id}` | `PriceListItemWrite` | `PriceListItemRead` | 200/204/400/401/403 | Jefe, Supervisor |
| `PATCH` | `/directory/fichas/{id}/assign-price-list` | `AssignPriceList` | `FichaRead` | 200/400/401/403 | Jefe, Supervisor |

### Servicio de Negocio

| Servicio | Método | Responsabilidad única | Transaccional |
| :--- | :--- | :--- | :--- |
| `pricing/services.py` | `create_price_list()` / `update_price_list()` | Persistir lista; nombre único entre vivas (`Conflict` 409) | Sí |
| `pricing/services.py` | `set_price_list_item()` | Unicidad (lista, producto) `Conflict` 409 + precio ≥ 0 (400) | Sí |
| `pricing/services.py` | `soft_delete_price_list()` | Bloquear baja si tiene fichas asignadas (`Conflict` 409) | Sí |
| `directory/services.py` | `assign_price_list()` | Integridad asignación↔rol cliente (400) | Sí |

Todos los services aplican `@audit(action, entity)`. No hay cálculo financiero (sin ORM-free
`calculations.py`): el precio es un dato, no un cálculo derivado.

---

## 3. Capa de Presentación (UI — React + Refine)

### Árbol de Directorios de la Feature

```
src/features/pricing/
├── components/
│   ├── PriceListsContainer.tsx     # Contenedor: orquesta hooks + subcomponentes
│   ├── PriceListForm.tsx           # Presentacional: alta/edición de lista
│   └── PriceItemsGrid.tsx          # Presentacional: grilla producto/precio
├── hooks/
│   ├── usePriceLists.ts
│   └── usePriceListItems.ts
├── types/
│   └── pricing.types.ts            # Re-exporta tipos generados del OpenAPI
└── index.ts                        # Contrato público explícito
src/features/directory/             # MODIFICA
├── components/PriceListSelect.tsx  # Selector en el form de ficha (solo rol cliente)
└── hooks/useAssignPriceList.ts
```

### Contrato Público (`pricing/index.ts`)

```typescript
export { PriceListsContainer } from './components/PriceListsContainer';
export { usePriceLists } from './hooks/usePriceLists';
export { usePriceListItems } from './hooks/usePriceListItems';
export type { PriceListType, PriceListItemType } from './types/pricing.types';
```

### Custom Hooks (`hooks/`)

| Hook | Responsabilidad única | Endpoint / resource | Refine hook |
| :--- | :--- | :--- | :--- |
| `usePriceLists` | Listar/crear/editar/baja de listas | `/pricing/price-lists` | `useList`/`useCreate`/`useUpdate`/`useDelete` |
| `usePriceListItems` | Ítems de precio de una lista | `/pricing/price-lists/{id}/items` | `useList`/`useCreate`/`useUpdate`/`useDelete` |
| `useAssignPriceList` | Asignar lista a la ficha | `PATCH /directory/fichas/{id}/assign-price-list` | `useCustomMutation` |

### Resources y Páginas (`src/pages/`)

| Ruta | Tipo | Página (`src/pages/`) | Contenedor | Perfil (`canDo`) |
| :--- | :--- | :--- | :--- | :--- |
| `/pricing/price-lists` | Protegida (`lazy`) | `PriceListsPage.tsx` | `PriceListsContainer` | `PRICING.read/create/update` |

> **Convención del proyecto (manda sobre la plantilla genérica):** las rutas se declaran en `App.tsx`
> como rutas protegidas (`<Authenticated>` + `ForcePasswordChangeGuard`) con `lazy(() => import(...))`,
> **NO** con un array `resources` de Refine. El gating por perfil se resuelve en componente con
> `usePermissions().canDo('PRICING', acción)`. Las páginas son *dumb* (sin estado ni fetch directos).

---

## 4. Configuración y DevSecOps

### Gestión de Secretos

- **Backend:** este change NO introduce variables de entorno nuevas (`.env.example` sin cambios).
- **Frontend:** sin variables `VITE_*` nuevas.

### Seguridad Proactiva

- **Análisis Estático Backend:** `ruff`, `mypy --strict` y `bandit` limpios en `apps/pricing` y en los
  módulos tocados de `apps/directory`.
- **Análisis Estático Frontend:** `eslint` + `tsc` limpios en `features/pricing` y el selector de `directory`.
- **SCA:** sin dependencias nuevas; `pip-audit` y `npm audit` sin CVEs.

---

## 5. Cambios Estructurales

### Nuevas Dependencias

Ninguna. Se resuelve con Django/DRF y Refine existentes (KISS/YAGNI).

### Migraciones de Base de Datos

- `pricing/0001_initial` (CreateModel + constraints) y `directory/000N` (AddField `price_list` nullable
  PROTECT). Ambas con reverse estándar de Django; sin data migration. Probar el reverse antes de cerrar.
