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

---

## 1) PROPOSAL → proposal.md

### Intent

Acelerar el go-live permitiendo cargar masivamente los maestros desde CSV/Excel: **productos** y **fichas de Directorio**. La migración desde las hojas de cálculo actuales del cliente requiere cargar cientos de registros; hacerlo a mano por los formularios sería inviable. La importación valida cada fila con las **mismas reglas de dominio** que el alta individual, previsualiza el resultado antes de confirmar y es idempotente.

### Scope (qué cambia)

- **Importador de productos**: nombre, categoría (referencia existente), unidad de medida (referencia existente).
- **Importador de fichas**: campos base (identificación, nombre/razón social, roles, contacto).
- **Flujo dry-run → commit**: validación sin persistir, reporte fila por fila, y confirmación con commit atómico.
- Formatos CSV y Excel; el archivo se procesa, **no** se almacena (no es gestión documental).

### Decisiones de comportamiento (validadas)

- **Commit all-or-nothing:** el lote se persiste en una transacción atómica y solo si **ninguna** fila tiene error de validación. Una sola fila con error aborta todo el commit.
- **Deduplicación idempotente (skip):** las filas cuya clave natural ya existe (producto = nombre; ficha = número de identificación) se **omiten**, no se duplican ni se sobrescriben. Re-correr el mismo archivo no altera lo ya cargado.
- **Referencia, no creación:** las categorías y unidades se referencian por nombre desde el archivo de productos; **no** se crean ahí (se crean controladas en F5). Una referencia inexistente es error de fila.

> **Distinción importante:** *skip* (duplicado, omisión válida) **no** es *error*. Un lote con duplicados pero sin errores de validación **sí** se confirma, insertando las nuevas y omitiendo las existentes. El all-or-nothing aplica a errores de validación, no a omisiones.

### Impacto en el modelo de datos

- Ninguna tabla nueva de negocio. La importación opera sobre `directory.Ficha` (F4) y `products.Product` (F5) reusando sus reglas. El proceso es **stateless**: dry-run y commit reciben el archivo; el commit re-valida y persiste atómicamente (sin estado temporal que limpiar).
- Módulo `BULK_IMPORT` y sus acciones registrados en el catálogo de `access-control` (F2).

### Fuera de alcance

- **Importar listas de precios** → no.
- **Stock inicial y saldos CxC/CxP** → F20 (`opening-balances`).
- **Crear categorías o unidades desde el archivo** → se referencian existentes (F5).
- **Términos de crédito y lista de precios de la ficha** → se configuran después; no entran en la importación base.

### Verificación de invariantes

- La validación **no** se reimplementa: cada fila pasa por los serializers/services de dominio de F4/F5 (DRY). Reimplementarla crearía una fuente de verdad paralela que se desincronizaría.
- Errores por el contrato uniforme, a nivel de fila. Importación restringida por perfil (F2).

### Criterio de aborto (verificable)

Si los serializers de dominio de `Ficha` (F4) y `Product` (F5) no están disponibles para reusarse, abortar: la importación no debe validar con reglas propias.

---

## 2) SPECS → specs/bulk-import/spec.md

# Delta para la capability `bulk-import`

## ADDED Requirements

### Requirement: Previsualización sin persistir (dry-run)
El sistema MUST permitir cargar un archivo CSV o Excel y validarlo fila por fila SIN persistir, devolviendo un reporte por fila con su número, su estado (válida, a omitir por duplicado, o con error) y, si tiene error, el campo y el mensaje según el contrato uniforme.

#### Scenario: Dry-run de un archivo válido
- DADO un archivo con filas válidas
- CUANDO se ejecuta el dry-run
- ENTONCES el sistema devuelve el reporte marcando las filas como válidas
- Y no persiste ningún registro

#### Scenario: Dry-run con filas inválidas
- DADO un archivo con algunas filas inválidas
- CUANDO se ejecuta el dry-run
- ENTONCES el reporte señala cada fila inválida con su número, campo y mensaje
- Y no persiste ningún registro

### Requirement: Commit atómico all-or-nothing
El commit MUST persistir el lote en una única transacción y solo si ninguna fila tiene error de validación. Si al menos una fila tiene error, el sistema MUST NOT persistir ninguna fila.

#### Scenario: Commit de un lote sin errores
- DADO un archivo cuyas filas son todas válidas o a omitir
- CUANDO se confirma la importación
- ENTONCES el sistema persiste las filas nuevas en una transacción
- Y devuelve el conteo de insertadas y omitidas

#### Scenario: Commit con una fila inválida
- DADO un archivo con al menos una fila con error de validación
- CUANDO se intenta confirmar la importación
- ENTONCES el sistema no persiste ninguna fila
- Y devuelve el reporte de errores

### Requirement: Deduplicación idempotente
El importador MUST omitir las filas cuya clave natural ya existe (producto por nombre; ficha por número de identificación), sin duplicarlas ni sobrescribirlas. Re-ejecutar el mismo archivo MUST NOT alterar los registros existentes. Una omisión por duplicado NO es un error y no impide el commit.

#### Scenario: Re-ejecutar el mismo archivo
- DADO un archivo ya importado con éxito
- CUANDO se importa el mismo archivo de nuevo
- ENTONCES todas las filas se marcan como omitidas
- Y no se altera ningún registro existente

#### Scenario: Lote con nuevas y duplicadas
- DADO un archivo con filas nuevas y filas cuya clave ya existe
- CUANDO se confirma la importación
- ENTONCES el sistema inserta las nuevas y omite las existentes
- Y reporta ambos conteos

### Requirement: Validación delegada a las reglas de dominio
Cada fila MUST validarse con las mismas reglas de su entidad (identificación ecuatoriana, roles ≥1, unicidad, referencias existentes), sin reimplementarlas en el importador.

#### Scenario: Fila de ficha con identificación inválida
- DADO una fila de ficha con una cédula que no pasa el dígito verificador
- CUANDO se valida
- ENTONCES la fila se marca con error y el mismo mensaje que produce el alta individual

#### Scenario: Producto con categoría inexistente
- DADO una fila de producto que referencia una categoría que no existe
- CUANDO se valida
- ENTONCES la fila se marca con error indicando la categoría inexistente

### Requirement: Importadores de productos y de fichas
El sistema MUST proveer un importador de productos y uno de fichas. La ficha importa campos base (identificación, nombre, roles, contacto) y NO importa términos de crédito ni lista de precios.

#### Scenario: Importar fichas con roles múltiples
- DADO un archivo de fichas con una fila que declara roles cliente y proveedor
- CUANDO se confirma la importación
- ENTONCES la ficha se crea con ambos roles

---

## 3) DESIGN → design.md

### Estrategia general (stateless)

Tanto el dry-run como el commit reciben el archivo. El commit **re-valida** y persiste en una transacción atómica. No hay almacenamiento temporal del lote validado entre dry-run y commit, lo que evita gestionar tokens y limpieza de estado. La re-validación en el commit es barata y garantiza consistencia si el catálogo cambió entre ambos pasos.

### Parsing

- **CSV:** módulo `csv` de la librería estándar. **Excel:** `openpyxl` (ya en el stack). Un parser en `apps/bulk_import/parsers.py` produce filas como diccionarios normalizados, conservando el número de fila original para el reporte.
- **Límite de filas** por archivo: constante centralizada (p. ej. 5.000). Si se excede, error pidiendo dividir el archivo (proceso síncrono, sin Celery).

### Validación y dedup (reuso de dominio)

- Cada fila se valida instanciando el **serializer de dominio** correspondiente (`FichaWriteSerializer` de F4, `ProductWriteSerializer` de F5) y recolectando sus errores. **No** se reimplementan reglas.
- **Dedup:** antes de validar para inserción, se comprueba la clave natural (nombre de producto; número de identificación de ficha) contra los registros vivos; si existe, la fila se marca `skipped`.
- Estados de fila: `valid` / `skipped` / `error`.

### Commit

- `transaction.atomic`: se valida el lote completo; si hay cualquier `error`, se aborta sin persistir. Si no hay errores, se insertan las filas `valid` y se omiten las `skipped`.
- El commit se registra con `@audit` (quién importó, qué entidad, conteos), sin almacenar el archivo.

### Capa de API

- Endpoints por entidad y modo: `POST /bulk-import/products` y `/bulk-import/fichas`, con un flag `dry_run`. Respuesta: reporte por fila + conteos.
- **Plantillas descargables**: endpoint que entrega un CSV de ejemplo con las columnas esperadas de cada entidad, para que el usuario prepare el archivo.
- **Permisos por perfil:** módulo `BULK_IMPORT` registrado en `apps/authz/catalog.py`; importar restringido a Jefe/Supervisor.
- **Contrato OpenAPI:** anotar con `drf-spectacular` (incluida la forma del reporte por fila); regenerar `schema.yml`.

### Capa de frontend

- **Asistente de importación** en `src/features/bulk-import/`: seleccionar entidad → descargar plantilla → subir archivo → ver el reporte de dry-run en una tabla (fila, estado, errores por campo) → confirmar (habilitado solo si no hay filas en error) → ver conteos de insertadas/omitidas.
- Estados vacío/carga/error/éxito; el reporte de errores reutiliza el componente de errores por campo; tokens del theme.

### Seguridad

- Importación restringida por perfil (F2). El archivo se procesa en memoria y no se persiste. Validación de tipo y tamaño de archivo.

### Qué NO se hace (YAGNI)

Sin upsert, sin creación de categorías/unidades desde archivo, sin importación de precios/crédito/saldos, sin procesamiento asíncrono, sin almacenar el archivo subido.

---

## 4) TASKS → tasks.md

> Orden obligatorio del `config.yaml`: Contrato (OpenAPI) → Migraciones Django → Backend (services) → Frontend → Seguridad → Pruebas. Cada tarea nombra el archivo/módulo exacto. Definition of done global: todos los gates del pipeline en verde localmente antes de declarar el change completo.

### A. Contrato (OpenAPI)
- [ ] A.1 Crear la app `bulk_import` y el parser CSV/Excel en `apps/bulk_import/parsers.py` (filas normalizadas con número de fila; límite de filas como constante central).
- [ ] A.2 Definir la forma del reporte por fila (estado válido/omitido/error + errores por campo) y los serializers de respuesta.
- [ ] A.3 Registrar el módulo `BULK_IMPORT` y sus acciones en `apps/authz/catalog.py`.
- [ ] A.4 Anotar los endpoints con `drf-spectacular` (incluido el reporte) y regenerar `schema.yml`.

### B. Migraciones
- [ ] B.1 Verificar que no se requieren modelos nuevos (proceso stateless); si se añadiera algún registro de auditoría de importación, `makemigrations` reversible. (Por defecto: sin tablas nuevas.)

### C. Backend (services + vistas)
- [ ] C.1 Implementar en `apps/bulk_import/services.py` la validación por fila **delegando** en los serializers de dominio (`Ficha` F4, `Product` F5) y la deduplicación por clave natural (skip).
- [ ] C.2 Implementar el commit atómico all-or-nothing (`transaction.atomic`), con `@audit` del evento y conteos de insertadas/omitidas.
- [ ] C.3 Implementar los endpoints de productos y de fichas (flag `dry_run`) y el endpoint de plantilla descargable, protegidos por la permission class de F2 (módulo `BULK_IMPORT`, Jefe/Supervisor); registrar rutas.
- [ ] C.4 Verificar que los errores por fila siguen el contrato uniforme.

### D. Frontend
- [ ] D.1 Regenerar tipos + Zod desde `schema.yml` (`npm run codegen`).
- [ ] D.2 Construir el asistente de importación en `src/features/bulk-import/` (selección de entidad, descarga de plantilla, carga de archivo).
- [ ] D.3 Mostrar el reporte de dry-run en tabla (fila, estado, errores por campo); habilitar confirmar solo sin filas en error; mostrar conteos tras el commit.
- [ ] D.4 Estados vacío/carga/error/éxito; tokens del theme; reutilizar el componente de errores por campo.

### E. Seguridad
- [ ] E.1 Restringir la importación a perfiles autorizados (Jefe/Supervisor) server-side.
- [ ] E.2 Validar tipo y tamaño del archivo; procesar en memoria sin persistirlo.

### F. Pruebas (gate)
- [ ] F.1 Tests de backend en `apps/bulk_import/tests/` cubriendo todos los Scenarios (dry-run válido/inválido sin persistir; commit sin errores; commit con una fila inválida → nada persiste; re-ejecución idempotente; lote mixto nuevas/duplicadas; validación delegada con mensajes de dominio; categoría inexistente; fichas con roles múltiples). Probar CSV y Excel.
- [ ] F.2 Test de idempotencia explícito: importar dos veces el mismo archivo no cambia los conteos de la base.
- [ ] F.3 Tests de frontend (Vitest + RTL) del asistente y de la tabla de reporte.
- [ ] F.4 Ejecutar y dejar en verde: `ruff`, `mypy --strict`, `bandit`, `pip-audit`, `pytest` (cobertura ≥80%); `eslint`, `tsc`, `npm audit`, `vitest`. Confirmar antes de declarar el change completo.
