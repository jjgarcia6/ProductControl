# Change: add-period-validation — Fase 9

**Capability:** `period` (inicia) · **Depende de:** F1 (auth) · **Desbloquea:** F11 (kardex), F12 (ingresos) y todo documento con fecha (F13–F19, F21–F24)
**Fuente de verdad:** `openspec/config.yaml`. Ante conflicto, manda el `config.yaml`.
**Requerimientos:** 2.2.

> **Cómo usar este archivo.** Consolida los cuatro artefactos del change. Cada sección de primer nivel mapea a un archivo dentro de `openspec/changes/add-period-validation/`:
> - `## 1) PROPOSAL` → `proposal.md`
> - `## 2) SPECS` → un delta: `specs/period/spec.md`
> - `## 3) DESIGN` → `design.md`
> - `## 4) TASKS` → `tasks.md`
>
> La `## 5) MODIFICACIONES PUNTUALES` NO es un artículo del change dir: es la edición exacta sobre `config/settings/base.py`. Se aplica como *diff* dirigido, no como regeneración.
>
> **F9 es una fase de mecanismo, backend puro.** Sin endpoints, sin UI, sin permisos, sin cambios en el catálogo de `access-control` (respeta "depende solo de F1"). Entrega la entidad `period`, el validador transversal y sus tests. El proceso de cierre/reversión y su superficie de usuario llegan en F25.
>
> Requirements en RFC 2119 (MUST/MUST NOT/SHALL); Scenarios en español (DADO/CUANDO/ENTONCES). Código e identificadores en inglés; documentación en español.

---

## 1) PROPOSAL → proposal.md

### Intent

Entregar la **regla transversal de validación de período cerrado** (requisito 2.2) como un mecanismo reutilizable que toda fase con documentos fechados consumirá: antes de crear o modificar un documento, su fecha contable no debe caer en un período contable mensual cerrado. F9 aporta (a) la entidad `Period` (mes contable con estado abierto/cerrado) y (b) el validador de dominio que las capas de service de F11+ invocarán. F9 **no** ejecuta cierres: el proceso de cierre, el acta versionada y la reversión son de F25; aquí solo se define la entidad y la regla.

### Scope (qué cambia)

- **Entidad `Period`**: mes contable identificado por `(year, month)`, con `status` `OPEN`/`CLOSED`. Unicidad por `(year, month)`.
- **Validador transversal** en la capa de service: `assert_date_operable(doc_date)`. Semántica **implícita-abierta**: ausencia de fila = abierto; solo un `CLOSED` explícito bloquea. Rechazo vía el contrato de errores uniforme (`non_field_errors`), reutilizando el mensaje ya anclado en `apps/common`.
- **Contrato para fases consumidoras** (documentado en `design.md`): la fecha contable de los documentos es `DateField` interpretada en zona local **America/Guayaquil (UTC-5, sin DST)**; `(year, month)` se extraen de esa fecha.

### Decisiones de modelado (validadas)

- **Semántica implícita-abierta:** solo se persisten y bloquean períodos `CLOSED`. Es la lectura literal de 2.2 ("no pertenezca a un período cerrado") y la única compatible con que F25 sea el único creador/ejecutor de cierres. Evita la rigidez de un registro explícito-abierto (que exigiría abrir cada mes antes de operar, sin respaldo en requisitos).
- **Alcance de la regla en escritura:** *ninguna fecha involucrada en la escritura cae en período cerrado.* En create, la fecha persistida debe estar abierta; en update, la fecha actual del documento **y** (si cambia) la nueva fecha deben estar abiertas. Esto cubre el efecto 15.5 ("los documentos del período quedan bloqueados para modificación") sin depender de F25.
- **Enforcement en la capa de service, autoritativo:** consistente con el codebase (viewsets/serializers delgados; lógica en services). Cada service de documento (F11+) llama al validador. Un mixin de serializer como azúcar de feedback rápido queda descartado en F9 (no como única defensa; diferible si alguna fase lo justifica).
- **`Period` se rige por la clase 1 de la política de soft delete:** máquina de estado (`OPEN`/`CLOSED`), **sin borrado**; la transición la ejecuta F25 (cierre y reversión). No hereda `SoftDeleteModel`.
- **Backend puro (depende solo de F1):** sin endpoints ni permisos. Un endpoint de lectura arrastraría F2 y rompería la dependencia; se difiere a F25, donde la UI de cierre sí lo necesita.

### Impacto en el modelo de datos (antes que UI — DIP)

- Nueva app `period`. Tabla `period` con `year`, `month`, `status` y marcas de tiempo; `unique(year, month)`. Migración reversible.
- **Sin data migration de seed:** la semántica implícita-abierta hace innecesario sembrar meses. Los períodos `CLOSED` los crea F25; el seed de períodos históricos para go-live corresponde a F20/F25.

### Flujo del usuario (UI)

**N/A en F9.** No hay superficie de usuario: es un mecanismo de dominio consumido por servicios de backend en fases posteriores. La pantalla y los permisos de cierre/reversión son de F25.

### Cadena de trazabilidad

No se altera la cadena de trazabilidad (Ingreso → Kardex → Entrega → Cobro / Ingreso → CxP → Pago). `period` es una regla de control temporal: no genera movimientos de Kardex, documentos ni saldos. **Protege** la cadena impidiendo escrituras sobre períodos cerrados.

### Fuera de alcance

- **Proceso de cierre** (ejecución, condiciones de 15.3, acta versionada, reversión, nota de reversión) → F25.
- **Superficie de usuario y permisos** (endpoint de lectura de períodos, UI de cierre, módulo `period` en el catálogo de `access-control`) → F25.
- **Seed de períodos históricos** para saldos de apertura → F20/F25.
- **La invocación del validador desde documentos concretos** → cada fase consumidora (F11+); F9 solo provee el validador y lo prueba aislado.
- **Prohibiciones estrictas (heredadas de la plantilla):** persistencia SOLO PostgreSQL vía Django ORM (sin SQL raw); operaciones multi-tabla en `transaction.atomic()` con rollback total; credenciales SOLO por `.env`/GCP Secret Manager; sin refactorizaciones ajenas al dominio (YAGNI).

### Verificación de invariantes

- **Período cerrado:** F9 le da hogar concreto (capability `period`). El invariante ya existe en `config.yaml`; **no requiere edición**.
- **Soft delete (3 clases):** `Period` = clase 1 (máquina de estado, sin borrado). Coherente con la política.
- **Kardex append-only / FIFO / cuadre / snapshot / nota de crédito / doble costeo:** no se tocan.
- **Contrato de errores uniforme:** el validador levanta `ValidationError(["La fecha pertenece a un período cerrado."])`, que el `EXCEPTION_HANDLER` de `apps.common` ya mapea a `{"non_field_errors": [...]}` (forma verificada en `apps/common/tests/test_exceptions.py`). F9 reutiliza mensaje y forma; no introduce un contrato nuevo.

### Riesgos y rollback

- **Riesgo 1 — corrimiento de mes en el borde.** Si un documento usara `DateTimeField` en UTC, un registro del último día del mes en horario nocturno local podría caer en el mes siguiente en UTC y evaluar el período equivocado. Mitigación: el contrato para fases consumidoras fija `DateField` en zona local (UTC-5, sin DST); Ecuador no tiene horario de verano, por lo que el riesgo residual es nulo mientras se respete `DateField`.
- **Riesgo 2 — enforcement omitido en una fase futura.** Como el validador se invoca desde cada service de documento, una fase podría olvidar llamarlo. Mitigación: se documenta como precondición explícita en `design.md` y cada fase consumidora incluirá su propio Scenario de "fecha en período cerrado → rechazo"; no es responsabilidad de F9 forzarlo en tiempo de compilación.
- **Criterio de aborto (verificable):** abortar si (a) la migración inversa (`migrate period zero`) falla tras 2 intentos de corrección, o (b) los tests de los Scenarios no quedan en verde, o (c) el validador no emite exactamente la forma `non_field_errors` del contrato.
- **Plan de rollback:** `migrate period zero` elimina la tabla. Sin data migration y sin dependencias de datos de negocio (ningún documento la consume aún), el rollback es limpio y sin efectos colaterales.

---

## 2) SPECS

### 2.1 → specs/period/spec.md

# Delta para la capability `period`

> Los Scenarios describen la **regla de dominio** (comportamiento del validador `assert_date_operable`), no endpoints HTTP. En F9 los períodos `CLOSED` se establecen creando la fila directamente (no hay proceso de cierre hasta F25).

## ADDED Requirements

### Requirement: Período contable mensual con estado
El sistema MUST representar cada mes contable como un período único por `(año, mes)` con estado `OPEN` o `CLOSED`. El sistema MUST NOT permitir dos períodos con el mismo `(año, mes)`. Los períodos MUST NOT eliminarse; su ciclo de vida se gobierna por transición de estado.

#### Scenario: Unicidad del período
- DADO un período existente para un `(año, mes)`
- CUANDO se intenta crear otro período con el mismo `(año, mes)`
- ENTONCES el sistema rechaza la creación por violación de unicidad

### Requirement: Validación de período cerrado antes de escribir
Antes de crear o modificar un documento, el sistema MUST validar que ninguna fecha involucrada en la escritura pertenezca a un período cerrado. Si la fecha pertenece a un período cerrado, el sistema MUST rechazar la operación con el contrato de errores uniforme (`non_field_errors`).

#### Scenario: Fecha en mes sin período registrado (implícita-abierta)
- DADO que no existe un período para el `(año, mes)` de la fecha del documento
- CUANDO se valida esa fecha
- ENTONCES el sistema la considera operable y permite continuar

#### Scenario: Fecha en período abierto
- DADO un período `OPEN` para el `(año, mes)` de la fecha del documento
- CUANDO se valida esa fecha
- ENTONCES el sistema la considera operable y permite continuar

#### Scenario: Crear documento con fecha en período cerrado
- DADO un período `CLOSED` para el `(año, mes)` de la fecha del documento
- CUANDO se valida esa fecha al crear
- ENTONCES el sistema responde **400** con `{"non_field_errors": ["La fecha pertenece a un período cerrado."]}`

#### Scenario: Modificar un documento cuya fecha está en período cerrado
- DADO un documento cuya fecha actual pertenece a un período `CLOSED`
- CUANDO se intenta modificarlo
- ENTONCES el sistema rechaza la modificación con el mismo error de período cerrado

#### Scenario: Mover la fecha de un documento hacia un período cerrado
- DADO un documento cuya fecha actual pertenece a un período `OPEN`
- Y un período `CLOSED` en otro `(año, mes)`
- CUANDO se intenta cambiar la fecha del documento hacia ese período cerrado
- ENTONCES el sistema rechaza la modificación con el error de período cerrado

---

## 3) DESIGN → design.md

> **Orden de trabajo adaptado.** El orden canónico del `config.yaml` (Contrato OpenAPI → Migraciones → Backend → Frontend → Seguridad → Pruebas) se adapta a una fase sin API ni UI: **Datos → Migraciones → Backend (validador) → Seguridad → Pruebas.** No hay capa de contrato OpenAPI ni capa de frontend en F9.

### Capa de datos

- **App `period`**:
  - `Period(TimeStampedModel)`:
    - `year` (`PositiveIntegerField`)
    - `month` (`PositiveSmallIntegerField`, validación 1–12)
    - `status` (`CharField` con choices `OPEN`/`CLOSED`, default `OPEN`)
    - `UniqueConstraint(fields=["year", "month"], name="period_unique_year_month")`
    - Opcional (validación de rango en DB): `CheckConstraint(check=Q(month__gte=1) & Q(month__lte=12), name="period_month_range")`.
  - **NO** hereda `SoftDeleteModel` (clase 1: sin borrado, ciclo de vida por `status`).
- Migración reversible. **Sin** data migration de seed (semántica implícita-abierta).

**Tablas e índices / constraints**

| Tabla | Índice / Constraint | Tipo | Justificación |
| :--- | :--- | :--- | :--- |
| `period` | `(year, month)` | unique | un solo período por mes contable; cubre el lookup del validador |
| `period` | `1 <= month <= 12` | check constraint | integridad del mes a nivel de DB |

**Impacto en invariantes del sistema**

- **Período cerrado:** implementado aquí. `status=CLOSED` es la condición de bloqueo.
- **Soft delete (3 clases):** clase 1 (sin borrado; transición por `status`, ejecutada por F25).
- **Kardex / FIFO / cuadre / snapshot / nota de crédito / doble costeo:** no se tocan.
- **Trazabilidad:** no se altera.

### Capa de aplicación (backend — sin API)

- **Selector** `apps/period/selectors.py::get_period(year, month) -> Period | None`: lookup por `(year, month)`; retorna `None` si no existe (mes implícitamente abierto).
- **Service / validador transversal** `apps/period/services.py`:
  - `is_period_closed(doc_date) -> bool`: función delgada que deriva `(year, month)` de `doc_date` y consulta `get_period`; `True` solo si existe y `status=CLOSED`.
  - `assert_date_operable(doc_date) -> None`: si `is_period_closed(doc_date)` es `True`, levanta `rest_framework.exceptions.ValidationError(["La fecha pertenece a un período cerrado."])`. En caso contrario, no hace nada.
- **Contrato de consumo para F11+** (documental, no código en F9): cada service de documento invoca `assert_date_operable` con la fecha contable del documento en create y update; en update evalúa la fecha actual y, si cambia, también la nueva.

**Servicios de negocio**

| Servicio | Método | Responsabilidad única | Transaccional |
| :--- | :--- | :--- | :--- |
| `period/selectors.py` | `get_period()` | resolver el período de un `(año, mes)` o `None` | No |
| `period/services.py` | `is_period_closed()` | decidir si una fecha cae en período cerrado | No |
| `period/services.py` | `assert_date_operable()` | levantar el error de contrato si la fecha no es operable | No |

### Contrato para fases consumidoras (precondición documentada)

- Los documentos con fecha DEBEN modelar su fecha contable como `DateField` (no `DateTimeField`).
- La fecha se interpreta en zona local **America/Guayaquil (UTC-5, sin DST)**; `(year, month)` se extraen de esa fecha.
- Cada service de documento DEBE invocar `assert_date_operable` en create y update, e incluir su propio Scenario de "fecha en período cerrado → 400 `non_field_errors`".

### Seguridad

- Sin superficie externa: nada que exponer ni permisos que definir en F9. El validador no maneja datos sensibles. La restricción de quién puede cerrar/revertir un período (solo el Jefe, req. 2.5/15.1) es de F25.

### Qué NO se hace (YAGNI)

Sin endpoints, sin UI, sin permisos, sin registro en el catálogo de `access-control`, sin proceso de cierre, sin acta, sin reversión, sin seed de períodos, sin mixin de serializer. F9 entrega entidad + validador + tests.

---

## 4) TASKS → tasks.md

> Definition of done global: todos los gates de backend en verde localmente antes de declarar el change completo. No hay gates de frontend (no hay UI).

### A. Datos (modelo)
- [ ] A.1 Crear la app `period` y el modelo `Period` (`year`, `month` 1–12, `status` `OPEN`/`CLOSED` default `OPEN`; `UniqueConstraint(year, month)`; `CheckConstraint` de rango de mes; hereda solo `TimeStampedModel`, sin soft delete).
- [ ] A.2 Añadir la app a `LOCAL_APPS` en `config/settings/base.py`.

### B. Migraciones
- [ ] B.1 `makemigrations period`; confirmar reversibilidad (upgrade + downgrade) del modelo y los constraints.
- [ ] B.2 `migrate` y verificar arranque limpio. **Sin** data migration de seed.

### C. Backend (validador)
- [ ] C.1 Implementar `get_period(year, month)` en `apps/period/selectors.py`.
- [ ] C.2 Implementar `is_period_closed(doc_date)` y `assert_date_operable(doc_date)` en `apps/period/services.py`, levantando el error de contrato (`ValidationError(["La fecha pertenece a un período cerrado."])`).
- [ ] C.3 Documentar en el `design.md`/docstrings la precondición para fases consumidoras (F11+): `DateField` en zona local UTC-5; invocar `assert_date_operable` en create/update (fecha actual y nueva).

### D. Frontend
- [ ] D.1 N/A — F9 no tiene superficie de usuario.

### E. Seguridad (no negociable)
- [ ] E.1 Análisis estático de los módulos afectados: `ruff check` + `mypy --strict`. Corregir todo.
- [ ] E.2 `bandit` sobre `apps/period`; confirmar que no hay SQL raw, secretos ni credenciales en el diff.

### F. Pruebas (gate)
- [ ] F.1 Tests en `apps/period/tests/` cubriendo los Scenarios: unicidad `(year, month)`; mes sin período → operable; período `OPEN` → operable; período `CLOSED` al crear → 400 `non_field_errors` con el mensaje exacto; documento con fecha en período cerrado → modificación bloqueada; mover fecha hacia período cerrado → bloqueada. Los `CLOSED` se establecen creando la fila directamente.
- [ ] F.2 Test de reversibilidad de la migración (`migrate period zero` limpio).
- [ ] F.3 Ejecutar y dejar en verde: `ruff`, `mypy --strict`, `bandit`, `pip-audit`, `pytest` (cobertura ≥80%). Confirmar antes de declarar el change completo.

---

## 5) MODIFICACIONES PUNTUALES (archivos existentes del repo)

> Aplicar como *diff* dirigido. NO regenerar el archivo completo.

### 5.1 `config/settings/base.py`

En `LOCAL_APPS`, tras `"apps.system_settings"` (F8):
```python
    "apps.period",
```

> **Sin cambios** en `config/urls.py` (no hay endpoints), en `apps/authz/catalog.py` (no hay permisos; se respeta "depende solo de F1") ni en `openspec/config.yaml` (el invariante "período cerrado" ya existe).
