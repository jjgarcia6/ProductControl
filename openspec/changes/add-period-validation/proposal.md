# Propuesta: add-period-validation

> **Fase 9.** Capability `period` (inicia) · **Depende de:** F1 (auth) · **Desbloquea:** F11
> (kardex), F12 (intake) y todo documento con fecha (F13–F19, F21–F24) · **Requerimientos:** 2.2.
> **Fuente de verdad:** `openspec/config.yaml`. Ante conflicto, manda el `config.yaml`.
>
> **F9 es una fase de mecanismo, backend puro.** Sin endpoints, sin UI, sin permisos, sin cambios en
> el catálogo de `access-control` (respeta "depende solo de F1"). Entrega la entidad `Period`, el
> validador transversal y sus tests. El proceso de cierre/reversión y su superficie de usuario llegan
> en F25.

## 1. El Problema o Necesidad de Negocio

El invariante de negocio "período cerrado" (requisito 2.2) exige que, antes de crear o modificar
CUALQUIER documento, el sistema valide que su fecha contable no caiga en un período contable mensual
cerrado; si cae, se rechaza. Hoy no existe ni la entidad que representa el estado de un mes contable
ni la regla que lo hace cumplir. Cada fase posterior con documentos fechados (F11 kardex, F12 intake,
y F13–F24) depende de ese mecanismo: sin él, no hay forma de proteger los períodos ya conciliados de
escrituras retroactivas.

F9 entrega la **regla transversal de validación de período cerrado** como un mecanismo reutilizable:
(a) la entidad `Period` (mes contable con estado abierto/cerrado) y (b) el validador de dominio
`assert_date_operable` que las capas de service de F11+ invocarán. Es prioritario porque es
precondición dura de la primera fase que escribe documentos (F11).

F9 **no** ejecuta cierres: el proceso de cierre, el acta versionada y la reversión son de F25; aquí
solo se define la entidad y la regla.

## 2. Alcance Crítico

### In-Scope (Lo que se va a construir)

- **Entidad `Period`**: mes contable identificado por `(year, month)`, con `status` `OPEN`/`CLOSED`.
  Unicidad por `(year, month)`.
- **Validador transversal** en la capa de service: `assert_date_operable(doc_date)`. Semántica
  **implícita-abierta**: ausencia de fila = abierto; solo un `CLOSED` explícito bloquea. Rechazo vía
  el contrato de errores uniforme (`non_field_errors`), reutilizando el mensaje ya anclado en
  `apps/common`.
- **Contrato para fases consumidoras** (documentado en `design.md`): la fecha contable de los
  documentos es `DateField` interpretada en zona local **America/Guayaquil (UTC-5, sin DST)**;
  `(year, month)` se extraen de esa fecha.

Sin nuevos contratos de datos expuestos (no hay serializers ni tipos Zod): F9 es backend puro sin API.

### Out-of-Scope (Prohibiciones Estrictas)

- **Backend:** Toda persistencia MUST ser PostgreSQL vía Django ORM. Sin SQL raw.
- **Backend:** Las transacciones multi-tabla MUST usar `transaction.atomic()` con rollback total.
- **Backend:** `Period` es una entidad con máquina de estado (soft delete clase 1): NO hereda
  `SoftDeleteModel`; no se borra, su ciclo de vida es por transición de `status`.
- **Backend:** El cálculo financiero N/A en F9 (no hay FIFO/costeo/merma/saldos).
- **Seguridad:** Las credenciales MUST NOT almacenarse en el código; MUST gestionarse vía `.env` /
  GCP Secret Manager.
- **Calidad:** Las refactorizaciones ajenas al dominio de este cambio MUST NOT introducirse (YAGNI).

Diferido fuera de F9:

- **Proceso de cierre** (ejecución, condiciones de 15.3, acta versionada, reversión, nota de
  reversión) → F25.
- **Superficie de usuario y permisos** (endpoint de lectura de períodos, UI de cierre, módulo
  `period` en el catálogo de `access-control`) → F25.
- **Seed de períodos históricos** para saldos de apertura → F20/F25.
- **La invocación del validador desde documentos concretos** → cada fase consumidora (F11+); F9 solo
  provee el validador y lo prueba aislado.

## 3. Evaluación de Impacto

### Modelo de Datos (PostgreSQL)

- Nueva app `period`. Tabla `period` con `year`, `month`, `status` y marcas de tiempo
  (`TimeStampedModel`).
- `UniqueConstraint(fields=["year", "month"], name="period_unique_year_month")`.
- `CheckConstraint` de rango `1 <= month <= 12` (integridad del mes a nivel de DB).
- `Period` **NO** hereda `SoftDeleteModel` (soft delete clase 1: sin borrado; ciclo de vida por
  `status`).
- Migración Django reversible (`makemigrations period`). **Sin** data migration de seed: la semántica
  implícita-abierta hace innecesario sembrar meses; los `CLOSED` los crea F25.

### Lógica de Negocio y API

- **Sin endpoints DRF en F9.** Un endpoint de lectura arrastraría F2 (permisos) y rompería la
  dependencia "solo F1"; se difiere a F25.
- **Selector** `apps/period/selectors.py::get_period(year, month) -> Period | None`.
- **Service / validador transversal** `apps/period/services.py`:
  - `is_period_closed(doc_date) -> bool`.
  - `assert_date_operable(doc_date) -> None`: levanta `ValidationError(["La fecha pertenece a un
    período cerrado."])` (mapeada por el `EXCEPTION_HANDLER` de `apps.common` a
    `{"non_field_errors": [...]}`, HTTP 400) si la fecha cae en período cerrado.
- No se modifica lógica FIFO, costeo, merma, soft delete, CxC ni CxP (no existen aún).

### Flujo del Usuario (UI)

**N/A en F9.** No hay superficie de usuario: es un mecanismo de dominio consumido por servicios de
backend en fases posteriores. La pantalla y los permisos de cierre/reversión (solo el Jefe,
req. 2.5/15.1) son de F25.

### Cadena de Trazabilidad

No se altera la cadena de trazabilidad (Ingreso → Kardex → Entrega → Cobro / Ingreso → CxP → Pago).
`period` es una regla de control temporal: no genera movimientos de Kardex, documentos ni saldos.
**Protege** la cadena impidiendo escrituras sobre períodos cerrados.

## 4. Riesgos y Rollback

### Riesgo Principal

**Corrimiento de mes en el borde.** Si un documento usara `DateTimeField` en UTC, un registro del
último día del mes en horario nocturno local podría caer en el mes siguiente en UTC y evaluar el
período equivocado. Mitigación: el contrato para fases consumidoras fija `DateField` en zona local
(UTC-5, sin DST); Ecuador no tiene horario de verano, por lo que el riesgo residual es nulo mientras
se respete `DateField`.

Riesgo secundario: **enforcement omitido en una fase futura.** Como el validador se invoca desde cada
service de documento, una fase podría olvidar llamarlo. Mitigación: se documenta como precondición
explícita en `design.md` y cada fase consumidora incluirá su propio Scenario de "fecha en período
cerrado → rechazo"; no es responsabilidad de F9 forzarlo en tiempo de compilación.

### Criterio de Aborto

Abortar si (a) la migración inversa (`migrate period zero`) falla tras 2 intentos de corrección, o
(b) los tests de los Scenarios no quedan en verde, o (c) el validador no emite exactamente la forma
`non_field_errors` (HTTP 400) del contrato.

### Plan de Rollback

`migrate period zero` elimina la tabla. Sin data migration y sin dependencias de datos de negocio
(ningún documento la consume aún), el rollback es limpio y sin efectos colaterales.
