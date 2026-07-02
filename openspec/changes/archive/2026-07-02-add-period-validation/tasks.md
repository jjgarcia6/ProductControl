# Tareas: add-period-validation

> Orden de fases REQUIRED. Las fases que no aplican a esta fase backend-puro (Contrato OpenAPI,
> Frontend) se marcan **N/A** y no se eliminan. Definition of done: todos los gates de backend en
> verde localmente antes de declarar el change completo.

## Fase 0: Contrato y Sincronización Inicial

- [x] **0.1** N/A — F9 no expone serializers ni endpoints (backend puro sin API).
- [x] **0.2** N/A — sin contrato OpenAPI nuevo.
- [x] **0.3** N/A — sin tipos/Zod (no hay UI).
- [x] **0.4** N/A — sin variables de entorno nuevas.

## Fase 1: Modelo de Datos y Migraciones

- [x] **1.1** Crear la app `period` y el modelo `Period` en `backend/apps/period/models.py`:
  `year` (`PositiveIntegerField`), `month` (`PositiveSmallIntegerField`), `status`
  (`OPEN`/`CLOSED`, default `OPEN`); `UniqueConstraint(year, month)` + `CheckConstraint` de rango
  1–12. Hereda solo `TimeStampedModel` (NO `SoftDeleteModel`; soft delete clase 1).
- [x] **1.2** Añadir `"apps.period"` a `LOCAL_APPS` en `backend/config/settings/base.py`
  (tras `"apps.system_settings"`).
- [x] **1.3** Generar migración: `uv run python manage.py makemigrations period`. Revisar
  `0001_initial` (CreateModel + AddConstraint). **Sin** data migration de seed.
- [x] **1.4** Aplicar (`uv run python manage.py migrate`) y probar el reverse
  (`uv run python manage.py migrate period zero`); luego re-aplicar. Verificar reversibilidad limpia.

## Fase 2: Lógica de Negocio y API (Backend)

- [x] **2.1** N/A — sin cálculo financiero en F9.
- [x] **2.2** Implementar el selector `get_period(year, month) -> Period | None` en
  `backend/apps/period/selectors.py`.
- [x] **2.3** Implementar `is_period_closed(doc_date)` y `assert_date_operable(doc_date)` en
  `backend/apps/period/services.py`, levantando
  `ValidationError(["La fecha pertenece a un período cerrado."])` (mapeado a 400 `non_field_errors`
  por `apps.common`). Documentar en docstrings la precondición para fases consumidoras (F11+):
  `DateField` en zona local UTC-5; invocar `assert_date_operable` en create/update (fecha actual y,
  si cambia, la nueva).
- [x] **2.4** N/A — sin endpoints ni URLs (no se toca `config/urls.py`).

## Fase 3: Integración de Datos (Frontend — Hooks)

- [x] **3.1** N/A — F9 no tiene superficie de usuario.
- [x] **3.2** N/A.

## Fase 4: Componentes y Páginas (Frontend — UI)

- [x] **4.1–4.5** N/A — F9 no tiene UI.

## Fase 5: Seguridad y DevSecOps

- [x] **5.1** `ruff check backend/apps/period/` y `mypy --strict` (o `mypy backend/apps/period/`).
  Corregir todos los errores.
- [x] **5.2** `bandit -c pyproject.toml -r backend/apps/period`; confirmar que no hay SQL raw,
  secretos ni credenciales.
- [x] **5.3** N/A — sin frontend.
- [x] **5.4** Verificar que no hay secretos en el diff.
- [x] **5.5** `pip-audit` (sin dependencias nuevas; debe quedar en verde).
- [x] **5.6** N/A — sin componentes UI.

## Fase 6: Pruebas y Validación Final

- [x] **6.1** Tests en `backend/apps/period/tests/` cubriendo los Scenarios del delta:
  - unicidad `(year, month)` → rechazo;
  - mes sin período → operable;
  - período `OPEN` → operable;
  - crear con fecha en período `CLOSED` → 400 `non_field_errors` con el mensaje exacto;
  - documento con fecha en período cerrado → modificación bloqueada;
  - mover fecha hacia período cerrado → bloqueada.
  Los `CLOSED` se establecen creando la fila directamente. Ejecutar con
  `uv run pytest apps/period/tests/ -v --cov`.
- [x] **6.2** N/A — sin tests de frontend.
- [x] **6.3** N/A — sin E2E (no hay UI).
- [x] **6.4** Integración: confirmar migración reversible (`migrate period zero` limpio) y que la
  cadena de trazabilidad no se altera.
- [x] **6.5** Definition of done — gates de backend en verde localmente:
  `ruff check . && ruff format --check .`, `mypy .`, `bandit`, `pip-audit`,
  `pytest` (cobertura ≥80% global). Confirmar antes de declarar el change completo.
