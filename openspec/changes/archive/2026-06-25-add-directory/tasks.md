# Tareas: add-directory

> Orden REQUIRED: Contrato (OpenAPI) → Migraciones → Backend → Frontend → Seguridad → Pruebas. No se
> avanza de fase con ítems pendientes. Definition of done: todos los gates del pipeline en verde
> localmente antes de declarar el change completo.

## Fase 0: Contrato y Sincronización Inicial

- [x] **0.1** Backend — Crear los serializers DRF en `backend/apps/directory/serializers.py`
  (`FichaWriteSerializer`, `FichaReadSerializer`, `LinkUserWriteSerializer`) y en
  `backend/apps/credit/serializers.py` (`CreditTermsWriteSerializer`, `CreditTermsReadSerializer`),
  con `help_text` en cada campo. `DecimalField` para `credit_limit` (nunca `FloatField`).
- [x] **0.2** Backend — Anotar los endpoints con `drf-spectacular` y regenerar el OpenAPI:
  `uv run python manage.py spectacular --file schema.yml`. Verificar que expone los nuevos serializers.
- [x] **0.3** Frontend — Regenerar tipos + Zod desde `../backend/schema.yml`: `npm run codegen` →
  `src/shared/api/schema.ts` y `src/shared/api/zod.ts`. MUST NOT escribirse a mano; derivar con `z.infer<>`.
- [x] **0.4** Global — Confirmar que NO se requieren variables nuevas en `backend/.env.example` ni
  `frontend/.env.example` (esta fase no añade secretos).

## Fase 1: Modelo de Datos y Migraciones

- [x] **1.1** Crear la app `directory` y el modelo `Ficha` en `backend/apps/directory/models.py`:
  identificación, contacto, `roles` (`ArrayField` de enum en español MAYÚSCULAS), `status`, O2O `user`
  (`on_delete=SET_NULL`). Hereda `TimeStampedModel` (de `apps/common/models.py`); **NO** `SoftDeleteModel`
  (clase 3). Definir el `UniqueConstraint` parcial del número (`condition=~Q(status="INACTIVO")`) y el
  `GinIndex` de `roles`.
- [x] **1.2** Crear la app `credit` y el modelo `CreditTerms` en `backend/apps/credit/models.py`:
  FK `ficha`, `facet`, `credit_limit` (Decimal), `term_days`, `notice_days` (default 2), con
  `UniqueConstraint(ficha, facet)`. Hereda `TimeStampedModel`.
- [x] **1.3** Generar migraciones: `uv run python manage.py makemigrations directory credit`. Revisar
  los archivos `0001_initial.py` generados.
- [x] **1.4** Aplicar y probar el reverse: `migrate` → `migrate directory zero` / `migrate credit zero`
  → `migrate`. Verificar que las tablas/constraints/índices se crean y se revierten sin error.

## Fase 2: Lógica de Negocio y API (Backend)

- [x] **2.1** Crear las funciones PURAS de validación de identificación en
  `backend/apps/common/validations.py`: enrutar por tipo y dígito verificador (cédula/RUC natural →
  módulo 10; sociedad privada 3er dígito 9 y público 3er dígito 6 → módulo 11; pasaporte sin checksum).
  Sin dependencia del ORM (mismo estilo que `apps/authz/catalog.py`).
- [x] **2.2** Implementar `backend/apps/directory/services.py` (`create_ficha`, `update_ficha`,
  `change_status`, `link_user`): validación de identificación (vía `apps.common.validations`), roles ≥1,
  transiciones de estado y vínculo O2O. `transaction.atomic()`; decorador `@audit`; excepciones
  tipadas; conflictos vía `Conflict` (`apps/common/exceptions.py`).
- [x] **2.3** Implementar `backend/apps/credit/services.py` (`upsert_terms`): integridad faceta↔rol y
  unicidad por (ficha, faceta). `transaction.atomic()`; `@audit`.
- [x] **2.4** Crear los ViewSets delgados en `backend/apps/directory/views.py` (CRUD acotado de ficha +
  acciones `@action` `block`/`unblock`/`deactivate`/`reactivate`/`link-user`; listados excluyen
  INACTIVO por defecto, con `?include_inactive`) y `backend/apps/credit/views.py` (crear/editar términos).
  Delegan en services. Registrar el módulo `directory` (constante `MODULE_DIRECTORY = "directory"`,
  acciones `read`/`create`/`update`) en `apps/authz/catalog.py` y proteger con la permission class de F2.
- [x] **2.5** Registrar rutas en `backend/apps/directory/urls.py` y `backend/apps/credit/urls.py` con
  los prefijos `/directory` y `/credit`. Verificar que todos los errores salen por el contrato uniforme.

## Fase 3: Integración de Datos (Frontend — Hooks)

- [x] **3.1** Crear los hooks en `frontend/src/features/directory/hooks/`: `useFichas` (`useList` con
  filtros rol/estado), `useFichaMutation` (`useCreate`/`useUpdate`), `useFichaStatus`
  (`useCustomMutation` para transiciones), `useCreditTerms`. NO montar TanStack Query en paralelo.
- [x] **3.2** Validar en los hooks que la respuesta cumple el schema Zod generado en Fase 0 antes de
  exponer los datos; lanzar error descriptivo si no coincide.

## Fase 4: Componentes y Páginas (Frontend — UI)

- [x] **4.1** Crear el contenedor `DirectoryList.tsx` en `frontend/src/features/directory/components/`:
  consume `useFichas`; filtros por rol y estado (excluye INACTIVO por defecto); cubre estados
  vacío/carga/error/éxito.
- [x] **4.2** Crear `FichaForm.tsx` (contenedor) + `FichaFormFields.tsx` y `CreditTermsSubform.tsx`
  (presentacionales): roles múltiples, identificación con validación de formato Zod (dígito verificador
  en backend), contacto; el sub-formulario solo ofrece la faceta cuyo rol tiene la ficha. React Hook
  Form + `zodResolver`. Cero hex literales (tokens del theme); áreas táctiles ≥44px; inputs ≥16px iOS;
  `FieldError` compartido para mapear errores del backend a los campos.
- [x] **4.3** Implementar las acciones de estado (bloquear/reactivar/dar de baja) vía `useFichaStatus`,
  visibles según perfil.
- [x] **4.4** Actualizar el contrato público `frontend/src/features/directory/index.ts` con los exports
  explícitos de componentes, hooks y tipos.
- [x] **4.5** Crear las páginas dumb `DirectoryPage.tsx` y `FichaFormPage.tsx` en `frontend/src/pages/`
  y registrar los resources/rutas en la config de Refine (`<Refine resources={[...]}>`) con protección
  por perfil (`accessControlProvider`) y `lazy(() => import(...))`.

## Fase 5: Seguridad y DevSecOps

- [x] **5.1** Backend — `uv run ruff check .` + `uv run ruff format --check .` y `uv run mypy .`
  (strict) limpios en `apps/directory/`, `apps/credit/` y `apps/common/validations.py`.
- [x] **5.2** Backend — `uv run bandit -c pyproject.toml -r apps config`. Corregir o documentar toda
  alerta MEDIUM+. Verificar que la validación de identificación es efectiva **server-side**.
- [x] **5.3** Frontend — `npm run lint` y `npm run typecheck` limpios en `src/features/directory/`.
- [x] **5.4** Global — Verificar que no hay secretos en el código y que las acciones del Directorio
  respetan los permisos por perfil (F2).
- [x] **5.5** Dependencias — Sin nuevas dependencias previstas; si se añadiera alguna, `uv run pip-audit`
  (Python) y `npm audit --audit-level=moderate` (Node) sin CVEs conocidos.
- [x] **5.6** UI — Validar contraste WCAG AA en los nuevos componentes en modo claro y oscuro.

## Fase 6: Pruebas y Validación Final

- [x] **6.1** Backend — Tests de `apps/common/validations.py` en `apps/common/tests/`: casos válidos e
  inválidos de cédula, RUC (natural, sociedad, público) y pasaporte (funciones puras; cobertura alta).
- [x] **6.2** Backend — Tests en `backend/apps/directory/tests/` y `backend/apps/credit/tests/`
  cubriendo TODOS los Scenarios: identificación válida/inválida(400)/duplicada(409); roles
  múltiples/sin rol(400); email inválido(400); estados block/unblock/deactivate/reactivate y
  exclusión de INACTIVO; vínculo usuario y duplicado(409); términos por faceta; faceta duplicada(409);
  integridad faceta↔rol(400); 401/403 sin autorización. Ejecutar con `--cov` (≥80% global).
- [x] **6.3** Frontend — Tests (Vitest + RTL) en `frontend/src/features/directory/components/` del
  formulario de ficha y del sub-formulario de crédito por faceta: flujo de éxito, feedback de error,
  estados vacío/carga/error y accesibilidad básica (roles ARIA, teclado).
- [x] **6.4** E2E — `npx playwright test` incluyendo WebKit (Safari/iOS): flujo principal del
  Directorio e inputs de identificación.
- [x] **6.5** Definition of done — Todos los gates en verde localmente: `ruff`, `mypy`, `bandit`,
  `pip-audit`, `pytest`; `eslint`, `tsc`, `npm audit`, `vitest`, `playwright`. Confirmar antes de
  declarar el change completo.
