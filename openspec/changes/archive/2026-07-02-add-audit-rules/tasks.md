# Tareas: add-audit-rules

<!-- Orden de fases REQUIRED: Contrato → Migraciones → Backend → Frontend → Seguridad → Pruebas. -->
<!-- Cada tarea nombra el archivo/módulo exacto. Definition of done: gates de backend en verde localmente. -->

## Fase 0: Contrato y Sincronización Inicial

- [x] **0.1** **N/A** — F10 no expone superficie HTTP: no hay serializers DRF nuevos.
- [x] **0.2** **N/A** — Sin cambios en el OpenAPI (`backend/schema.yml`); no se regenera.
- [x] **0.3** **N/A** — Sin `npm run codegen`; no hay tipos/Zod nuevos.
- [x] **0.4** **N/A** — Sin variables de entorno nuevas en `.env.example`.

## Fase 1: Modelo de Datos y Migraciones

- [x] **1.1** **N/A** — `AuditLog` (`apps/common/models.py`) permanece intacto; no se crea ni altera modelo.
- [x] **1.2** **N/A** — Sin `makemigrations`.
- [x] **1.3** **N/A** — Sin `migrate`.
- [x] **1.4** **N/A** — Sin migración que reversar.

## Fase 2: Lógica de Negocio y API (Backend)

- [x] **2.1** Crear `backend/apps/common/audit_rules.py` (registro de reglas, sin ORM): `AuditAction`
  (`TextChoices`/`StrEnum` con `value` == literal vigente + nuevo `CORRECTION`), la convención de `entity`
  (PascalCase del modelo), el registro `AUDITED_FIELDS: dict[str, frozenset[str]]` (inicialmente vacío) y
  el helper `is_audited(entity, field) -> bool`.
- [x] **2.2** Añadir `to_audit_str(value) -> str` en `backend/apps/common/audit.py`: `Decimal`→notación
  simple (`format(value, "f")`), `date`/`datetime`→ISO, `Model`/FK→`str(pk)`, `None`→`""`, resto→`str()`.
- [x] **2.3** Añadir `record_field_changes(*, user, entity, object_id, before, after, action=CORRECTION)`
  en `backend/apps/common/audit.py`: una fila `AuditLog` por campo auditado con cambio real; NO abre
  transacción propia (contrato: corre dentro de la del service llamador); devuelve la lista de registros creados.
- [x] **2.4** Corregir el docstring de `@audit` en `backend/apps/common/audit.py` para referir
  `AuditAction` y `record_field_changes`; **conservar su comportamiento grueso** (sin diff campo-nivel).
- [x] **2.5** Retrofit de constantes: sustituir literales de acción por `AuditAction` en los `@audit` de
  `apps/accounts/services.py`, `apps/authz/services.py`, `apps/directory/services.py`,
  `apps/products/services.py`, `apps/pricing/services.py`, `apps/credit/services.py`. **Los valores
  persistidos no cambian.**
- [x] **2.6** Reconciliación de la fuente de verdad: editar `openspec/config.yaml` **L139–140** para
  describir el mecanismo real (`@audit` = evento; `record_field_changes` = diff campo/anterior/nuevo;
  vocabulario `AuditAction`).

## Fase 3: Integración de Datos (Frontend — Hooks)

- [x] **3.1** **N/A** — F10 no tiene superficie de usuario; sin hooks de Refine.
- [x] **3.2** **N/A** — Sin schema Zod que validar.

## Fase 4: Componentes y Páginas (Frontend — UI)

- [x] **4.1–4.5** **N/A** — Sin componentes, páginas ni resources de Refine. La vista de consulta del log
  es de una fase posterior.

## Fase 5: Seguridad y DevSecOps

- [x] **5.1** `ruff check` + `ruff format --check` + `mypy --strict` sobre `backend/apps/common/` y los
  services retrofiteados. Corregir todos los errores.
- [x] **5.2** `bandit -c pyproject.toml -r apps` sobre `apps/common`: confirmar que no hay SQL raw ni
  secretos en el diff. Corregir toda alerta MEDIUM o superior.
- [x] **5.3** **N/A** — Sin frontend que lintear.
- [x] **5.4** Verificar que no hay secretos en el diff (credenciales, tokens, connection strings).
- [x] **5.5** `pip-audit` (gate global; sin dependencias nuevas).
- [x] **5.6** **N/A** — Sin componentes UI ni contraste de color que validar.

## Fase 6: Pruebas y Validación Final

- [x] **6.1** Backend — Escribir pruebas del mecanismo en `backend/apps/common/tests/`:
  - Una fila por campo corregido; múltiples campos → múltiples filas.
  - Campo no auditable → sin fila; sin cambio real → sin fila.
  - Acción `CORRECTION` ≠ `UPDATE`.
  - Normalización de `Decimal` (`"12.50"`, sin exponente) / fecha ISO / FK→pk / `None`→`""`.
  - Usar una entidad existente real (sin retrofitear su service) o un modelo de prueba.
  - Ejecutar con `uv run pytest backend/apps/common/tests/ -v --cov`.
- [x] **6.2** Backend — Test de compatibilidad del retrofit: el evento grueso de un service de F1–F7
  conserva su valor de acción persistido (p. ej. `AuditLog.action == "UPDATE"`) tras la sustitución por el enum.
- [x] **6.3** **N/A** — Sin E2E/Playwright (no hay UI).
- [x] **6.4** Integración — Verificar: sin migración pendiente; sin operaciones síncronas bloqueantes; la
  cadena de trazabilidad sigue íntegra (F10 no la toca).
- [x] **6.5** Definition of done — Todos los gates de backend en verde, ejecutados **localmente**, antes
  de declarar el change completo: `ruff check` + `ruff format --check`, `mypy --strict`, `bandit`,
  `pip-audit`, `pytest` (cobertura ≥80% global). Sin gates de frontend (no hay UI).
