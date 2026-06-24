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

## Capacidades implementadas

El trabajo avanza por fases (ver `documents/PLAN_DE_FASES.md`). Entregadas hasta ahora:

- **F1 · auth** — login (access en memoria + refresh en cookie httpOnly), rotación + blacklist,
  `me`, logout, cambio de contraseña propio, roles del sistema, rate limit de login.
- **F2 · access-control** — perfiles configurables (permisos por `(módulo, acción)` desde un
  catálogo), autorización por perfil en DRF y mecanismo de **campos invisibles** por perfil.
- **F3 · user-management** — consola de administración (solo Jefe): CRUD de usuarios, **reset
  administrativo** con contraseña temporal y **cambio forzado** en el primer acceso, desactivación
  que invalida la sesión, y administración de perfiles (editar permisos / baja con soft delete).

## Arranque local — Backend

Requiere Python 3.12+ y [`uv`](https://docs.astral.sh/uv/).

```bash
cd backend
cp .env.example .env          # ajusta DATABASE_URL, DJANGO_SECRET_KEY, etc.
uv sync                       # crea .venv e instala dependencias
uv run python manage.py migrate
uv run python manage.py runserver
```

- **PostgreSQL es obligatorio en todos los entornos** (`DATABASE_URL` requerido; **sin fallback
  SQLite**). En prod usa la **Session pooler** (IPv4) de Supabase — no la conexión directa
  (`db.<ref>.supabase.co`, IPv6-only e inalcanzable desde Codespaces/CI):
  `postgresql://postgres.<ref>:<password>@aws-<n>-<region>.pooler.supabase.com:5432/postgres`.
- Para desarrollo local sin Supabase, levanta el **Postgres local** (ver la sección de tests) y
  apunta `DATABASE_URL` a `localhost:5433`.
- OpenAPI en `http://localhost:8000/api/schema/`; Swagger UI en `/api/docs/`.
- Regenerar el schema: `uv run python manage.py spectacular --file schema.yml`
  (`backend/schema.yml` es artefacto generado, gitignored — no se commitea).

### Tests del backend (PostgreSQL)

Los tests corren contra PostgreSQL (mismo motor que prod). No uses la `DATABASE_URL` de Supabase
para tests: la **Session pooler** no tiene `CREATEDB`, así que `pytest` no puede crear su base de
test. Levanta el Postgres local y apunta los tests ahí — sin tocar tu `.env`, porque `load_dotenv`
usa `override=False`:

```bash
cd backend
docker compose -f docker-compose.dev.yml up -d     # Postgres 17 en localhost:5433
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/postgres uv run pytest
```

El CI levanta su propio servicio Postgres y exporta `DATABASE_URL` para todos los gates.

Gates de calidad (todos deben pasar antes de declarar una tarea completa):

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy .
uv run bandit -c pyproject.toml -r apps config
uv run pip-audit
uv run pytest          # cobertura >=80% global
```

## Arranque local — Frontend

Requiere Node 24+ (Node 20 está EOL; CI corre sobre Node 24).

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
- **Design tokens**: `frontend/src/index.css` es la **única fuente de color** (variables CSS de
  shadcn vía `@theme inline`, Tailwind v4 CSS-first). CERO hex literales en componentes.
- **Contexto para agentes**: ver `CLAUDE.md` (raíz) para arquitectura y comandos de un vistazo.

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

3. **TypeScript 6.x y Tailwind 4.x (actualización de stack, 2026-06-23).** Las decisiones
   cerradas originales (§1) eran TS 5.x y Tailwind 3.x; se subieron a sus últimas estables —
   **TypeScript `~6.0` (6.0.3)** y **Tailwind `^4.3.1`** — y el runbook se actualizó en
   consecuencia. Detalle de la migración de Tailwind 3 → 4:
   - Se eliminaron `postcss` y `autoprefixer` y el archivo `postcss.config.js`; Tailwind 4 trae
     autoprefixing y nesting integrados (Lightning CSS).
   - Se añadió el plugin oficial **`@tailwindcss/vite`** (registrado en `vite.config.ts`), que
     reemplaza al plugin de PostCSS.
   - En `src/index.css` las tres directivas `@tailwind` se reemplazaron por `@import "tailwindcss";`.
   - Para TS 6: se quitó `baseUrl` de `tsconfig.app.json` (deprecado en TS6, eliminado en TS7);
     con `moduleResolution: "bundler"` el alias `@/*` sigue funcionando solo con `paths`.
   - Verificado en verde: `typecheck`, `build`, `lint` y `vitest`.

4. **Tema CSS-first y alineación con shadcn/ui (change `align-shadcn-tailwind4-tokens`).**
   El config.yaml exige shadcn/ui + Lucide React. Se adoptó el **contrato canónico de variables
   CSS de shadcn** (`card`, `popover`, `secondary`, `muted`, `accent`, `destructive`, `input`,
   `ring`, `--radius` único) mapeando la paleta del proyecto (neutros cálidos, índigo frío como
   `primary`, semánticos `success/warning/danger/info` exclusivos de estado) dentro de esos slots.
   - Se **eliminó `tailwind.config.js`**: el theme pasó a ser **CSS-first** vía `@theme inline` en
     `src/index.css`, que es ahora la **única fuente de color** (cero hex literales en componentes).
     Dark mode por clase `.dark` con `@custom-variant`, no por `darkMode: 'class'` en config JS.
   - Se instalaron las dependencias que el config.yaml exigía y faltaban: `lucide-react`,
     `class-variance-authority`, `tw-animate-css`.
   - Se creó `src/components/ui/` (estilo `new-york`, `components.json`) para que `npx shadcn add`
     funcione out-of-the-box, conservando los tokens propios (`--surface` y los semánticos) por
     encima del set shadcn.

5. **Override de `typescript` para `openapi-typescript`.** `openapi-typescript@7.13.0` aún
   declara su peer como `typescript ^5.x` y bloquearía el install con TS 6. Se añadió
   `overrides.openapi-typescript.typescript = "$typescript"` para que use la misma versión raíz
   (6.0.3). El CLI emite los tipos igual; revisar cuando publique soporte formal a TS 6.

6. **ESLint en vez del `oxlint` del scaffold.** El runbook (§5.7) y la CI (§7.2) exigen
   `eslint` como linter bloqueante; se reemplazó `oxlint` por `eslint` (flat config).

7. **Artefactos de codegen: type-check reactivado al añadir endpoints.** En el bootstrap el OpenAPI
   estaba vacío y `src/shared/api/schema.ts` y `zod.ts` se excluían de `tsc`/`eslint`. Con auth (F1)
   y access-control (F2) el contrato ya tiene endpoints, así que el chequeo de esos artefactos está
   **reactivado** (forman parte de `tsc` y `eslint`). La regla "Zod siempre generado, nunca a mano"
   se mantiene: `npm run codegen` los produce.

8. **Override de `js-yaml ^4.2.0`** en el frontend para cerrar un advisory moderado transitivo
   de `@redocly/openapi-core` (vía el toolchain de codegen), dejando `npm audit` en limpio.

9. **Adaptación de `openapi-zod-client` a Zod v4 (change `add-access-control`).** El generador
   (`openapi-zod-client@1.18.3`) emite `z.record(value)` (sintaxis Zod v3), pero el proyecto fija
   Zod v4, que exige `z.record(key, value)`. El primer tipo-mapa del contrato (`permissions` de
   access-control) lo destapó; se añadió un paso de pipeline `codegen/fix-zod-v4.mjs` al script
   `codegen` que reescribe `z.record(` → `z.record(z.string(), ` sobre el `zod.ts` generado (las
   claves de OpenAPI `additionalProperties` siempre son string). No es edición manual del artefacto;
   revisar cuando el generador soporte Zod v4 de forma nativa.
