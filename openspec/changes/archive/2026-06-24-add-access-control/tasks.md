# Tareas: add-access-control
<!-- Orden de fases REQUIRED: Contrato → Migraciones → Backend → Frontend → Seguridad → Pruebas. -->
<!-- Cada tarea nombra el archivo o módulo exacto a crear o modificar. -->

## Fase 0: Contrato y Sincronización Inicial

- [x] **0.1** Backend — Definir en `apps/authz/serializers.py`: `ProfileReadSerializer`,
  `ProfileWriteSerializer` (con `help_text` por campo y validación de `permissions`/
  `visible_sensitive_fields` contra el catálogo) y `AssignProfileSerializer`. Extender el serializer
  de identidad de F1 (`UserIdentityReadSerializer`) para incluir `profile`.
- [x] **0.2** Backend — Definir el `SensitiveFieldsMixin` (omite, no enmascara) en
  `apps/authz/serializers.py` y anotar los endpoints con `drf-spectacular`, marcando como **opcionales**
  los campos sensibles. Regenerar `backend/schema.yml` con
  `uv run python manage.py spectacular --file schema.yml`.
- [x] **0.3** Frontend — Regenerar tipos/Zod desde el OpenAPI con `npm run codegen`
  (`src/shared/api/schema.ts` + `zod.ts`). Verificar que los campos sensibles quedan `optional`.
  MUST NOT escribirse Zod a mano. Incluir el paso de pipeline `codegen/fix-zod-v4.mjs` (adapta
  `z.record` de Zod v3 a v4) en el script `codegen` de `package.json`.
- [x] **0.4** Global — Sin variables de entorno nuevas; confirmar que `backend/.env.example` y
  `frontend/.env.example` no requieren cambios.

## Fase 1: Modelo de Datos y Migraciones

- [x] **1.1** Crear la app `authz` (`apps/authz/`) y definir `Profile` en `apps/authz/models.py`:
  heredar de `SoftDeleteModel` (que ya incluye `TimeStampedModel`) de `apps/common/models.py`; campos
  `name`, `description`, `permissions` (JSON), `visible_sensitive_fields` (JSON), `auto_approval`;
  `UniqueConstraint` parcial (`condition=Q(deleted_at__isnull=True)`) sobre `name`. Generalizar los
  managers de soft delete en `apps/common/models.py` (`TypeVar`) para que `Profile.objects` tipe
  correctamente bajo `mypy --strict`.
- [x] **1.2** Definir el catálogo central de módulos/acciones y el registro de campos sensibles como
  constantes en `apps/authz/catalog.py` (extensibles por fase; F2 registra el módulo de identidad/perfiles).
- [x] **1.3** Añadir el FK `profile` (FK→`authz.Profile`, `null=True`, `on_delete=PROTECT`) al modelo
  `accounts.User`.
- [x] **1.4** Generar migraciones: `uv run python manage.py makemigrations authz accounts`. Crear la
  data migration de seed (`seed_system_profiles` + `remove_system_profiles`) y la de backfill del FK
  a perfiles homónimos, ambas con `reverse_code` (nunca noop si hay datos).
- [x] **1.5** Aplicar: `uv run python manage.py migrate`. Verificar tablas/constraints.
- [x] **1.6** Probar el reverse: `uv run python manage.py migrate authz zero` (y el reverse de
  `accounts`); luego re-aplicar `migrate`. Confirmar que la reversión funciona sin errores.

## Fase 2: Lógica de Negocio y API (Backend)

- [x] **2.1** Implementar las funciones de resolución en `apps/authz/services.py`:
  `resolve_permission(profile, module, action)` y `visible_fields_for(profile, resource)`
  (sin dependencia del ORM en la lógica de decisión, testeables aisladas).
- [x] **2.2** Implementar en `apps/authz/services.py` `assign_profile(user, profile)` con
  `@audit("UPDATE", "User")` dentro de `transaction.atomic()`, y `seed_system_profiles()` idempotente.
- [x] **2.3** Implementar las permission classes en `apps/authz/permissions.py`
  (`HasModulePermission`) que delegan en `resolve_permission` y devuelven `403 {detail}` genérico al denegar.
- [x] **2.4** Implementar los endpoints en `apps/authz/views.py` (ViewSets/APIViews delgados que
  delegan en services): `GET /authz/profiles`, `GET /authz/profiles/{id}`, `POST /authz/profiles`,
  `POST /authz/users/{id}/assign-profile`. Registrar rutas en `apps/authz/urls.py`.
- [x] **2.5** Modificar el endpoint `GET /auth/me` (F1) para incluir el perfil del usuario usando el
  serializer extendido de 0.1.

## Fase 3: Integración de Datos (Frontend — Hooks)

- [x] **3.1** Modificar `src/features/auth/store/session.store.ts` para incluir `profile` en la sesión
  (Zustand, solo estado de sesión).
- [x] **3.2** Crear `src/features/auth/hooks/usePermissions.ts`: envuelve `useGetIdentity` de Refine y
  expone `canDo(module, action)` y `canSee(resource, field)` derivados del perfil. Validar la respuesta
  contra el schema Zod generado en Fase 0. Actualizar `src/features/auth/index.ts`.

## Fase 4: Componentes y Páginas (Frontend — UI)

- [x] **4.1** Aplicar el gating con `usePermissions` en los componentes ya existentes (ocultar
  acciones/columnas según perfil) — defensa secundaria. No se crean páginas ni componentes nuevos.
- [x] **4.2** Manejar los errores `403` como aviso limpio (`{detail}`) vía el `notificationProvider`
  de F1; tolerar la ausencia de campos sensibles opcionales sin romper la UI.

## Fase 5: Seguridad y DevSecOps

- [x] **5.1** Backend — `uv run ruff check apps/authz apps/accounts && uv run ruff format --check .`
  y `uv run mypy .` (strict). Corregir todos los errores.
- [x] **5.2** Backend — `uv run bandit -c pyproject.toml -r apps/authz`. Resolver toda alerta MEDIUM+.
- [x] **5.3** Frontend — `npm run lint` y `npm run typecheck` sobre `src/features/auth/`.
- [x] **5.4** Global — Verificar que toda decisión de acceso es **server-side** y que los campos
  invisibles **nunca se serializan** para perfiles sin permiso (no solo ocultos en UI). Verificar que
  los `403` no filtran estructura interna sensible (mensaje genérico). Sin secretos en el código.
- [x] **5.5** Dependencias — Si se añadieran: `uv run pip-audit` y `npm audit --audit-level=moderate`.
  Mantener el gate de imagen en CI: `trivy` sobre la imagen Docker del backend (sin cambios de
  `Dockerfile` en esta fase, pero el paso no se elimina).

## Fase 6: Pruebas y Validación Final

- [x] **6.1** Backend — Tests en `apps/authz/tests/` cubriendo todos los Scenarios del spec: crear
  perfil; nombre duplicado (400); permiso fuera de catálogo (400); asignación (éxito); perfil
  inexistente (404); asignación sin rol Jefe (403); identidad con perfil; acción permitida/denegada
  (403); auto-aprobación habilitada/deshabilitada; perfiles semilla; idempotencia del seed.
  Ejecutar con `uv run pytest apps/authz -v --cov` (cobertura ≥80%).
- [x] **6.2** Backend — Test específico del `SensitiveFieldsMixin`: el campo sensible **no aparece**
  en el JSON para un perfil sin acceso (la clave está ausente; no basta read-only/enmascarado).
- [x] **6.3** Frontend — Tests (Vitest + RTL) de `usePermissions` y del gating por perfil; tolerancia
  a la ausencia de campos opcionales. Ejecutar con `npx vitest run src/features/auth`.
- [x] **6.4** Integración — Verificar: migración `authz`+`accounts` reversible (reverse + migrate sin
  pérdida); sin errores en consola del navegador; la cadena de trazabilidad no se altera.
- [x] **6.5** Definition of done — Todos los gates en verde localmente antes de declarar el change
  completo: `ruff`, `mypy --strict`, `bandit`, `pip-audit`, `pytest` (≥80%); `eslint`, `tsc`,
  `npm audit`, `vitest`.
