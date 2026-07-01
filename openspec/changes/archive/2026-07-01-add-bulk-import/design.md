# Diseño Técnico: add-bulk-import

<!-- DIP: Las capas se diseñan de abajo hacia arriba: Datos → API → UI. -->

### Estrategia general (stateless)

Tanto el dry-run como el commit reciben el archivo. El commit **re-valida** y persiste en una transacción
atómica. No hay almacenamiento temporal del lote validado entre dry-run y commit, lo que evita gestionar tokens
y limpieza de estado. La re-validación en el commit es barata y garantiza consistencia si el catálogo cambió
entre ambos pasos.

## 1. Capa de Datos (PostgreSQL + Django ORM)

**Sin tablas nuevas.** El proceso es stateless: opera sobre `directory.Ficha` (F4) y `products.Product` (F5)
reusando sus modelos, managers y constraints. No se crean/alteran columnas, índices ni foreign keys.

### Tablas e Índices

| Tabla | Índice / Constraint | Tipo | Justificación |
| :--- | :--- | :--- | :--- |
| — | — | — | No se crea ni altera ninguna tabla; la dedup consulta los constraints/índices existentes de `Ficha` (número) y `Product` (nombre). |

### Migración Django

Sin migración de esquema (no hay `makemigrations`). El commit persiste vía los managers existentes de F4/F5. Si
en el futuro se añadiera un registro de auditoría de importación, su migración MUST incluir `reverse_code`.

### Impacto en Invariantes del Sistema

- **Período cerrado:** N/A — productos y fichas no son documentos con fecha.
- **Kardex FIFO / append-only:** N/A — no genera movimientos de Kardex.
- **Doble costeo:** N/A — no toca costo nominal ni efectivo.
- **Cuadre de ruta:** N/A.
- **Snapshot inmutable de entrega:** N/A.
- **Nota de crédito vinculada:** N/A.
- **Soft delete (3 clases):** se respeta el de la entidad destino — `Product` catálogo (clase 2, `deleted_at`);
  `Ficha` Directorio (clase 3, estado INACTIVO). La dedup consulta solo registros vivos.
- **Trazabilidad:** No se altera Ingreso → Kardex → Entrega → Cobro / Ingreso → CxP → Pago.

---

## 2. Capa de API y Contratos (Fuente de Verdad)

### Diccionario de Datos Vivo

No hay serializers de escritura propios (la validación se delega en F4/F5). El contrato nuevo es la **forma del
reporte por fila** (salida) y las **columnas de entrada** por entidad.

| Entidad | Campo | Tipo (Py / TS) | Descripción (Uso y Propósito) | Restricciones |
| :--- | :--- | :--- | :--- | :--- |
| `RowReport` | `row_number` | `int / number` | Número de fila original en el archivo, para localizar el error | ≥1 |
| `RowReport` | `status` | `str / enum` | Estado de la fila tras validar | `valid` \| `skipped` \| `error` |
| `RowReport` | `errors` | `dict / Record<string,string[]>` | Errores por campo (contrato uniforme); vacío si no hay error | Solo presente si `status = error` |
| `ImportResult` | `dry_run` | `bool / boolean` | Si la operación fue previsualización o commit | — |
| `ImportResult` | `inserted` | `int / number` | Conteo de filas insertadas (0 en dry-run) | ≥0 |
| `ImportResult` | `skipped` | `int / number` | Conteo de filas omitidas por duplicado | ≥0 |
| `ImportResult` | `rows` | `list / RowReport[]` | Reporte fila por fila | — |
| `ProductRow` (entrada) | `name`, `category`, `unit` | `str / string` | Columnas esperadas del CSV/Excel de productos | `category`/`unit` referencian existentes |
| `FichaRow` (entrada) | `identification`, `name`, `roles`, `contact…` | `str / string` | Columnas base de fichas | identificación válida; `roles` ≥1 |

### Backend: Serializers DRF

- `RowReportSerializer` y `ImportResultSerializer` — **salida** (contrato de lectura del reporte), cada campo con `help_text`.
- **No** hay `WriteSerializer` propio: cada fila se valida instanciando el serializer de dominio existente
  (`FichaWriteSerializer` de F4, `ProductWriteSerializer` de F5) y recolectando sus `.errors`. Esto es la
  aplicación directa de DRY / criterio de aborto.

### Frontend: Tipos generados (Zod + TypeScript)

`rowReportSchema` / `importResultSchema` y sus `z.infer<>` se **generan** del OpenAPI (`npm run codegen`); MUST NOT
escribirse a mano. El asistente valida la respuesta contra el schema generado antes de renderizar la tabla.

### Endpoints de DRF

| Verbo | Ruta | Write Serializer | Read Serializer | Códigos HTTP | Roles |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/bulk-import/products?dry_run={bool}` | (delega en `ProductWriteSerializer`) | `ImportResultSerializer` | `200/201/400/401/403` | Jefe, Supervisor |
| `POST` | `/bulk-import/fichas?dry_run={bool}` | (delega en `FichaWriteSerializer`) | `ImportResultSerializer` | `200/201/400/401/403` | Jefe, Supervisor |
| `GET` | `/bulk-import/products/template` | — | (archivo CSV) | `200/401/403` | Jefe, Supervisor |
| `GET` | `/bulk-import/fichas/template` | — | (archivo CSV) | `200/401/403` | Jefe, Supervisor |

- `dry_run=true` → `200 OK` con el reporte (aunque haya filas en error). `dry_run` ausente/false → commit:
  `201 Created` si no hay errores, `400 Bad Request` con el reporte si alguna fila tiene error.
- Permisos por perfil: módulo `bulk-import` registrado en `apps/authz/catalog.py`, resuelto por `HasModulePermission`.
- Contrato OpenAPI anotado con `drf-spectacular` (incluida la forma del reporte); regenerar `schema.yml`.

### Servicio de Negocio

| Servicio | Método | Responsabilidad única | Transaccional |
| :--- | :--- | :--- | :--- |
| `services.py` | `validate_rows(entity, rows)` | Valida cada fila con el serializer de dominio y marca `valid/skipped/error` | No |
| `services.py` | `commit_import(entity, rows)` | Persiste las filas `valid` all-or-nothing; omite `skipped`; audita por fila reusando los services de dominio F4/F5 | Sí (`transaction.atomic`; el `@audit` lo aportan `create_product`/`create_ficha` por fila) |
| `parsers.py` | `parse_file(file)` | Convierte CSV/Excel en filas normalizadas con su número; aplica límite de filas | No |

- Estados de fila: `valid` / `skipped` / `error`. **Dedup:** antes de validar para inserción, se comprueba la
  clave natural contra los registros vivos; si existe, la fila se marca `skipped`.
- Re-validación en el commit (barata) que garantiza consistencia si el catálogo cambió entre dry-run y commit;
  no hay estado temporal del lote entre ambos pasos.

---

## 3. Capa de Presentación (UI — React + Refine)

### Árbol de Directorios de la Feature

```text
src/features/bulk-import/
├── components/
│   ├── ImportWizard.tsx          # Contenedor: orquesta hooks y pasos (entidad→plantilla→carga→reporte→commit)
│   └── ImportReportTable.tsx     # Presentacional: tabla fila/estado/errores por campo
├── hooks/
│   ├── useImportDryRun.ts        # Dry-run vía useCustomMutation
│   └── useImportCommit.ts        # Commit vía useCustomMutation
├── types/
│   └── import.types.ts           # Re-exporta tipos generados del OpenAPI (ImportResult, RowReport)
└── index.ts                      # Contrato público de la feature
```

### Contrato Público (`index.ts`)

```typescript
export { ImportWizard } from './components/ImportWizard';
export { useImportDryRun } from './hooks/useImportDryRun';
export { useImportCommit } from './hooks/useImportCommit';
export type { ImportResultType, RowReportType } from './types/import.types';
```

### Custom Hooks

| Hook | Responsabilidad única | Endpoint / resource | Refine hook |
| :--- | :--- | :--- | :--- |
| `useImportDryRun` | Previsualizar el archivo sin persistir | `POST /bulk-import/{entity}?dry_run=true` | `useCustomMutation` |
| `useImportCommit` | Confirmar la importación | `POST /bulk-import/{entity}` | `useCustomMutation` |

### Resources y Páginas (`src/pages/`)

| Ruta / Resource | Tipo | Página (`src/pages/`) | Componente Contenedor | Roles permitidos |
| :--- | :--- | :--- | :--- | :--- |
| `/bulk-import` | Protegida (`lazy`) | `BulkImportPage.tsx` | `ImportWizard` | Jefe, Supervisor |

- El gating por perfil se resuelve en componente con `usePermissions().canDo("bulk-import", "create")`.
- Confirmar habilitado **solo** si no hay filas en error. Estados vacío/carga/error/éxito REQUIRED; cero hex
  literales (tokens del theme); reutiliza el componente de errores por campo; áreas táctiles ≥44px.

---

## 4. Configuración y DevSecOps

### Gestión de Secretos

- **Backend:** ninguna variable nueva (el límite de filas es una constante centralizada, no un secreto).
- **Frontend:** ninguna variable `VITE_*` nueva.

### Seguridad Proactiva

- Análisis estático limpio de `ruff`, `mypy --strict` y `bandit` en `apps/bulk_import`.
- Frontend: `eslint` y `tsc` limpios en `src/features/bulk-import`.
- SCA: `pip-audit` / `npm audit` (sin dependencias nuevas — `openpyxl` ya está en el stack; CSV es stdlib).
- Importación restringida por perfil; el archivo se procesa en memoria y **no** se persiste; validación de tipo y tamaño.

---

## 5. Cambios Estructurales

### Nuevas Dependencias

| Paquete | Versión | Entorno | Justificación |
| :--- | :--- | :--- | :--- |
| — | — | — | Sin dependencias nuevas: `csv` (stdlib) y `openpyxl` (ya en el stack para XLSX de reportes). |

### Migraciones de Base de Datos

Ninguna (proceso stateless, sin modelos nuevos). Qué NO se hace (YAGNI): upsert, creación de categorías/unidades
desde archivo, importación de precios/crédito/saldos, procesamiento asíncrono, almacenar el archivo subido.
