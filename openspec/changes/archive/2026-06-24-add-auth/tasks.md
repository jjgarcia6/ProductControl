# Tareas: add-auth
<!-- Orden REQUIRED: Contrato → Migraciones → Backend → Frontend → Seguridad → Pruebas. -->

## Fase 0: Contrato y Sincronización Inicial
<!-- Nota de orden: el custom user model es precondición del contrato OpenAPI (los serializers lo referencian),
     por eso 0.1 crea la app/modelo antes de los serializers. El modelo precede al serializer dentro de esta fase. -->

- [x] **0.1** Backend — Crear la app `apps/accounts/` y definir `User(AbstractUser)` con `role` (`Role.TextChoices`: JEFE/SUPERVISOR/RUTA/USUARIO, default USUARIO) en `apps/accounts/models.py`. NO hereda `SoftDeleteMixin` (no es catálogo).
- [x] **0.2** Backend — Configurar `AUTH_USER_MODEL = "accounts.User"` y habilitar `accounts` + `rest_framework_simplejwt.token_blacklist` en `INSTALLED_APPS` en `config/settings/base.py`. Configurar `SIMPLE_JWT` (access 15 min, refresh 7 d, rotación + blacklist tras rotación).
- [x] **0.3** Backend — Definir serializers en `apps/accounts/serializers.py` (`LoginSerializer`, `UserIdentitySerializer`, `ChangePasswordSerializer`) con `help_text=...` en cada campo. Separar entrada (write) de salida (read).
- [x] **0.4** Backend — Anotar los endpoints con `drf-spectacular` (cuerpo real: access en body, refresh en cookie) y regenerar `schema.yml`. Verificar que el OpenAPI expone los serializers y sus `help_text`.
- [x] **0.5** Frontend — Regenerar tipos/Zod desde `schema.yml` en `frontend/src/features/auth/types/` (`npm run codegen`). MUST NOT escribir tipos ni schemas a mano; derivar con `z.infer<>`.
- [x] **0.6** Global — Actualizar `backend/.env.example` (`JWT_SIGNING_KEY`, `CORS_ALLOWED_ORIGINS`, `AUTH_COOKIE_DOMAIN`, `AUTH_COOKIE_SAMESITE`, `LOGIN_RATELIMIT`) y `frontend/.env.example` (`VITE_API_BASE_URL`).

## Fase 1: Modelo de Datos y Migraciones

- [x] **1.1** Generar migración: `python manage.py makemigrations accounts`. Verificar que es la **primera** migración del proyecto con `python manage.py showmigrations` (criterio de aborto: no debe existir migración aplicada con el `User` por defecto de Django).
- [x] **1.2** Aplicar migración: `python manage.py migrate`. Verificar que `accounts_user` y las tablas de `token_blacklist` se crearon y que el arranque es limpio.
- [x] **1.3** Probar el reverse: `python manage.py migrate accounts zero`. Verificar reversión sin errores. Luego re-aplicar: `python manage.py migrate`.

## Fase 2: Lógica de Negocio y API (Backend)

- [x] **2.1** Implementar `apps/accounts/services.py`: `issue_tokens` (access en body + cookie `httpOnly`), `rotate_refresh` (rota + blacklist del anterior), `revoke_refresh` (logout: blacklist del refresh de la cookie + limpia cookie), `revoke_all_refresh(user)` (helper reutilizable: blacklist de TODOS los outstanding refresh del usuario — F3 lo reusa) y `change_own_password` (valida actual, aplica política y **delega** la invalidación en `revoke_all_refresh(user)`, sin reimplementarla). Operaciones multi-paso bajo `transaction.atomic()`. Sin capturar `Exception` genérico.
- [x] **2.2** Implementar las vistas delgadas en `apps/accounts/views.py` (`login`, `refresh`, `logout`, `me`, `change-password`) delegando en services; cada una usa los serializers de Fase 0.
- [x] **2.3** Registrar rutas en `apps/accounts/urls.py` con prefijo `/auth` e incluirlas en `config/urls.py`.
- [x] **2.4** Verificar que todos los errores salen por el exception handler del contrato uniforme (`{campo: [mensajes]}` en 400 / `{detail}` en 401/429).

## Fase 3: Integración de Datos (Frontend — Hooks)

- [x] **3.1** Implementar el store de sesión en `frontend/src/features/auth/store/sessionStore.ts` (Zustand): access **en memoria**, sin `localStorage`/persistencia.
- [x] **3.2** Implementar el interceptor HTTP en `frontend/src/features/auth/api/httpClient.ts`: añade `Authorization` con el access en memoria; ante 401 intenta `refresh` (`withCredentials`) una vez y reintenta; si falla, limpia sesión y redirige a login.
- [x] **3.3** Implementar el `authProvider` de Refine en `frontend/src/features/auth/providers/authProvider.ts` (`login`, `logout`, `check` con refresh silencioso al cargar la app, `getIdentity`, `onError`).
- [x] **3.4** Implementar el hook `useChangePassword` en `frontend/src/features/auth/hooks/useChangePassword.ts` (`useCustomMutation`); validar la respuesta contra el schema Zod generado en Fase 0.

## Fase 4: Componentes y Páginas (Frontend — UI)

- [x] **4.1** Crear `LoginContainer.tsx` en `features/auth/components/` (orquesta `authProvider.login` + navegación; cubre vacío/carga/error/éxito).
- [x] **4.2** Crear los presentacionales `LoginForm.tsx` y `ChangePasswordForm.tsx` en `features/auth/components/`: React Hook Form + `zodResolver`; todo color desde tokens del theme (cero hex); áreas táctiles ≥44px; inputs ≥16px en iOS; errores de campo con `FieldError` compartido.
- [x] **4.3** Actualizar `frontend/src/features/auth/index.ts` con las exportaciones explícitas (authProvider, contenedor, hook, store, tipos).
- [x] **4.4** Crear las dumb pages `LoginPage.tsx` y `ChangePasswordPage.tsx` en `frontend/src/pages/` (solo importan y renderizan el contenedor; sin estado ni fetch directos).
- [x] **4.5** Registrar los recursos/rutas en la config de Refine (`/login` pública, `/account/change-password` protegida) con `lazy(() => import(...))`.

## Fase 5: Seguridad y DevSecOps
<!-- No negociable. -->

- [x] **5.1** Backend — `ruff check apps/accounts/` y `mypy --strict apps/accounts/`. Corregir todos los errores.
- [x] **5.2** Backend — `bandit -r apps/accounts/`. Corregir o documentar toda alerta MEDIUM o superior.
- [x] **5.3** Backend — Activar `django-ratelimit` en `login`; configurar validadores de contraseña de Django y verificar mensajes en español (`LANGUAGE_CODE`).
- [x] **5.4** Backend — Configurar atributos de cookie de refresh (`httpOnly`, `Secure`, `SameSite`, `Path=/auth`), `CORS_ALLOW_CREDENTIALS=True` y origen del frontend. Si el despliegue queda cross-site (`SameSite=None`), añadir protección CSRF double-submit en `refresh`/`logout`. **Registrar la decisión en README/ADR.**
- [x] **5.5** Frontend — `eslint frontend/src/features/auth/` y `tsc --noEmit`. Corregir todos los errores.
- [x] **5.6** Global — Verificar que no hay secretos en el código (clave de firma JWT, credenciales, connection strings).
- [x] **5.7** Dependencias — `pip-audit` (Python), `npm audit` (Node) y `trivy fs .` / imagen. No mergear con CVEs conocidos.
- [x] **5.8** UI — Validar contraste WCAG AA en las pantallas Login y Cambio de contraseña en modo claro y oscuro; estados hover/active/focus/disabled visibles.

## Fase 6: Pruebas y Validación Final
<!-- Gate de cobertura: ≥80% global. No hay cálculo financiero en esta fase. -->

- [x] **6.1** Backend — Pruebas en `apps/accounts/tests/` cubriendo TODOS los Scenarios del spec: login válido/inválido/inactivo; refresh válido/revocado/ausente; logout + refresh tras logout; `me` con/sin token; cambio de contraseña correcto/actual-incorrecta/política; rol en identidad; rate limit. Ejecutar `pytest apps/accounts/tests/ -v --cov` (≥80%).
- [x] **6.2** Frontend — Pruebas (Vitest + RTL) en `frontend/src/features/auth/`: flujo de login (éxito + error de credenciales), interceptor de refresh, estados vacío/carga/error, accesibilidad básica (roles ARIA, teclado). Ejecutar `vitest run`.
- [x] **6.3** E2E / cross-browser — Playwright incluyendo WebKit (Safari/iOS): smoke del login y validación de inputs ≥16px sin zoom.
- [x] **6.4** Integración — Verificar: migración reversible (reverse + migrate sin pérdida); sin operaciones bloqueantes que choquen con el timeout de Cloud Run; sin errores de consola ni warnings de React; el access NO persiste en `localStorage`.
- [x] **6.5** Definition of done — Todos los gates del pipeline (backend y frontend) en verde, ejecutados localmente, antes de declarar el cambio completo.
