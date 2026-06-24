# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Fuente de verdad

`openspec/config.yaml` es la fuente de verdad del proyecto. Ante cualquier conflicto entre el
código, este archivo, el README o los runbooks de `documents/`, **manda `config.yaml`**. Léelo
antes de tomar decisiones de arquitectura, stack o convenciones — contiene el contexto de dominio,
el sistema visual (design tokens con sus hex exactos), los invariantes de negocio inviolables y los
patrones arquitectónicos obligatorios.

Idioma: documentación y lógica de negocio en **español**; código, rutas de API e identificadores
técnicos en **inglés**. Reglas y requisitos se redactan con keywords RFC 2119 (MUST, SHOULD, MAY).

## Monorepo y contrato inter-app

```
backend/    Django 5.2 LTS + DRF — fuente de verdad del contrato OpenAPI. Cloud Run (Docker).
frontend/   React 19 + Vite + Refine v5 — GENERA tipos TS + Zod desde el OpenAPI. Vercel (sin Docker).
openspec/   config.yaml (fuente de verdad), schemas, changes, specs.
documents/  PLAN_DE_FASES.md y runbooks.
```

El **backend es la fuente de verdad** del contrato. El frontend espeja los tipos **generándolos**
desde `backend/schema.yml` (OpenAPI de DRF) con `npm run codegen` → `src/shared/api/schema.ts`
(tipos) y `src/shared/api/zod.ts` (esquemas Zod). NUNCA al revés; los esquemas Zod MUST NOT
escribirse a mano. Tras cambiar serializers/endpoints, regenera el schema y luego el codegen.
`npm run codegen` incluye un post-paso `codegen/fix-zod-v4.mjs` que adapta los `z.record` que el
generador emite en sintaxis Zod v3 a la de Zod v4. `backend/schema.yml` es artefacto generado
(gitignored): se regenera con `spectacular`, no se commitea.

## Comandos

**Backend** (Python 3.12+, `uv`; correr desde `backend/`):

```bash
uv sync                                   # instala dependencias en .venv
uv run python manage.py migrate
uv run python manage.py runserver         # OpenAPI en /api/schema/, Swagger en /api/docs/
uv run python manage.py spectacular --file schema.yml   # regenerar OpenAPI (insumo del codegen)

# Gates de calidad (orden bloqueante de §7.1):
uv run ruff check . && uv run ruff format --check .
uv run mypy .                             # strict
uv run bandit -c pyproject.toml -r apps config
uv run pip-audit
uv run pytest                             # cobertura >=80% global

uv run pytest apps/authz/tests/test_authz_api.py             # un archivo
uv run pytest apps/authz/tests/test_authz_api.py::test_x     # un test

# Tests con Postgres (paridad con prod): con DATABASE_URL→Supabase, pytest NO puede crear la
# DB de test (el pooler no tiene CREATEDB). Levanta Postgres local y apunta los tests ahí:
docker compose -f docker-compose.dev.yml up -d
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/postgres uv run pytest
```

**Frontend** (Node 24+; correr desde `frontend/`):

```bash
npm install
npm run codegen        # genera tipos TS + Zod desde ../backend/schema.yml — correr antes de dev
npm run dev
npm run lint           # eslint
npm run typecheck      # tsc -b
npm test               # vitest run (un archivo: npx vitest run ruta/al/archivo.test.ts)
npm audit --audit-level=moderate
npx playwright test    # E2E + WebKit (Safari iOS)
```

### Definition of Done (no negociable)

Antes de declarar una tarea completa, el agente MUST ejecutar localmente **todos** los gates del
pipeline que apliquen y dejarlos en verde. NO se delega el descubrimiento de fallos al CI. `main`
está protegida; todo cambio entra por Pull Request con el pipeline verde. La CI dispara por path
(`.github/workflows/backend.yml` y `frontend.yml` solo corren si cambió su subdirectorio).

## Arquitectura del backend

- **Lógica de negocio SOLO en `services/`.** Los ViewSets y serializers de DRF son delgados:
  reciben, validan y delegan. Estructura por app: `apps/<app>/` con `models.py`, `serializers.py`,
  `views.py`, `services.py`, `urls.py`, `tests/`. `apps/common/` aloja transversales
  (excepciones, auditoría, modelos base).
- **Cálculo financiero en funciones puras** sin dependencia del ORM (FIFO, costo nominal/efectivo,
  merma, saldos CxC/CxP), testeables aisladas — habilita el gate de cobertura **≥90%** en esos módulos.
- **Transacciones:** toda operación multi-tabla va en `transaction.atomic()` con rollback total.
- **Auditoría centralizada** vía decorador `@audit(action, entity)` en services; no se repite la
  lógica de logging. Registra fecha/hora, usuario, campo, valor anterior y nuevo.
- **Settings split:** `config/settings/base.py` (compartido) + `dev.py` / `prod.py`. Secretos SOLO
  por variables de entorno (GCP Secret Manager en prod); nunca en el repo. La DB real es **PostgreSQL
  en Supabase**, conectada por la **Session pooler** (IPv4) en `DATABASE_URL` — la conexión directa
  (`db.<ref>.supabase.co`) es IPv6-only e inalcanzable desde muchos entornos. `DATABASE_URL` es
  **obligatorio** (PostgreSQL en todos los entornos; **sin fallback SQLite**); dev y tests usan el
  Postgres local de `docker-compose.dev.yml`, y el CI levanta su propio servicio Postgres. Usuario
  propio `accounts.User` (extiende `AbstractUser` con `role`); F2 añade el FK `profile`; F3 el flag
  `must_change_password`.
- **Auth:** SimpleJWT (access 15 min / refresh 7 días, rotación + blacklist). El refresh viaja en
  cookie httpOnly (`/auth`); el access NUNCA en cookie — va en el cuerpo y vive en memoria del cliente.
  **Cambio forzado (F3):** un middleware (`apps/accounts/middleware.py`) resuelve el usuario por el JWT
  y, mientras `must_change_password` esté activo, bloquea con 403 toda operación salvo `me`,
  `change-password` y `logout`.
- **Autorización (access-control, F2 — app `authz`):** `Profile` (catálogo, soft delete clase 2) es la
  fuente de verdad de los permisos por `(módulo, acción)`; las permission classes de DRF resuelven por
  el perfil del usuario (deniegan con 403 `{detail}` genérico) y el `SensitiveFieldsMixin` OMITE del
  output los campos sensibles que el perfil no puede ver (no los enmascara). La autorización MUST
  resolverse por el perfil, nunca por el `role` nominal. El catálogo de módulos/acciones y el registro
  de campos sensibles viven en `apps/authz/catalog.py`, extensibles por fase.
- **Gestión de identidad (user-management, F3 — apps `accounts` + `authz`):** consola de administración
  restringida al Jefe. Usuarios (`/auth/users…`): alta/edición, **reset administrativo** (contraseña
  temporal dada o generada + activa `must_change_password` + blacklist), desactivación/reactivación
  (blacklist). Perfiles (`PATCH/DELETE /authz/profiles/{id}`): editar permisos y baja (soft delete clase
  2; **409** si tiene usuarios asignados). La asignación de perfil de F2 (`assign-profile`) se extiende
  para sincronizar `role` + blacklist. La autorización **reutiliza** el módulo `access-control`
  (read/create/update), sin tocar el seed. 409 vía `Conflict` en `apps/common/exceptions.py`. Eventos de
  seguridad auditados con `@audit`.
- **Cloud Run = stateless:** filesystem efímero, escribir SOLO en `/tmp`; sin estado en memoria
  entre requests; sin threads de fondo (tareas vía Cloud Scheduler, no Celery); escuchar en `$PORT`.

### Invariantes de negocio (ver §"Invariantes" en config.yaml para la lista completa)

Reglas inviolables al escribir lógica: período cerrado bloquea crear/editar documentos con fecha en
él; **Kardex append-only** (nunca borrar/editar movimientos — las correcciones generan eventos de
auditoría y recálculos); FIFO con saldo nunca negativo; doble costeo nominal/efectivo; snapshot
inmutable de la entrega al pasar a GENERADO; nota de crédito de proveedor siempre ligada a un Ingreso.
**Soft delete por política de tres clases** (no global): documentos con máquina de estado y Kardex son
inmutables/append-only; catálogos sin estado usan `deleted_at` + manager que filtra; fichas de
Directorio se dan de baja con estado INACTIVO.

## Arquitectura del frontend

- **Feature-driven alrededor de los resources de Refine:** `src/features/<feature>/` con
  `components/`, `hooks/`, `types/`, `api/`, `providers/`, `store/`. Lógica compartida en
  `src/shared/`. Componentes visuales reutilizables en `@/components/custom/`; primitivos shadcn en
  `@/components/ui/`. `src/pages/` son **dumb pages**: sin estado ni llamadas directas a la API —
  lo asíncrono se encapsula en custom hooks dentro de `features/`.
- **Refine v5** gestiona el estado de servidor (React Query vive DENTRO de Refine; MUST NOT montar
  un TanStack Query paralelo). **Zustand SOLO para estado de UI/sesión** (tema, sidebar, filtros);
  nunca para estado de servidor.
- **Formularios:** React Hook Form + Zod resolver, con el Zod **generado** del OpenAPI.
- Alias de import: `@/*` → `src/*`. shadcn/ui estilo `new-york`, icon library Lucide React.

### Design tokens — fuente única de color

`src/index.css` es la **ÚNICA** fuente de color (Tailwind v4 CSS-first). Define el contrato canónico
de variables CSS de shadcn en `:root`/`.dark` y las expone como utilidades vía `@theme inline` (no
hay `tailwind.config.js`). **CERO hex literales en componentes** — usa siempre las utilidades de
token (`bg-primary`, `text-muted-foreground`, `border`, `rounded-md`, etc.). Los valores exactos de
la paleta (neutros cálidos Notion/Claude, primary índigo frío, semánticos success/warning/danger/info
exclusivos de estado) están fijados en `config.yaml` → "Sistema visual"; modo claro y oscuro REQUIRED.
Dark mode por clase `.dark` en `<html>`, gobernado por `ThemeProvider`.

## Convenciones

- **Commits:** Conventional Commits de una línea — `type(scope): subject`.
- **Versiones pineadas** en lockfiles (`uv.lock`, `package-lock.json`). Los upgrades son PRs
  deliberados gateados por escaneo de dependencias + tests; no se flota a la última versión.
- **KISS/YAGNI ganan** los empates con SOLID (proyecto de un dev; evitar sobre-abstracción). No se
  implementa funcionalidad fuera del alcance del cambio actual; no CRUD completo por defecto.

## Flujo OpenSpec

El trabajo se planifica con OpenSpec (schema `spec-driven`). Skills disponibles: `/opsx:propose`
(crea proposal + design + tasks), `/opsx:apply` (implementa tasks), `/opsx:archive` (archiva y
sincroniza delta specs a `openspec/specs/<capability>/spec.md`), `/opsx:explore` (modo de
pensamiento, sin implementar). Los cambios activos viven en `openspec/changes/`; los archivados en
`openspec/changes/archive/YYYY-MM-DD-<name>/`. Usa el CLI `openspec` (`openspec list --json`,
`openspec status --change <name> --json`) para inspeccionar estado.
