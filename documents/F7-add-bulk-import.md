# Change: add-bulk-import — Fase 7

**Capability:** `bulk-import` (inicia) · **Depende de:** F4 (directory), F5 (products) · **Desbloquea:** — (habilitación de go-live)
**Fuente de verdad:** `openspec/config.yaml`. Ante conflicto, manda el `config.yaml`.
**Requerimientos:** **gap** de go-live (no en v1.1).

> **Cómo usar este archivo.** Consolida los cuatro artefactos del change. Cada sección de primer nivel mapea a un archivo dentro de `openspec/changes/add-bulk-import/`:
> - `## 1) PROPOSAL` → `proposal.md`
> - `## 2) SPECS` → `specs/bulk-import/spec.md` (delta)
> - `## 3) DESIGN` → `design.md`
> - `## 4) TASKS` → `tasks.md`
>
> Requirements en RFC 2119 (MUST/MUST NOT/SHALL); Scenarios en español (DADO/CUANDO/ENTONCES). Código e identificadores en inglés; documentación en español.
>
> **Convención de catálogo:** el módulo de autorización se registra como `bulk-import` (kebab-case en inglés), coherente con `access-control`/`directory`/`products` de `apps/authz/catalog.py`.

---

## 1) PROPOSAL → proposal.md

### 1. El Problema o Necesidad de Negocio

Acelerar el go-live permitiendo cargar masivamente los maestros desde CSV/Excel: **productos** y **fichas
de Directorio**. La migración desde las hojas de cálculo actuales del cliente requiere cargar cientos de
registros; hacerlo a mano por los formularios sería inviable y propenso a error. La importación valida
cada fila con las **mismas reglas de dominio** que el alta individual, previsualiza el resultado antes de
confirmar y es idempotente (re-cargar el mismo archivo no duplica).

### 2. Alcance Crítico

#### In-Scope (Lo que se va a construir)

- **Importador de productos**: nombre, categoría (referencia existente), unidad de medida (referencia existente).
- **Importador de fichas**: campos base (identificación, nombre/razón social, roles, contacto).
- **Flujo dry-run → commit**: validación sin persistir con reporte fila por fila, y confirmación con commit atómico.
- Formatos **CSV y Excel**; el archivo se procesa en memoria, **no** se almacena (no es gestión documental).
- **Asistente de importación** en el Frontend: seleccionar entidad → descargar plantilla → subir archivo →
  ver el reporte de dry-run → confirmar → ver conteos de insertadas/omitidas.
- Nuevos contratos de datos: serializers DRF de respuesta (reporte por fila) y sus tipos Zod **generados**
  del OpenAPI. No hay serializers de escritura propios: la validación se **delega** en los serializers de F4/F5.

**Decisiones de comportamiento (validadas):**

- **Commit all-or-nothing:** el lote se persiste en una transacción atómica y solo si **ninguna** fila tiene
  error de validación. Una sola fila con error aborta todo el commit.
- **Deduplicación idempotente (skip):** las filas cuya clave natural ya existe (producto = nombre; ficha =
  número de identificación) se **omiten**, no se duplican ni se sobrescriben.
- **Referencia, no creación:** categorías y unidades se referencian por nombre; **no** se crean aquí (se
  crean controladas en F5). Una referencia inexistente es error de fila.

> **Distinción importante:** *skip* (duplicado, omisión válida) **no** es *error*. Un lote con duplicados
> pero sin errores de validación **sí** se confirma, insertando las nuevas y omitiendo las existentes. El
> all-or-nothing aplica a errores de validación, no a omisiones.

#### Out-of-Scope (Prohibiciones Estrictas)

- **Backend:** Toda persistencia MUST ser PostgreSQL vía Django ORM. Sin SQL raw.
- **Backend:** El commit multi-fila MUST usar `transaction.atomic()` con rollback total.
- **Backend:** La validación NO se reimplementa; MUST delegar en los serializers/services de dominio de F4/F5 (DRY).
- **Frontend:** Los colores hardcodeados MUST NOT usarse; todo estilo MUST usar tokens del theme (modo claro y oscuro).
- **Seguridad:** Las credenciales MUST NOT almacenarse en el código; gestión vía `.env` / GCP Secret Manager.
- **Dominio — fuera de alcance:**
  - **Importar listas de precios** → no.
  - **Stock inicial y saldos CxC/CxP** → F20 (`opening-balances`).
  - **Crear categorías o unidades desde el archivo** → se referencian existentes (F5).
  - **Términos de crédito y lista de precios de la ficha** → se configuran después; no entran en la importación base.
  - **Upsert / sobrescritura**, procesamiento asíncrono (Celery) y almacenamiento del archivo subido → no (YAGNI).

### 3. Evaluación de Impacto

#### Modelo de Datos (PostgreSQL)

- **Ninguna tabla nueva de negocio.** La importación opera sobre `directory.Ficha` (F4) y `products.Product`
  (F5) reusando sus reglas. El proceso es **stateless**: dry-run y commit reciben el archivo; el commit
  re-valida y persiste atómicamente (sin estado temporal que limpiar).
- **Sin migración de esquema** (no se crean/alteran columnas, índices ni constraints). Por defecto no hay
  `makemigrations`; si se añadiera un registro de auditoría de importación, su migración MUST ser reversible.
- No se afectan índices únicos parciales de soft delete, ni el Kardex, ni ningún invariante financiero.

#### Lógica de Negocio y API

- Nueva app `bulk_import` con `parsers.py` (CSV/Excel → filas normalizadas) y `services.py` (validación por
  fila delegada + dedup + commit atómico con `@audit`).
- Endpoints por entidad y modo (flag `dry_run`), más un endpoint de **plantilla descargable**. Sin CRUD;
  son operaciones explícitas (validar / confirmar / descargar plantilla).
- No se toca la lógica FIFO, costeo, merma, ni la aplicación de cobros/pagos.

#### Flujo del Usuario (UI)

- Nueva ruta protegida con el **asistente de importación** (`src/features/bulk-import/`): entidad → plantilla
  → carga → tabla de reporte de dry-run (fila, estado, errores por campo) → confirmar (habilitado solo sin
  filas en error) → conteos de insertadas/omitidas.
- Roles afectados: la importación se restringe a **Jefe** y **Supervisor** (perfil con el módulo `bulk-import`).
  Responsable de ruta y Usuario no ven el asistente.
- Estados de pantalla vacío/carga/error/éxito REQUIRED; áreas táctiles ≥44px; inputs ≥16px en iOS.

#### Cadena de Trazabilidad

**No se altera la cadena de trazabilidad** (Ingreso → Kardex → Entrega → Cobro / Ingreso → CxP → Pago). La
importación solo crea maestros (productos y fichas); no genera movimientos de Kardex ni documentos financieros.

### 4. Riesgos y Rollback

#### Riesgo Principal

Que la validación del importador **diverja** de las reglas del alta individual (fuente de verdad paralela que
se desincroniza). Se mitiga instanciando los propios serializers de dominio de F4/F5 por fila, sin reimplementar
reglas. Riesgo secundario: un archivo grande procesado síncronamente choque con el timeout de Cloud Run
(mitigado con un límite de filas por archivo).

#### Criterio de Aborto

Si los serializers de dominio de `Ficha` (F4) y `Product` (F5) no están disponibles para reusarse, **abortar**:
la importación no debe validar con reglas propias. Verificable: importar sus módulos y construir los serializers
en un test; si falla, se aborta el change.

#### Plan de Rollback

El change es **stateless y sin migración de esquema**: revertir es retirar la app `bulk_import`, su entrada en
el catálogo (`bulk-import`) y la feature de Frontend; no hay data migration ni recálculo de saldos. Los registros
insertados por un commit previo permanecen (son altas válidas de maestros) y se gestionan por los flujos de F4/F5.

---

## 2) SPECS → specs/bulk-import/spec.md

# Delta para bulk-import

## ADDED Requirements

### Requirement: Previsualización sin persistir (dry-run)
El sistema MUST permitir cargar un archivo CSV o Excel y validarlo fila por fila SIN persistir, devolviendo
HTTP `200 OK` con un reporte por fila: su número, su estado (válida, a omitir por duplicado, o con error) y,
si tiene error, el campo y el mensaje según el contrato uniforme.

#### Scenario: Supervisor previsualiza un archivo válido
- DADO un usuario con el módulo `bulk-import` y un archivo con filas válidas
- CUANDO ejecuta el dry-run en `POST /bulk-import/products?dry_run=true`
- ENTONCES el Backend MUST responder `200 OK` con el reporte marcando las filas como válidas
- Y no persiste ningún registro

#### Scenario: Supervisor previsualiza un archivo con filas inválidas
- DADO un archivo con algunas filas inválidas
- CUANDO ejecuta el dry-run
- ENTONCES el Backend MUST responder `200 OK` con el reporte que señala cada fila inválida con su número, campo y mensaje
- Y no persiste ningún registro
- Y el Frontend MUST mostrar la tabla de reporte con los errores por campo usando tokens del theme

### Requirement: Commit atómico all-or-nothing
El commit MUST persistir el lote en una única transacción y solo si ninguna fila tiene error de validación.
Si al menos una fila tiene error, el sistema MUST NOT persistir ninguna fila y MUST responder `400 Bad Request`
con el reporte de errores por fila.

#### Scenario: Supervisor confirma un lote sin errores
- DADO un archivo cuyas filas son todas válidas o a omitir
- CUANDO confirma la importación en `POST /bulk-import/products` (sin `dry_run`)
- ENTONCES el Backend MUST procesar dentro de `transaction.atomic()` y persistir las filas nuevas
- Y MUST registrar la operación en `audit_log` con acción `CREATE` (entidad y conteos)
- Y MUST responder `201 Created` con el conteo de insertadas y omitidas
- Y el Frontend MUST mostrar una notificación de éxito con los conteos

#### Scenario: Supervisor confirma un lote con una fila inválida
- DADO un archivo con al menos una fila con error de validación
- CUANDO intenta confirmar la importación
- ENTONCES el Backend MUST NOT persistir ninguna fila
- Y MUST responder `400 Bad Request` con el reporte de errores por fila
- Y el Frontend MUST mostrar los errores sin exponer detalles internos

### Requirement: Deduplicación idempotente
El importador MUST omitir las filas cuya clave natural ya existe (producto por nombre; ficha por número de
identificación), sin duplicarlas ni sobrescribirlas. Re-ejecutar el mismo archivo MUST NOT alterar los
registros existentes. Una omisión por duplicado NO es un error y no impide el commit.

#### Scenario: Supervisor re-ejecuta el mismo archivo
- DADO un archivo ya importado con éxito
- CUANDO importa el mismo archivo de nuevo
- ENTONCES el Backend MUST responder `201 Created` con todas las filas marcadas como omitidas
- Y no altera ningún registro existente

#### Scenario: Supervisor confirma un lote con filas nuevas y duplicadas
- DADO un archivo con filas nuevas y filas cuya clave ya existe
- CUANDO confirma la importación
- ENTONCES el Backend MUST insertar las nuevas y omitir las existentes
- Y MUST responder `201 Created` reportando ambos conteos

### Requirement: Validación delegada a las reglas de dominio
Cada fila MUST validarse con las mismas reglas de su entidad (identificación ecuatoriana, roles ≥1, unicidad,
referencias existentes), sin reimplementarlas en el importador. El mensaje de error de fila MUST ser el mismo
que produce el alta individual, siguiendo el contrato de errores uniforme.

#### Scenario: Fila de ficha con identificación inválida
- DADO una fila de ficha con una cédula que no pasa el dígito verificador
- CUANDO se valida (dry-run o commit)
- ENTONCES la fila se marca con error y el mismo mensaje que produce el alta individual de F4

#### Scenario: Producto con categoría inexistente
- DADO una fila de producto que referencia una categoría que no existe
- CUANDO se valida
- ENTONCES la fila se marca con error indicando la categoría inexistente

### Requirement: Importadores de productos y de fichas
El sistema MUST proveer un importador de productos y uno de fichas. La ficha importa campos base (identificación,
nombre, roles, contacto) y NO importa términos de crédito ni lista de precios. El sistema MUST ofrecer una
plantilla descargable por entidad con las columnas esperadas.

#### Scenario: Supervisor importa fichas con roles múltiples
- DADO un archivo de fichas con una fila que declara roles cliente y proveedor
- CUANDO confirma la importación
- ENTONCES la ficha se crea con ambos roles

#### Scenario: Supervisor descarga la plantilla de una entidad
- DADO un usuario con el módulo `bulk-import`
- CUANDO solicita `GET /bulk-import/products/template`
- ENTONCES el Backend MUST responder `200 OK` con un CSV de ejemplo con las columnas esperadas

### Requirement: Validación del archivo (tipo, tamaño y límite de filas)
El sistema MUST rechazar archivos con formato no soportado, que excedan el tamaño máximo o el límite de filas
por archivo (constante centralizada), respondiendo `400 Bad Request` sin procesar el contenido.

#### Scenario: Usuario sube un archivo que excede el límite de filas
- DADO un archivo cuyo número de filas supera el límite configurado
- CUANDO se envía al endpoint de importación
- ENTONCES el Backend MUST responder `400 Bad Request` indicando que debe dividir el archivo
- Y el Frontend MUST mostrar el mensaje al usuario

#### Scenario: Usuario sube un archivo con formato no soportado
- DADO un archivo que no es CSV ni Excel
- CUANDO se envía al endpoint de importación
- ENTONCES el Backend MUST responder `400 Bad Request` indicando el formato inválido
- Y no persiste ningún registro

### Requirement: Restricción de acceso por perfil
La importación MUST estar restringida a perfiles con el módulo `bulk-import` (Jefe/Supervisor). Un usuario sin
ese permiso MUST recibir `403 Forbidden`.

#### Scenario: Usuario sin permiso intenta importar
- DADO un usuario cuyo perfil NO incluye el módulo `bulk-import`
- CUANDO accede a `POST /bulk-import/products`
- ENTONCES el Backend MUST responder `403 Forbidden` con `{detail}` genérico
- Y el Frontend MUST NOT mostrar el asistente de importación a ese perfil

#### Scenario: Usuario sin sesión intenta importar
- DADO un usuario sin sesión activa (sin token SimpleJWT válido)
- CUANDO accede a `POST /bulk-import/products`
- ENTONCES el Backend MUST responder `401 Unauthorized`
- Y el Frontend MUST redirigir al login (authProvider de Refine)

---

## 3) DESIGN → design.md

### 1. Capa de Datos (PostgreSQL + Django ORM)

**Sin tablas nuevas.** El proceso es stateless: opera sobre `directory.Ficha` (F4) y `products.Product` (F5)
reusando sus modelos, managers y constraints. No se crean/alteran columnas, índices ni foreign keys.

#### Tablas e Índices

| Tabla | Índice / Constraint | Tipo | Justificación |
| :--- | :--- | :--- | :--- |
| — | — | — | No se crea ni altera ninguna tabla; la dedup consulta los constraints/índices existentes de `Ficha` (número) y `Product` (nombre). |

#### Migración Django

Sin migración de esquema (no hay `makemigrations`). El commit persiste vía los managers existentes de F4/F5. Si
en el futuro se añadiera un registro de auditoría de importación, su migración MUST incluir `reverse_code`.

#### Impacto en Invariantes del Sistema

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

### 2. Capa de API y Contratos (Fuente de Verdad)

#### Diccionario de Datos Vivo

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

#### Backend: Serializers DRF

- `RowReportSerializer` y `ImportResultSerializer` — **salida** (contrato de lectura del reporte), cada campo con `help_text`.
- **No** hay `WriteSerializer` propio: cada fila se valida instanciando el serializer de dominio existente
  (`FichaWriteSerializer` de F4, `ProductWriteSerializer` de F5) y recolectando sus `.errors`. Esto es la
  aplicación directa de DRY / criterio de aborto.

#### Frontend: Tipos generados (Zod + TypeScript)

`rowReportSchema` / `importResultSchema` y sus `z.infer<>` se **generan** del OpenAPI (`npm run codegen`); MUST NOT
escribirse a mano. El asistente valida la respuesta contra el schema generado antes de renderizar la tabla.

#### Endpoints de DRF

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

#### Servicio de Negocio

| Servicio | Método | Responsabilidad única | Transaccional |
| :--- | :--- | :--- | :--- |
| `services.py` | `validate_rows(entity, rows)` | Valida cada fila con el serializer de dominio y marca `valid/skipped/error` | No |
| `services.py` | `commit_import(entity, rows)` | Persiste las filas `valid` all-or-nothing; omite `skipped`; audita | Sí (`transaction.atomic` + `@audit`) |
| `parsers.py` | `parse_file(file)` | Convierte CSV/Excel en filas normalizadas con su número; aplica límite de filas | No |

- Estados de fila: `valid` / `skipped` / `error`. **Dedup:** antes de validar para inserción, se comprueba la
  clave natural contra los registros vivos; si existe, la fila se marca `skipped`.
- Re-validación en el commit (barata) que garantiza consistencia si el catálogo cambió entre dry-run y commit;
  no hay estado temporal del lote entre ambos pasos.

---

### 3. Capa de Presentación (UI — React + Refine)

#### Árbol de Directorios de la Feature

```
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

#### Custom Hooks

| Hook | Responsabilidad única | Endpoint / resource | Refine hook |
| :--- | :--- | :--- | :--- |
| `useImportDryRun` | Previsualizar el archivo sin persistir | `POST /bulk-import/{entity}?dry_run=true` | `useCustomMutation` |
| `useImportCommit` | Confirmar la importación | `POST /bulk-import/{entity}` | `useCustomMutation` |

#### Resources y Páginas (`src/pages/`)

| Ruta / Resource | Tipo | Página (`src/pages/`) | Componente Contenedor | Roles permitidos |
| :--- | :--- | :--- | :--- | :--- |
| `/bulk-import` | Protegida (`lazy`) | `BulkImportPage.tsx` | `ImportWizard` | Jefe, Supervisor |

- El gating por perfil se resuelve en componente con `usePermissions().canDo("bulk-import", "create")`.
- Confirmar habilitado **solo** si no hay filas en error. Estados vacío/carga/error/éxito REQUIRED; cero hex
  literales (tokens del theme); reutiliza el componente de errores por campo; áreas táctiles ≥44px.

---

### 4. Configuración y DevSecOps

#### Gestión de Secretos

- **Backend:** ninguna variable nueva (el límite de filas es una constante centralizada, no un secreto).
- **Frontend:** ninguna variable `VITE_*` nueva.

#### Seguridad Proactiva

- Análisis estático limpio de `ruff`, `mypy --strict` y `bandit` en `apps/bulk_import`.
- Frontend: `eslint` y `tsc` limpios en `src/features/bulk-import`.
- SCA: `pip-audit` / `npm audit` (sin dependencias nuevas — `openpyxl` ya está en el stack; CSV es stdlib).
- Importación restringida por perfil; el archivo se procesa en memoria y **no** se persiste; validación de tipo y tamaño.

---

### 5. Cambios Estructurales

#### Nuevas Dependencias

| Paquete | Versión | Entorno | Justificación |
| :--- | :--- | :--- | :--- |
| — | — | — | Sin dependencias nuevas: `csv` (stdlib) y `openpyxl` (ya en el stack para XLSX de reportes). |

#### Migraciones de Base de Datos

Ninguna (proceso stateless, sin modelos nuevos). Qué NO se hace (YAGNI): upsert, creación de categorías/unidades
desde archivo, importación de precios/crédito/saldos, procesamiento asíncrono, almacenar el archivo subido.

---

## 4) TASKS → tasks.md

> Orden de fases REQUIRED (`config.yaml`): Contrato → Migraciones → Backend → Frontend → Seguridad → Pruebas.
> Cada tarea nombra el archivo/módulo exacto. Definition of done global: todos los gates del pipeline en verde
> localmente antes de declarar el change completo.

### Fase 0: Contrato y Sincronización Inicial
- [ ] **0.1** Backend — Crear la app `bulk_import` y definir la forma del reporte en
  `backend/apps/bulk_import/serializers.py`: `RowReportSerializer` e `ImportResultSerializer` (salida), con
  `help_text` en cada campo. No hay `WriteSerializer` propio.
- [ ] **0.2** Backend — Registrar el módulo `bulk-import` y sus acciones (`create`) en `backend/apps/authz/catalog.py`.
- [ ] **0.3** Backend — Anotar los endpoints con `drf-spectacular` (incluido el reporte) y regenerar `backend/schema.yml`.
- [ ] **0.4** Frontend — Regenerar tipos + Zod desde `schema.yml` (`npm run codegen`) en `frontend/src/features/bulk-import/types/`.
- [ ] **0.5** Global — Confirmar que no hay variables de entorno nuevas (`.env.example` sin cambios).

### Fase 1: Modelo de Datos y Migraciones
- [ ] **1.1** Verificar que no se requieren modelos nuevos (proceso stateless); sin `makemigrations`. Si se
  añadiera un registro de auditoría de importación, su migración MUST ser reversible (`reverse_code`).

### Fase 2: Lógica de Negocio y API (Backend)
- [ ] **2.1** Implementar el parser en `backend/apps/bulk_import/parsers.py`: CSV (stdlib) y Excel (`openpyxl`)
  → filas normalizadas conservando el número de fila; aplicar el límite de filas (constante central).
- [ ] **2.2** Implementar en `backend/apps/bulk_import/services.py` `validate_rows` (delega en los serializers
  de dominio `Ficha` F4 / `Product` F5 y marca `valid/skipped/error`; dedup por clave natural contra registros vivos).
- [ ] **2.3** Implementar `commit_import` en `services.py`: commit atómico all-or-nothing (`transaction.atomic`)
  con `@audit(action, entity)` y conteos de insertadas/omitidas.
- [ ] **2.4** Implementar los endpoints en `backend/apps/bulk_import/views.py` (productos y fichas con flag
  `dry_run`, y plantilla descargable), delgados, protegidos por `HasModulePermission` (módulo `bulk-import`);
  errores por fila con el contrato uniforme. Registrar rutas en `backend/apps/bulk_import/urls.py`.

### Fase 3: Integración de Datos (Frontend — Hooks)
- [ ] **3.1** Crear `useImportDryRun` y `useImportCommit` en `frontend/src/features/bulk-import/hooks/` con
  `useCustomMutation` de Refine (sin TanStack paralelo).
- [ ] **3.2** Validar en el hook que la respuesta cumple el schema Zod generado en Fase 0 antes de exponer los datos.

### Fase 4: Componentes y Páginas (Frontend — UI)
- [ ] **4.1** Crear `ImportWizard.tsx` (contenedor) en `frontend/src/features/bulk-import/components/`:
  selección de entidad, descarga de plantilla, carga de archivo; cubrir estados vacío/carga/error/éxito.
- [ ] **4.2** Crear `ImportReportTable.tsx` (presentacional): tabla fila/estado/errores por campo; reutilizar el
  componente de errores por campo; confirmar habilitado solo sin filas en error; tokens del theme (cero hex); ≥44px.
- [ ] **4.3** Actualizar el contrato público `frontend/src/features/bulk-import/index.ts` (exports explícitos).
- [ ] **4.4** Crear la página `BulkImportPage.tsx` en `frontend/src/pages/` (Dumb Page: solo renderiza `ImportWizard`).
- [ ] **4.5** Registrar la ruta protegida `/bulk-import` con `lazy(() => import(...))`; gating con
  `usePermissions().canDo("bulk-import", "create")`.

### Fase 5: Seguridad y DevSecOps
- [ ] **5.1** Restringir la importación server-side a perfiles con el módulo `bulk-import` (Jefe/Supervisor);
  `ruff` + `mypy --strict` limpios en `backend/apps/bulk_import/`.
- [ ] **5.2** `bandit -r backend/apps/bulk_import/`; validar tipo y tamaño del archivo; procesar en memoria sin persistirlo.
- [ ] **5.3** Frontend — `eslint frontend/src/features/bulk-import/` y `tsc --noEmit` limpios.
- [ ] **5.4** Verificar que no hay secretos en el código; contraste WCAG AA en modo claro y oscuro.

### Fase 6: Pruebas y Validación Final
- [ ] **6.1** Tests de backend en `backend/apps/bulk_import/tests/` cubriendo todos los Scenarios (dry-run
  válido/inválido → `200` sin persistir; commit sin errores → `201`; commit con fila inválida → `400`, nada
  persiste; re-ejecución idempotente; lote mixto nuevas/duplicadas; validación delegada con mensajes de dominio;
  categoría inexistente; fichas con roles múltiples; límite de filas/formato → `400`; `401`/`403`). Probar CSV y Excel.
- [ ] **6.2** Test de idempotencia explícito: importar dos veces el mismo archivo no cambia los conteos de la base.
- [ ] **6.3** Tests de frontend (Vitest + RTL) del asistente y de la tabla de reporte (éxito/error/estados/ARIA).
- [ ] **6.4** Integración — sin operaciones síncronas que choquen con el timeout de Cloud Run; sin errores/warnings de consola.
- [ ] **6.5** Definition of done — dejar en verde: `ruff`, `mypy --strict`, `bandit`, `pip-audit`, `pytest`
  (cobertura ≥80%); `eslint`, `tsc`, `npm audit`, `vitest`. Confirmar antes de declarar el change completo.
