# Tareas: add-user-management

> Orden obligatorio del `config.yaml`: Contrato (OpenAPI) → Migraciones Django → Backend (services) → Frontend → Seguridad → Pruebas. Cada tarea nombra el archivo/módulo exacto. Definition of done global: todos los gates del pipeline en verde localmente antes de declarar el change completo.

## A. Contrato y modelo (OpenAPI + datos)
- [x] A.1 Añadir `must_change_password` (boolean, default `false`, not null) al modelo `accounts.User` con `help_text`.
- [x] A.2 Definir serializers de administración de usuarios en `apps/accounts/serializers.py` (`UserAdminWrite/Read`, `ResetPasswordWrite/Read`), con `help_text` por campo.
- [x] A.3 Definir serializers de administración de perfiles en `apps/authz/serializers.py` (`ProfileAdminWrite`: editar permisos; baja con validación de usuarios asignados). Reutilizar el `AssignProfileWrite` de F2 para el cambio de perfil.
- [x] A.4 Anotar los endpoints con `drf-spectacular` y regenerar `schema.yml`.

## B. Migraciones
- [x] B.1 `makemigrations accounts` (campo `must_change_password`); confirmar reversibilidad (`AddField` estándar).
- [x] B.2 `migrate`, verificar arranque limpio y probar el reverse (`migrate accounts <anterior>` → re-aplicar).

## C. Backend (services + vistas)
- [x] C.1 Implementar en `apps/accounts/services.py`: `create_user`, `update_user`, `reset_password` (temporal + flag + blacklist), `deactivate_user`/`reactivate_user` (blacklist), todo bajo `@audit` y `transaction.atomic()`.
- [x] C.2 Implementar en `apps/authz/services.py`: **extender `assign_profile` de F2** para sincronizar `role` + blacklist de refresh; `update_profile_permissions` y `deactivate_profile` (soft delete clase 2 con validación de usuarios asignados). Todo bajo `@audit` y `transaction.atomic()`.
- [x] C.3 Implementar las vistas admin delgadas en `apps/accounts/views.py` y `apps/authz/views.py`, protegidas por la permission class de Jefe (F2); registrar rutas en los `urls.py`.
- [x] C.4 Implementar la permission class / middleware de cambio forzado que bloquea todo (403 `{detail}`) salvo `change-password`, `me` y `logout` cuando `must_change_password` está activo.
- [x] C.5 Verificar que `POST /auth/change-password` (F1) desactiva el flag y que `GET /auth/me` lo expone.
- [x] C.6 Verificar que todos los errores salen por el contrato uniforme (`{detail}` para 401/403/404; `{campo: [mensajes]}` para 400).

## D. Frontend
- [x] D.1 Regenerar tipos + Zod desde `schema.yml` (`npm run codegen`).
- [x] D.2 Construir la consola de usuarios en `src/features/users/` (hooks `useUsersList`/`useUserMutations`/`useUserAdminActions`, `UsersAdminConsole`, `UserForm`, `ResetPasswordDialog`), visible solo para Jefe (gating de F2).
- [x] D.3 Construir la administración de perfiles en `src/features/profiles/` (`ProfilesAdminConsole`, `PermissionMatrix`, hooks), visible solo para Jefe.
- [x] D.4 Implementar `ForcePasswordChangeGuard` en `src/features/auth/`: si `me.must_change_password`, redirigir a `/auth/change-password` y bloquear navegación hasta completarlo.
- [x] D.5 Estados vacío/carga/error/éxito, tokens del theme, `FieldError` compartido, inputs ≥16px iOS, áreas táctiles ≥44px.

## E. Seguridad
- [x] E.1 Verificar server-side que solo el perfil Jefe accede a la administración (usuarios y perfiles) → 403 en caso contrario.
- [x] E.2 Verificar que reset, desactivación y cambio de perfil invalidan los refresh (blacklist) de forma efectiva.
- [x] E.3 Verificar que el bloqueo por cambio forzado no puede saltarse (ningún endpoint de negocio responde con el flag activo).
- [x] E.4 Verificar que los eventos de seguridad quedan auditados con ejecutor, afectado, tipo y fecha/hora, y que el fallo de auditoría revierte la operación.
- [x] E.5 Verificar que la contraseña temporal no se loggea en claro y que no hay secretos en el código.

## F. Pruebas (gate)
- [x] F.1 Tests de backend en `apps/accounts/tests/` y `apps/authz/tests/` cubriendo todos los Scenarios (crear usuario; 403 sin autorización; identificador duplicado → 400; cambio de perfil + invalidación; perfil inexistente → 404; reset + temporal + flag + blacklist; temporal inválida → 400; desactivar/reactivar; auditoría y rollback por fallo de auditoría; cambio forzado bloquea operaciones → 403 y se desactiva al cambiar; editar perfil; baja de perfil sin usuarios; baja de perfil en uso → 409).
- [x] F.2 Tests de frontend (Vitest + RTL) de las consolas de administración y del `ForcePasswordChangeGuard` (flujo de primer acceso), incluyendo estados vacío/carga/error.
- [x] F.3 Ejecutar y dejar en verde: `ruff`, `mypy --strict`, `bandit`, `pip-audit`, `pytest` (cobertura ≥80%); `eslint`, `tsc`, `npm audit`, `vitest`; `Trivy` sobre la imagen del backend en el pipeline de deploy (sin CVEs conocidos). Confirmar antes de declarar el change completo.
