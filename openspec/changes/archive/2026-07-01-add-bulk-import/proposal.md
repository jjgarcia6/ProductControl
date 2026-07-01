# Propuesta: add-bulk-import

> **Fase 7.** Capability `bulk-import` (inicia) · **Depende de:** F4 (directory), F5 (products) ·
> **Desbloquea:** — (habilitación de go-live) · **Requerimientos:** gap de go-live (no en v1.1).
> **Fuente de verdad:** `openspec/config.yaml`. Ante conflicto, manda el `config.yaml`.
> **Convención de catálogo:** el módulo de autorización se registra como `bulk-import` (kebab-case en
> inglés), coherente con `access-control`/`directory`/`products` de `apps/authz/catalog.py`.

## 1. El Problema o Necesidad de Negocio

Acelerar el go-live permitiendo cargar masivamente los maestros desde CSV/Excel: **productos** y **fichas
de Directorio**. La migración desde las hojas de cálculo actuales del cliente requiere cargar cientos de
registros; hacerlo a mano por los formularios sería inviable y propenso a error. La importación valida
cada fila con las **mismas reglas de dominio** que el alta individual, previsualiza el resultado antes de
confirmar y es idempotente (re-cargar el mismo archivo no duplica).

## 2. Alcance Crítico

### In-Scope (Lo que se va a construir)

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

### Out-of-Scope (Prohibiciones Estrictas)

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

## 3. Evaluación de Impacto

### Modelo de Datos (PostgreSQL)

- **Ninguna tabla nueva de negocio.** La importación opera sobre `directory.Ficha` (F4) y `products.Product`
  (F5) reusando sus reglas. El proceso es **stateless**: dry-run y commit reciben el archivo; el commit
  re-valida y persiste atómicamente (sin estado temporal que limpiar).
- **Sin migración de esquema** (no se crean/alteran columnas, índices ni constraints). Por defecto no hay
  `makemigrations`; si se añadiera un registro de auditoría de importación, su migración MUST ser reversible.
- No se afectan índices únicos parciales de soft delete, ni el Kardex, ni ningún invariante financiero.

### Lógica de Negocio y API

- Nueva app `bulk_import` con `parsers.py` (CSV/Excel → filas normalizadas) y `services.py` (validación por
  fila delegada + dedup + commit atómico con `@audit`).
- Endpoints por entidad y modo (flag `dry_run`), más un endpoint de **plantilla descargable**. Sin CRUD;
  son operaciones explícitas (validar / confirmar / descargar plantilla).
- No se toca la lógica FIFO, costeo, merma, ni la aplicación de cobros/pagos.

### Flujo del Usuario (UI)

- Nueva ruta protegida con el **asistente de importación** (`src/features/bulk-import/`): entidad → plantilla
  → carga → tabla de reporte de dry-run (fila, estado, errores por campo) → confirmar (habilitado solo sin
  filas en error) → conteos de insertadas/omitidas.
- Roles afectados: la importación se restringe a **Jefe** y **Supervisor** (perfil con el módulo `bulk-import`).
  Responsable de ruta y Usuario no ven el asistente.
- Estados de pantalla vacío/carga/error/éxito REQUIRED; áreas táctiles ≥44px; inputs ≥16px en iOS.

### Cadena de Trazabilidad

**No se altera la cadena de trazabilidad** (Ingreso → Kardex → Entrega → Cobro / Ingreso → CxP → Pago). La
importación solo crea maestros (productos y fichas); no genera movimientos de Kardex ni documentos financieros.

## 4. Riesgos y Rollback

### Riesgo Principal

Que la validación del importador **diverja** de las reglas del alta individual (fuente de verdad paralela que
se desincroniza). Se mitiga instanciando los propios serializers de dominio de F4/F5 por fila, sin reimplementar
reglas. Riesgo secundario: un archivo grande procesado síncronamente choque con el timeout de Cloud Run
(mitigado con un límite de filas por archivo).

### Criterio de Aborto

Si los serializers de dominio de `Ficha` (F4) y `Product` (F5) no están disponibles para reusarse, **abortar**:
la importación no debe validar con reglas propias. Verificable: importar sus módulos y construir los serializers
en un test; si falla, se aborta el change.

### Plan de Rollback

El change es **stateless y sin migración de esquema**: revertir es retirar la app `bulk_import`, su entrada en
el catálogo (`bulk-import`) y la feature de Frontend; no hay data migration ni recálculo de saldos. Los registros
insertados por un commit previo permanecen (son altas válidas de maestros) y se gestionan por los flujos de F4/F5.
