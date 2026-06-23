# Bootstrap del stack y repositorio — Sistema de gestión operativa

**Tipo:** Runbook de habilitación (Fase 0 técnica)
**Destinatario:** Agente de implementación (Claude Code)
**Fuente de verdad:** `openspec/config.yaml`. Ante cualquier conflicto entre este runbook y el `config.yaml`, **manda el `config.yaml`**.
**Versión:** 1.1

> **Cambios respecto a v1.0:** incorporación del **contrato de errores uniforme** (sección 6) — exception handler de DRF en backend y manejo de errores sin ruido en frontend — más sus guardrails y verificaciones. Renumeración de las secciones posteriores. Este runbook es la versión completa para recrear el proyecto desde cero; si ya ejecutaste la v1.0, aplica solo el adendum `00b-adendum-contrato-de-errores.md`.

---

## 0. Cómo usar este documento

Este runbook instala y configura el **andamiaje** del proyecto: estructura del monorepo, backend, frontend, contrato de errores, tooling de calidad, CI/CD y configuración del repositorio. **No implementa lógica de negocio** de ningún módulo (eso vive en los changes de OpenSpec posteriores).

Reglas para el agente:

- Ejecuta los pasos **en orden**. No saltes verificaciones.
- Las versiones indicadas son **pisos / decisiones cerradas**, no versiones exactas a clavar. Resuelve la última versión compatible de cada paquete contra su documentación actual, respetando los pisos.
- Si un comando de scaffolding cambió respecto a lo aquí descrito, **prioriza la documentación oficial vigente** de la herramienta y conserva la *intención* del paso.
- Al terminar cada bloque (backend, frontend, errores, CI), corre su verificación antes de avanzar.
- **No** instales nada fuera de lo listado sin justificarlo contra el `config.yaml`.
- Documenta en el `README.md` raíz cualquier desviación que tomes y su motivo.

---

## 1. Decisiones cerradas (no re-decidir)

| Área | Decisión | Nota |
|---|---|---|
| Gestor de paquetes backend | **uv** | Crea y gestiona `.venv` |
| Python | **3.12+** | |
| Framework backend | **Django 5.2 LTS** | LTS por mantenibilidad de un solo dev |
| API | **DRF 3.15+** | |
| Auth | **djangorestframework-simplejwt 5.x** | **Fijo. No usar Supabase Auth** |
| OpenAPI | **drf-spectacular** | El schema del backend es la fuente de tipos |
| Node | **20.19+** | Requerido por OpenSpec y por el tooling frontend |
| Framework frontend | **React 19** | (Reemplaza a React 18 del stack v2.3) |
| Build | **Vite 5+** | |
| Meta-framework | **Refine v5** | (Reemplaza a Refine 4 del stack v2.3) |
| UI | **Shadcn/UI + Tailwind 3.x** | |
| Tipos/validación | **TypeScript 5.x (strict) + Zod** | Zod **generado** desde OpenAPI, nunca a mano |
| Estado servidor | **React Query dentro de Refine** | Sin TanStack en paralelo |
| Estado UI/sesión | **Zustand** | Solo UI/sesión, no datos de servidor |
| Base de datos | **PostgreSQL vía Supabase** | **Solo base de datos**: sin Auth/Realtime/Storage |
| Contenedor | **Docker solo en backend** | Cloud Run. Vercel compila desde fuente |
| Color de acento | **#4F52C9 (light) / #8488E6 (dark)** | Light/dark obligatorio |
| Contrato de errores | **`{campo: [mensajes]}` / `{detail}`, en español, sin ruido** | Transversal a todas las fases (sección 6) |

---

## 2. Prerrequisitos del entorno

Verifica que existan (instala lo que falte):

```bash
python3 --version    # >= 3.12
node --version       # >= 24.14
git --version
uv --version         # si falta: curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## 3. Estructura objetivo del monorepo

```
.
├── backend/                 # Django + DRF (contenerizado)
│   └── .env.example         # variables del backend (Django/PG/Resend/Meta/GCP)
├── frontend/                # React 19 + Vite + Refine (sin Docker)
│   └── .env.example         # variables del frontend (solo VITE_*)
├── openspec/                # ya existente: config.yaml, schemas, changes, specs
├── documents/               # PLAN_DE_FASES.md y documentación de proyecto
├── .github/
│   └── workflows/
│       ├── backend.yml      # pipeline backend (path-triggered)
│       └── frontend.yml     # pipeline frontend (path-triggered)
├── .gitignore
└── README.md
```

> La CI **debe** dispararse por path: el pipeline de backend solo corre si cambió `backend/`; el de frontend solo si cambió `frontend/`.

---

## 4. Backend — paso a paso

### 4.1 Crear el proyecto y el entorno virtual

```bash
mkdir -p backend && cd backend
uv init --package .
uv venv                       # crea .venv en backend/.venv
source .venv/bin/activate     # ACTIVAR EL ENTORNO VIRTUAL (obligatorio antes de continuar)
```

> A partir de aquí, **todo comando de backend se ejecuta con el `.venv` activado**. Verifica con `which python` que apunte a `backend/.venv/bin/python`. Como alternativa puntual puedes usar `uv run <comando>`, pero el flujo por defecto de este runbook asume el `.venv` activado.

### 4.2 Instalar dependencias

Dependencias de producción:

```bash
uv add django djangorestframework djangorestframework-simplejwt \
       django-cors-headers django-ratelimit drf-spectacular \
       psycopg[binary] python-dotenv \
       weasyprint openpyxl google-cloud-storage \
       gunicorn
```

Dependencias de desarrollo:

```bash
uv add --dev ruff mypy bandit pip-audit pytest pytest-django pytest-cov \
             django-stubs djangorestframework-stubs
```

### 4.3 Crear el proyecto Django

```bash
uv run django-admin startproject config .
```

Estructura de apps por capability (crea las carpetas base; **vacías de lógica**, solo el esqueleto de app Django):

```bash
mkdir -p apps
# Las apps de negocio se crearán en sus changes respectivos.
# En el bootstrap solo se crean las apps de soporte transversal:
uv run python manage.py startapp common apps/common      # modelos base, soft delete, auditoría, exception handler
```

> **No** crees aquí las apps de Directorio, Kardex, etc. Eso pertenece a cada change. El bootstrap solo deja `common` (utilidades transversales) y la configuración.

### 4.4 Settings por entorno

Divide `config/settings/` en `base.py`, `dev.py`, `prod.py`. Reglas:

- Secretos y credenciales **solo** desde variables de entorno (`python-dotenv` en dev, GCP Secret Manager en prod). **Nunca** en el repositorio.
- `DATABASES` apunta a Supabase (PostgreSQL) vía `DATABASE_URL`. **No** se configura ningún cliente de Supabase Auth/Realtime/Storage.
- `REST_FRAMEWORK`: autenticación por `JWTAuthentication` (SimpleJWT), `DEFAULT_SCHEMA_CLASS` de drf-spectacular, y `EXCEPTION_HANDLER` del contrato de errores (ver sección 6).
- SimpleJWT: access token **15 min**, refresh token **7 días**.
- `LANGUAGE_CODE = "es"` (los mensajes de error por defecto salen en español).
- `CORS_ALLOWED_ORIGINS`: solo el dominio de Vercel (configurable por entorno).
- `django-ratelimit` activo en endpoints de login.
- `DEBUG = False` en `prod.py` (obligatorio para que el contrato de errores no filtre tracebacks).

### 4.5 Modelos base transversales (en `apps/common`)

Deja preparados, **sin lógica de negocio**:

- Un `TimeStampedModel` abstracto (`created_at`, `updated_at`).
- La infraestructura de **soft delete de 3 clases** según el `config.yaml`:
  1. Documentos con máquina de estados / Kardex → **append-only / inmutables** (no se borran; se revierten por estado). El bootstrap solo documenta la convención; no fuerza un mixin de borrado.
  2. Catálogos y maestros sin máquina de estados → soft delete con `deleted_at`, manager por defecto que filtra, e índices únicos parciales.
  3. Fichas de Directorio → estado `INACTIVO` (no borrado).
- El **mecanismo** de auditoría (modelo de log + decorador/función `@audit(action, entity)`), **sin** las reglas de qué se audita (eso va en el change `add-audit-rules`).

> El **exception handler** del contrato de errores también vive en `apps/common`, pero se detalla en la sección 6 por ser transversal a backend y frontend.

### 4.6 Tooling de calidad (configuración)

- `ruff`: configurado en `pyproject.toml` (lint + format).
- `mypy`: **modo strict**, con `django-stubs` y `djangorestframework-stubs`.
- `bandit`: SAST sobre `apps/` y `config/`.
- `pip-audit`: escaneo de dependencias.
- `pytest` + `pytest-django` + `pytest-cov`: gate de cobertura **≥80% global**, **≥90% en módulos de cálculo financiero**. La lógica financiera (FIFO, costeo, merma, saldos) **debe** vivir en funciones puras sin dependencia del ORM, para poder testearla aislada (esto se hará en sus changes; el bootstrap solo deja el gate configurado).

### 4.7 Dockerfile (Cloud Run)

- Imagen base Python 3.12 slim.
- **Instalar las libs nativas de WeasyPrint** (Pango, Cairo, GDK-Pixbuf y dependencias) vía `apt`, o WeasyPrint no renderiza PDFs.
- Instalar dependencias con `uv` dentro de la imagen.
- Servir con `gunicorn`.
- El contenedor escala a cero en Cloud Run; no incluir worker persistente (no hay Celery).

### 4.8 Verificación del backend

```bash
uv run python manage.py migrate
uv run python manage.py runserver        # arranca sin errores
uv run python manage.py spectacular --file schema.yml   # genera el OpenAPI
uv run ruff check .
uv run mypy .
uv run pytest
```

Todo debe pasar (aunque haya pocos tests aún). El `schema.yml` generado es el insumo del codegen del frontend.

---

## 5. Frontend — paso a paso

### 5.1 Crear el proyecto

Desde la raíz del monorepo:

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

> Si prefieres el scaffolding de Refine con Vite + Shadcn, úsalo respetando React 19, Vite y TypeScript strict. Conserva la intención: React 19 + Vite + TS strict + Refine v5 + Shadcn + Tailwind.

### 5.2 Instalar dependencias

```bash
# Refine (core + integración REST) y router
npm install @refinedev/core @refinedev/react-router @refinedev/simple-rest react-router

# UI: Tailwind + Shadcn
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
# Shadcn: inicializar según su CLI vigente (componentes accesibles sobre Tailwind)

# Validación y estado UI
npm install zod zustand

# Codegen de tipos desde OpenAPI (resolver herramienta vigente; objetivo: TS + Zod desde schema.yml)
npm install -D openapi-typescript
```

### 5.3 TypeScript strict

En `tsconfig.json`: `"strict": true` (y flags estrictos asociados). El type-check (`tsc --noEmit`) es **bloqueante** en CI.

### 5.4 Tema y design tokens

- Implementar `ThemeProvider` con **light/dark obligatorio** vía variables CSS.
- Color de acento: **#4F52C9 (light) / #8488E6 (dark)**. Neutros cálidos, bordes sutiles sobre sombras (estética tipo Notion/Claude).
- Los semánticos de estado (amber para advertencias, red para peligro) **no** deben colisionar con el acento índigo.

### 5.5 Datos y estado

- **React Query vive dentro de Refine.** No instalar ni configurar TanStack Query en paralelo.
- **Zustand solo para estado de UI/sesión** (no para datos de servidor).
- Cliente REST de Refine apuntando al backend; base URL por variable de entorno (`VITE_API_URL`).

### 5.6 Codegen OpenAPI → TS + Zod

- Configurar un script `npm run codegen` que consuma el `schema.yml` del backend y **genere** los tipos TypeScript y los esquemas Zod.
- **Prohibido** escribir tipos o esquemas Zod a mano que dupliquen el contrato. El backend (OpenAPI de DRF) es la **única** fuente de verdad de tipos. Nunca al revés.

### 5.7 Tooling de calidad

```bash
npm install -D eslint vitest @testing-library/react @testing-library/jest-dom \
               @playwright/test
npx playwright install webkit    # WebKit es obligatorio para QA de Safari iOS
```

- `eslint` y `tsc` bloqueantes.
- `vitest` + React Testing Library para unidad/componentes.
- `playwright` con **WebKit** para el QA cross-browser de Safari iOS (inputs numéricos decimales y fechas).
- `npm audit` para dependencias.

### 5.8 Verificación del frontend

```bash
npm run dev          # arranca sin errores
npm run build        # compila
npx tsc --noEmit     # type-check limpio
npx eslint .
npx vitest run
```

---

## 6. Contrato de errores uniforme (transversal)

Define **una sola vez** cómo se ven los errores en todo el sistema. Todas las fases posteriores lo heredan; ninguna inventa su propio formato.

### 6.1 El contrato

Toda respuesta de error del backend cumple **uno** de dos formatos, siempre en español y **sin traceback ni ruido técnico**:

- **Validación (HTTP 400)** — plano, una clave por campo; los errores no atados a un campo van en `non_field_errors`:
  ```json
  { "ruc": ["El RUC ingresado no es válido."], "non_field_errors": ["La fecha pertenece a un período cerrado."] }
  ```
- **Errores generales (401/403/404/409/5xx)** — un único mensaje:
  ```json
  { "detail": "No tiene permiso para realizar esta acción." }
  ```

Nunca se devuelve al cliente: traceback, nombre de excepción, ruta de archivo, SQL ni status interno.

### 6.2 Backend — exception handler

- En `apps/common/exceptions.py`, implementar `custom_exception_handler(exc, context)` que: (1) invoque el handler por defecto de DRF; (2) si hay respuesta, normalice al contrato de §6.1 (validación como `{campo: [mensajes]}` con `non_field_errors`; resto como `{detail}`); (3) si la excepción **no** fue manejada (5xx), registre el traceback **solo en logs del servidor** y devuelva `{ "detail": "Ocurrió un error interno. Intente nuevamente." }` con status 500, sin propagar el traceback.
- Registrar en `REST_FRAMEWORK`:
  ```python
  "EXCEPTION_HANDLER": "apps.common.exceptions.custom_exception_handler",
  ```
- `LANGUAGE_CODE = "es"` y `DEBUG = False` en prod (sin esto el contrato no se garantiza).
- Tests del handler en `apps/common` (400 → `{campo: [mensajes]}`; 403/404 → `{detail}`; excepción no manejada → `{detail}` sin traceback).

### 6.3 Frontend — manejo sin ruido

- En el `dataProvider` de Refine, normalizar las respuestas de error a la forma que Refine espera (objeto con `message`, `statusCode` y, para 400, `errors` por campo). Verificar la forma exacta contra la documentación vigente de Refine.
- **Errores de campo:** mostrar el mensaje del backend junto al campo, con el mismo componente `FieldError` que usan los errores de Zod en cliente.
- **Errores globales:** mostrar `{detail}` con el `notificationProvider` de Refine como aviso limpio (toast/alert).
- **Regla dura:** la UI muestra **solo** el mensaje redactado. Nunca status code crudo, URL, JSON ni stack.

### 6.4 Validación field-level (convención para las fases)

Toda validación de entrada se declara en el **serializer DRF** (backend) y en el **esquema Zod generado** (frontend): tipos numéricos/decimales/texto rechazan entradas inválidas con mensaje específico por campo. Los **validadores de dominio** viven en `utils/validations.py` (según `config.yaml`): enrutan por tipo de identificación y dígito verificador — cédula y RUC de persona natural por módulo 10, sociedades privadas (3er dígito = 9) y sector público (3er dígito = 6) por módulo 11, pasaporte sin checksum. Se estrenan en la fase `add-directory`. Esto no se implementa en el bootstrap; queda como convención que cada fase respeta.

---

## 7. CI/CD — GitHub Actions (path-triggered)

### 7.1 `backend.yml` (se dispara solo si cambia `backend/`)

Orden de etapas, todas **bloqueantes** salvo el deploy:

1. Lint — `ruff`
2. Type-check — `mypy` (strict)
3. SAST — `bandit`
4. Escaneo de secretos — `gitleaks`
5. Escaneo de dependencias — `pip-audit`
6. Tests + cobertura — `pytest` (`≥80%` global, `≥90%` financiero)
7. Build de imagen — `docker`
8. Escaneo de imagen — `trivy`
9. Deploy — Cloud Run

### 7.2 `frontend.yml` (se dispara solo si cambia `frontend/`)

1. Lint — `eslint`
2. Type-check — `tsc`
3. Escaneo de dependencias — `npm audit`
4. Tests — `vitest` (+ Playwright/WebKit donde aplique)
5. Deploy — Vercel (automático)

---

## 8. Configuración del repositorio

- `.gitignore`: `.venv/`, `__pycache__/`, `node_modules/`, `dist/`, `.env`, `*.sqlite3`, `schema.yml` si se regenera, credenciales.
- `.env.example` **por app** (no uno único en la raíz), cada uno con sus variables **sin valores reales**:
  - `backend/.env.example`: variables del backend (`DATABASE_URL`, `DJANGO_SECRET_KEY`, `CORS_ALLOWED_ORIGINS`, claves de Resend/Meta y GCP como placeholders). El backend de desarrollo carga `backend/.env`.
  - `frontend/.env.example`: solo variables `VITE_*` expuestas al cliente (`VITE_API_URL`); **nunca** secretos. Vite carga `frontend/.env`.
- **Branch protection** en la rama principal: PR obligatorio, checks de CI en verde para mergear.
- **Conventional commits** de una línea: `type(scope): subject`.
- `README.md` raíz: instrucciones de arranque local de backend y frontend, y la nota de que `config.yaml` es la fuente de verdad.

---

## 9. Guardrails — qué NO hacer

- **No** implementar lógica de negocio de ningún módulo (Directorio, Kardex, etc.). Eso son changes posteriores.
- **No** usar Supabase Auth, Realtime ni Storage. Supabase es **solo** PostgreSQL.
- **No** introducir Celery ni workers persistentes (rompen el escalado a cero).
- **No** escribir tipos/Zod a mano que dupliquen el OpenAPI.
- **No** instalar TanStack Query en paralelo a Refine.
- **No** commitear secretos ni credenciales.
- **No** contenerizar el frontend (Vercel compila desde fuente).
- **No** devolver tracebacks, status crudos ni formatos de error ad-hoc: todo error pasa por el contrato de la sección 6.
- **No** mostrar ruido técnico (status code, URL, JSON, stack) en la UI.

---

## 10. Definición de Listo (DoD) del bootstrap

El bootstrap está completo cuando **todo** esto es verdad:

- [ ] `backend/` arranca (`runserver`) con el `.venv` activado y migraciones aplicadas.
- [ ] `spectacular` genera el `schema.yml` (OpenAPI) sin errores.
- [ ] `ruff`, `mypy --strict`, `bandit`, `pip-audit` y `pytest` pasan en verde localmente.
- [ ] `frontend/` arranca (`dev`), compila (`build`) y pasa `tsc --noEmit`, `eslint` y `vitest`.
- [ ] El codegen produce tipos TS + Zod a partir del `schema.yml`.
- [ ] El tema light/dark funciona con los tokens índigo definidos.
- [ ] **Contrato de errores activo:** un 400 devuelve `{campo: [mensajes]}` en español; un 403/404 devuelve `{detail}`; una excepción no manejada devuelve `{detail}` genérico sin traceback (con `DEBUG = False`). El frontend mapea errores a campos y muestra `{detail}` como aviso limpio, sin ruido técnico.
- [ ] Ambos pipelines de GitHub Actions existen, son path-triggered y corren en verde.
- [ ] Branch protection activo; `.env.example` por app y `.gitignore` correctos; sin secretos en el repo.
- [ ] `README.md` raíz documenta el arranque local.

Cuando todos los ítems estén marcados, el repositorio está listo para el primer change funcional.
