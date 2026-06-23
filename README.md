# ProductControl — Sistema de gestión operativa

Monorepo del sistema de gestión operativa para una empresa de compra y venta de productos
alimenticios perecibles. Reemplaza controles manuales en hojas de cálculo.

> **Fuente de verdad:** `openspec/config.yaml`. Ante cualquier conflicto entre este README,
> los runbooks y el `config.yaml`, **manda el `config.yaml`**.

## Estructura

```
backend/    # Django 5.2 LTS + DRF (contenerizado, Cloud Run). Fuente de verdad del OpenAPI.
frontend/   # React 19 + Vite + Refine (Vercel, sin Docker). Tipos + Zod generados del OpenAPI.
openspec/   # config.yaml (fuente de verdad), schemas, changes, specs.
documents/  # PLAN_DE_FASES.md y runbooks.
.github/    # CI path-triggered: backend.yml y frontend.yml.
```

El **backend es la fuente de verdad** del contrato (OpenAPI de DRF). El frontend **genera**
sus tipos TypeScript y esquemas Zod desde ese contrato; nunca al revés y nunca a mano.

## Arranque local — Backend

Requiere Python 3.12+ y [`uv`](https://docs.astral.sh/uv/).

```bash
cd backend
cp .env.example .env          # ajusta DATABASE_URL, DJANGO_SECRET_KEY, etc.
uv sync                       # crea .venv e instala dependencias
uv run python manage.py migrate
uv run python manage.py runserver
```

- Sin `DATABASE_URL`, el entorno de desarrollo cae a SQLite local para poder arrancar.
- OpenAPI en `http://localhost:8000/api/schema/`; Swagger UI en `/api/docs/`.
- Regenerar el schema: `uv run python manage.py spectacular --file schema.yml`.

Gates de calidad (todos deben pasar antes de declarar una tarea completa):

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy .
uv run bandit -c pyproject.toml -r apps config
uv run pip-audit
uv run pytest          # cobertura >=80% global
```

## Arranque local — Frontend

Requiere Node 20.19+.

```bash
cd frontend
cp .env.example .env          # VITE_API_URL apuntando al backend
npm install
npm run codegen               # genera tipos TS + Zod desde ../backend/schema.yml
npm run dev
```

Gates de calidad:

```bash
npm run lint        # eslint
npm run typecheck   # tsc
npm test            # vitest
npm audit --audit-level=moderate
npx playwright test # E2E + WebKit (Safari iOS)
```

## Convenciones

- **Commits**: Conventional Commits de una línea — `type(scope): subject`.
- **Ramas**: `main` protegida; todo cambio vía Pull Request con CI en verde.
- **Secretos**: solo por variables de entorno. `.env.example` por app, sin valores reales.

## Desviaciones respecto al runbook `00-bootstrap-stack-y-repositorio-v1.1.md`

El runbook (§0) pide documentar cualquier desviación y su motivo:

1. **Backend como proyecto de aplicación, no `--package`.** `uv init --package` genera un
   layout `src/` con `build-system` pensado para distribuir un paquete. Un proyecto Django
   servido por gunicorn no se distribuye como wheel; el `src/` añadía un stub muerto que
   chocaba con el layout `config/` + `apps/`. Se usó el layout de aplicación (sin
   `build-system`), que es el estándar de Django + uv. Misma intención: backend gestionado
   por uv sobre `pyproject.toml`.

2. **Django fijado a la serie 5.2 LTS.** El resolutor de `uv` ofrecía Django 6.0 (no LTS).
   La decisión cerrada (§1 / config.yaml) es **5.2 LTS**, así que se acotó a `>=5.2,<5.3`.

3. **TypeScript fijado a 5.x y Tailwind a 3.x.** El scaffold de Vite traía TS 6.0 y Tailwind
   sería v4; las decisiones cerradas (§1) son **TS 5.x** y **Tailwind 3.x**. Se fijaron a esas
   series (TS `~5.9`, Tailwind `^3.4`), verificando que compilan con Vite 8.

4. **ESLint en vez del `oxlint` del scaffold.** El runbook (§5.7) y la CI (§7.2) exigen
   `eslint` como linter bloqueante; se reemplazó `oxlint` por `eslint` (flat config).

5. **Artefactos de codegen excluidos del type-check estricto mientras el contrato esté vacío.**
   El bootstrap no define endpoints, así que el OpenAPI no tiene componentes y el generador de
   Zod emite un cliente vacío (sin esquemas que tipar). `src/shared/api/schema.ts` y `zod.ts`
   se excluyen de `tsc` y `eslint` por ahora; el primer change que añada endpoints reactiva su
   chequeo. La regla "Zod siempre generado, nunca a mano" se mantiene: `npm run codegen` los
   produce.

6. **Override de `js-yaml ^4.2.0`** en el frontend para cerrar un advisory moderado transitivo
   de `@redocly/openapi-core` (vía el toolchain de codegen), dejando `npm audit` en limpio.
