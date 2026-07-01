# Diseño Técnico: add-products

> Identificadores técnicos en inglés; documentación en español. Los valores de los enums de dominio
> (tipo de ingreso) se persisten con códigos en español MAYÚSCULAS (GAVETA/PESO) y se muestran en
> español en la UI, consistente con la convención de F1/F4.

## 1. Capa de Datos (PostgreSQL + Django ORM)

### Tablas e Índices

| Tabla | Índice / Constraint | Tipo | Justificación |
| :--- | :--- | :--- | :--- |
| `products_categories` | `name` WHERE `deleted_at IS NULL` | `partial-unique` | Nombre único solo entre categorías vivas (soft delete clase 2: el nombre se reutiliza tras baja). |
| `products_categories` | `deleted_at` | `btree` | El manager filtra vivos por `deleted_at IS NULL` (provisto por `SoftDeleteModel`). |
| `products_products` | `name` WHERE `deleted_at IS NULL` | `partial-unique` | Nombre de producto único entre vivos. |
| `products_products` | `category_id` | `fk` | FK `on_delete=PROTECT`; navegar/filtrar productos por categoría. |
| `products_products` | `unit_of_measure_id` | `fk` | FK `on_delete=PROTECT`; navegar productos por unidad. |
| `products_units_of_measure` | `name` WHERE `deleted_at IS NULL` | `partial-unique` | Nombre de unidad único entre vivas. |

### Modelo Django

<!-- Política soft delete 3 clases: los tres son catálogos clase 2 -> heredan SoftDeleteModel
     (deleted_at + manager filtrado + all_objects). Todos heredan TimeStampedModel vía SoftDeleteModel. -->

```python
# Modelos Django — app `products`
# Mixins: SoftDeleteModel (clase 2; ya incluye TimeStampedModel, objects/all_objects).
# Códigos de enum en español MAYÚSCULAS, consistentes con accounts.Role / directory.FichaStatus.

import uuid
from decimal import Decimal
from django.db import models
from django.db.models import Q
from apps.common.models import SoftDeleteModel


class IntakeType(models.TextChoices):
    GAVETA = "GAVETA", "Gaveta"
    PESO = "PESO", "Peso"


class UnitOfMeasure(SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=64)
    symbol = models.CharField(max_length=16)
    # Número de libras equivalente a 1 unidad (base: libras = 1; kilogramos ≈ 2.204623).
    conversion_factor = models.DecimalField(max_digits=12, decimal_places=6)

    class Meta:
        db_table = "products_units_of_measure"
        constraints = [
            models.UniqueConstraint(
                fields=["name"], condition=Q(deleted_at__isnull=True),
                name="uniq_unit_name_alive",
            ),
        ]


class Category(SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128)
    shelf_life_days = models.PositiveIntegerField(default=7)
    intake_type = models.CharField(max_length=8, choices=IntakeType.choices)
    # Estructura del rango de merma proporcional (valores pendientes del cliente -> nullable).
    merma_min = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    merma_max = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    reference_qty = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("100"))

    class Meta:
        db_table = "products_categories"
        constraints = [
            models.UniqueConstraint(
                fields=["name"], condition=Q(deleted_at__isnull=True),
                name="uniq_category_name_alive",
            ),
        ]


class Product(SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    unit_of_measure = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name="products")

    class Meta:
        db_table = "products_products"
        constraints = [
            models.UniqueConstraint(
                fields=["name"], condition=Q(deleted_at__isnull=True),
                name="uniq_product_name_alive",
            ),
        ]
```

### Migración Django

```
# Archivo: apps/products/migrations/0001_initial.py
#   operations: CreateModel(UnitOfMeasure, Category, Product) + AddConstraint(parciales).
# Archivo: apps/products/migrations/0002_seed_base_units.py
#   operations: RunPython(seed_base_units, unseed_base_units)
#     - seed_base_units:   get_or_create libras (factor 1) y kilogramos (factor 2.204623). Idempotente.
#     - unseed_base_units: hard_delete SOLO de libras/kilogramos sembradas (reverse no-noop).
# Generar: uv run python manage.py makemigrations products
# Aplicar: uv run python manage.py migrate
# Reverse de prueba: uv run python manage.py migrate products zero
```

### Impacto en Invariantes del Sistema

- **Período cerrado:** No aplica — `products` no crea documentos con fecha.
- **Kardex FIFO / append-only:** No se afecta — F5 no genera movimientos de Kardex.
- **Doble costeo:** No se afecta — el costeo nominal/efectivo vive en F12/F13.
- **Cuadre de ruta:** No se afecta.
- **Snapshot inmutable de entrega:** No se afecta.
- **Nota de crédito vinculada:** No aplica.
- **Soft delete (3 clases):** Los tres son **catálogos clase 2** → `SoftDeleteModel` (`deleted_at` +
  manager). La baja con dependencias (categoría/unidad con productos vivos) se bloquea con 409. No hay
  reversión de efectos porque no hay efectos en Kardex/saldos.
- **Trazabilidad:** No se altera (ver proposal §3).

---

## 2. Capa de API y Contratos (Fuente de Verdad)

### Diccionario de Datos Vivo

| Entidad | Campo | Tipo (Py / TS) | Descripción (Uso y Propósito) | Restricciones |
| :--- | :--- | :--- | :--- | :--- |
| `Category` | `name` | `str / string` | Nombre visible de la categoría | Único entre vivas (409 en service), max 128 |
| `Category` | `shelf_life_days` | `int / number` | Días de caducidad desde el ingreso | ≥0, default 7 |
| `Category` | `intake_type` | `str / enum` | Cómo ingresa el producto al inventario | `GAVETA` \| `PESO` |
| `Category` | `merma_min` | `Decimal / string` | Mínimo del rango de merma proporcional (lb) | Nullable hasta pendiente #1 |
| `Category` | `merma_max` | `Decimal / string` | Máximo del rango de merma proporcional (lb) | Nullable; `>= merma_min` si ambos presentes |
| `Category` | `reference_qty` | `Decimal / string` | Cantidad de referencia del rango (lb) | Default 100, >0 |
| `Product` | `name` | `str / string` | Nombre visible del producto | Único entre vivos (409 en service), max 128 |
| `Product` | `category` | `UUID / string` | Categoría a la que pertenece | FK existente (400 si no existe) |
| `Product` | `unit_of_measure` | `UUID / string` | Unidad de medida del producto | FK existente (400 si no existe) |
| `UnitOfMeasure` | `name` | `str / string` | Nombre de la unidad (p. ej. Libras) | Único entre vivas (409), max 64 |
| `UnitOfMeasure` | `symbol` | `str / string` | Símbolo corto (p. ej. lb, kg) | max 16 |
| `UnitOfMeasure` | `conversion_factor` | `Decimal / string` | Libras equivalentes a 1 unidad (base = 1) | >0; no se aplica en F5 |

### Backend: Serializers DRF

```python
# apps/products/serializers.py — write/read separados; cada campo con help_text para el OpenAPI.
# La unicidad NO se valida aquí (la gobierna el service con Conflict 409). Aquí: formato, choices y FK.

class CategoryWriteSerializer(serializers.ModelSerializer):
    # merma_min/merma_max/reference_qty -> DecimalField(max_digits=12, decimal_places=3, help_text=...)
    class Meta:
        model = Category
        fields = ["name", "shelf_life_days", "intake_type", "merma_min", "merma_max", "reference_qty"]

class CategoryReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "shelf_life_days", "intake_type",
                  "merma_min", "merma_max", "reference_qty", "created_at", "updated_at"]

# ProductWriteSerializer: PrimaryKeyRelatedField(queryset=Category.objects/UnitOfMeasure.objects) -> 400 si no existe.
# ProductReadSerializer: anida nombre de categoría/unidad para el listado.
# UnitOfMeasureWrite/ReadSerializer: name, symbol, conversion_factor.
```

### Frontend: Tipos generados (Zod + TypeScript)

```typescript
// Generado desde el OpenAPI de DRF (npm run codegen) — NO editar a mano.
// categoryWriteSchema, productWriteSchema, unitOfMeasureWriteSchema (Zod) + sus *Type = z.infer<...>.
// Los formularios usan React Hook Form + zodResolver(<schema>). Pesos como string decimal.
```

### Endpoints de DRF

| Verbo | Ruta | Write Serializer | Read Serializer | Códigos HTTP | Perfil (módulo `products`) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/products/categories` | — | `CategoryRead` | `200/401/403` | `read` |
| `POST` | `/products/categories` | `CategoryWrite` | `CategoryRead` | `201/400/401/403/409` | `create` |
| `PATCH` | `/products/categories/{id}` | `CategoryWrite` | `CategoryRead` | `200/400/401/403/404/409` | `update` |
| `DELETE` | `/products/categories/{id}` | — | — | `204/401/403/404/409` | `update` |
| `GET/POST/PATCH/DELETE` | `/products/products[/{id}]` | `ProductWrite` | `ProductRead` | `200/201/204/400/401/403/404/409` | `read/create/update` |
| `GET/POST/PATCH/DELETE` | `/products/units[/{id}]` | `UnitOfMeasureWrite` | `UnitOfMeasureRead` | `200/201/204/400/401/403/404/409` | `read/create/update` |

<!-- No hay transiciones de estado (catálogo sin máquina de estado). El DELETE es soft delete; se
     autoriza con la acción `update` del módulo (el catálogo de F2 no expone `delete`, igual que directory). -->

### Servicio de Negocio

| Servicio | Método | Responsabilidad única | Transaccional |
| :--- | :--- | :--- | :--- |
| `services.py` | `create_category` / `create_product` / `create_unit` | Crear validando unicidad de nombre entre vivos (409) y FK existentes | Sí |
| `services.py` | `update_*` | Editar revalidando unicidad excluyendo el propio pk | Sí |
| `services.py` | `deactivate_category` | Baja lógica; 409 si tiene productos vivos | Sí |
| `services.py` | `deactivate_unit` | Baja lógica; 409 si tiene productos vivos | Sí |
| `services.py` | `deactivate_product` | Baja lógica del producto | Sí |

<!-- No hay cálculo financiero en F5 (no se crea calculations.py): la merma valorizada vive en F13.
     Todas las escrituras se decoran con @audit(action, entity): CREATE/UPDATE/SOFT_DELETE. -->

---

## 3. Capa de Presentación (UI — React + Refine)

### Árbol de Directorios de la Feature

```
src/features/products/
├── components/
│   ├── CategoryList.tsx          # Contenedor: orquesta useCategories + tabla
│   ├── CategoryForm.tsx          # Presentacional: caducidad, tipo de ingreso, rango de merma
│   ├── ProductList.tsx           # Contenedor: orquesta useProducts + tabla
│   ├── ProductForm.tsx           # Presentacional: selección de categoría y unidad
│   ├── UnitList.tsx              # Contenedor: unidades de medida
│   └── UnitForm.tsx              # Presentacional: nombre, símbolo, factor
├── hooks/
│   ├── useCategories.ts          # CRUD de categorías vía data hooks de Refine
│   ├── useProducts.ts            # CRUD de productos
│   └── useUnits.ts               # CRUD de unidades
├── types/
│   └── products.types.ts         # Re-exporta los tipos generados del OpenAPI
└── index.ts                      # Contrato público de la feature
```

<!-- Tokens del theme ya definidos en src/index.css (F0/align-shadcn): no se redefine nada aquí.
     Todo color desde utilidades de token; cero hex literales. Estados vacío/carga/error/éxito en cada lista. -->

### Contrato Público (`index.ts`)

```typescript
export { CategoryList } from './components/CategoryList';
export { ProductList } from './components/ProductList';
export { UnitList } from './components/UnitList';
export { useCategories } from './hooks/useCategories';
export { useProducts } from './hooks/useProducts';
export { useUnits } from './hooks/useUnits';
export type { CategoryType, ProductType, UnitOfMeasureType } from './types/products.types';
```

### Custom Hooks (`hooks/`)

| Hook | Responsabilidad única | Endpoint / resource | Refine hook |
| :--- | :--- | :--- | :--- |
| `useCategories` | Listar/crear/editar/dar de baja categorías | `/products/categories` / `categories` | `useList/useCreate/useUpdate/useDelete` |
| `useProducts` | Listar/crear/editar/dar de baja productos | `/products/products` / `products` | `useList/useCreate/useUpdate/useDelete` |
| `useUnits` | Listar/crear/editar/dar de baja unidades | `/products/units` / `units` | `useList/useCreate/useUpdate/useDelete` |

### Rutas y Páginas (`src/pages/`)

| Ruta | Tipo | Página (`src/pages/`) | Componente Contenedor | Acceso |
| :--- | :--- | :--- | :--- | :--- |
| `/products/categories` | Protegida | `products/CategoriesPage.tsx` | `CategoryList` | perfil con `products.read` |
| `/products/products` | Protegida | `products/ProductsPage.tsx` | `ProductList` | perfil con `products.read` |
| `/products/units` | Protegida | `products/UnitsPage.tsx` | `UnitList` | perfil con `products.read` |

<!-- Las páginas son dumb pages: importan y renderizan el contenedor. Las rutas se declaran en
     App.tsx como rutas protegidas (<Authenticated> + ForcePasswordChangeGuard) con lazy(() =>
     import(...)), consistente con F1–F4 (NO un array `resources` de Refine). El gating por perfil
     se resuelve en el contenedor con usePermissions().canDo('products', acción). -->

---

## 4. Configuración y DevSecOps

### Gestión de Secretos

- **Backend:** No introduce variables de entorno nuevas.
- **Frontend:** No introduce variables `VITE_*` nuevas.

### Seguridad Proactiva

- **Análisis Estático Backend:** `ruff`, `mypy --strict` y `bandit` limpios en `apps/products/`.
- **Análisis Estático Frontend:** `eslint` y `tsc` limpios en `src/features/products/`.
- **SCA (Dependencias):** Sin dependencias nuevas; `pip-audit` / `npm audit` se ejecutan igual como gate.

---

## 5. Cambios Estructurales

### Nuevas Dependencias

Ninguna. Todo se resuelve con Django/DRF y Refine ya presentes.

### Migraciones de Base de Datos

Tres tablas nuevas (sin alterar tablas existentes) + una data migration de unidades base. Toda
migración con reverse funcional; la data migration de unidades incluye `reverse_code` que elimina solo
las filas sembradas (idempotente). No hay migración de datos existentes.
