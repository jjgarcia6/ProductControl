# Propuesta: add-user-management

**Capability:** `user-management` (inicia) · modifica `auth` y `access-control` · **Depende de:** F1, F2 · **Desbloquea:** — (consola operativa de identidad; no bloquea módulos de negocio, que se sirven con usuarios sembrados).
**Fuente de verdad:** `openspec/config.yaml`. Ante conflicto, manda el `config.yaml`.
**Requerimientos:** 2.5 (roles). El ciclo de vida de identidad es un **gap** respecto a v1.1.

## 1. El Problema o Necesidad de Negocio

F1 entregó autenticación y F2 el motor de autorización por perfil, pero **no existe forma de operar
la identidad sin tocar la base de datos a mano**: no se pueden dar de alta usuarios, cambiarles el
perfil, resetear una contraseña olvidada ni desactivar a quien deja la empresa. Sin esta consola, el
go-live exige sembrar usuarios por migración o shell — inviable para el Jefe, que es quien
administra. Este change cierra el hueco de **ciclo de vida de identidad** que los requerimientos
v1.1 no cubrían, y completa la administración de perfiles que F2 dejó deliberadamente en
modelo + mecanismo + seed.

## 2. Alcance Crítico

**Decisión de alcance:** un solo change cohesivo — es la misma consola de administración. Toca tres
capabilities porque administrar identidad cruza las tres:

- **`user-management`** (inicia): CRUD de usuarios, reset, desactivación, auditoría de eventos de seguridad.
- **`auth`** (modifica): flag de cambio forzado de contraseña en el primer acceso.
- **`access-control`** (modifica): administración de perfiles (CRUD + configuración de permisos) que completa lo iniciado en F2.

### In-Scope (Lo que se va a construir)

- **CRUD de usuarios** (crear, editar, desactivar, reactivar), restringido al perfil Jefe, con el `role` nominal sincronizado al perfil. La creación fija el perfil inline.
- **Extensión de la asignación de perfil de F2** (`POST /authz/users/{id}/assign-profile`): además de cambiar el perfil, ahora **sincroniza el `role`** e **invalida (blacklist) los refresh** vigentes para que los permisos nuevos surtan efecto sin esperar a que expire el token. Es un retoque de comportamiento sobre F2, no un endpoint nuevo.
- **Reset administrativo** de contraseña: temporal (definida por el admin o generada por el sistema) + activación del flag de cambio forzado + blacklist de refresh.
- **Contraseña temporal con cambio forzado** en el primer acceso (flag `must_change_password`).
- **Desactivación que invalida (blacklist) el refresh** del usuario; reactivación.
- **Administración de perfiles** (editar permisos por (módulo, acción) + flags; baja con soft delete clase 2 validando que no haya usuarios asignados), completando F2.
- **Auditoría de eventos de seguridad** (reset, desactivación/reactivación, cambio de perfil) usando el mecanismo `@audit` del bootstrap.
- **Nuevos contratos de datos:** serializers DRF de administración de usuarios y perfiles (anotados con `drf-spectacular`) → tipos TS + Zod **generados** del OpenAPI.

### Out-of-Scope (Prohibiciones Estrictas)

- **Backend:** Toda persistencia MUST ser PostgreSQL vía Django ORM. Sin SQL raw.
- **Backend:** Las operaciones multi-tabla (reset = set password + flag + blacklist) MUST usar `transaction.atomic()` con rollback total.
- **Backend:** `Profile` MUST usar soft delete clase 2 (catálogo). `accounts.User` NO es catálogo: la baja es desactivación (`is_active=False`), no `deleted_at`.
- **Frontend:** Cero hex literales; todo estilo vía tokens del theme (shadcn/Tailwind) con modo claro y oscuro.
- **Seguridad:** Credenciales y contraseñas temporales MUST NOT almacenarse en el código ni loggearse; gestión vía `.env` / GCP Secret Manager.
- **Calidad / YAGNI fuera de alcance:**
  - Cambio de contraseña propio del usuario autenticado → ya está en F1.
  - Recuperación self-service por email → diferida a post-F25 (depende de la infraestructura de email de F22).
  - Vínculo User ↔ Ficha de Directorio → se modela en F4.
  - MFA, SSO, invitaciones por correo, jerarquía de administradores → YAGNI.

## 3. Evaluación de Impacto

### Modelo de Datos (PostgreSQL)

- **`accounts.User`**: añadir `must_change_password` (`BooleanField`, default `False`, not null). Migración `AddField` sobre `accounts`, reversible.
- **No se crean tablas nuevas.** La administración opera sobre `User` (F1) y `Profile` (F2). Los eventos de seguridad se registran con el modelo de log de auditoría del bootstrap.
- Sin nuevos índices ni constraints; sin impacto en unicidad parcial. El `username`/identificador único ya existe en `User` (F1).

### Lógica de Negocio y API

- **Endpoints admin de usuarios** en `apps/accounts` (crear, editar, desactivar, reactivar, reset) como acciones explícitas — NO CRUD genérico ciego.
- **Endpoints admin de perfiles** en `apps/authz` (editar permisos, dar de baja), completando los de lectura/creación de F2.
- **Asignación de perfil:** se reutiliza `POST /authz/users/{id}/assign-profile` de F2, extendido para sincronizar `role` + blacklist. No se crea endpoint nuevo de cambio de perfil.
- **Lógica en `services/`**: reset, desactivación viven en `apps/accounts/services.py`; la asignación de perfil (extendida) y la administración de perfiles en `apps/authz/services.py`. ViewSets delgados.
- **Autorización por perfil** (permission classes de F2): todos exigen un perfil con permiso de administración (Jefe); 403 `{detail}` al denegar. La autorización se resuelve por el **perfil**, nunca por el `role` nominal.
- **No se toca** FIFO, costeo, merma, saldos CxC/CxP, período ni Kardex.

### Flujo del Usuario (UI)

- **Consola de administración** (recurso protegido, visible solo para Jefe vía `accessControlProvider`): listado + formularios de usuarios; listado + formularios de perfiles con su matriz de permisos.
- **Flujo de primer acceso**: si `GET /auth/me` indica `must_change_password`, el cliente redirige a la pantalla de cambio de contraseña y **bloquea la navegación** hasta completarlo.
- Estados vacío/carga/error/éxito obligatorios; tokens del theme; `FieldError` compartido; inputs ≥16px iOS; áreas táctiles ≥44px.
- Roles afectados: **Jefe** (único actor de administración). Los demás perfiles no ven la consola.

### Cadena de Trazabilidad

**No se altera la cadena de trazabilidad** (Ingreso → Kardex → Entrega → Cobro / Ingreso → CxP → Pago). F3 opera exclusivamente sobre identidad y autorización; no genera ni modifica documentos de negocio ni movimientos de Kardex.

### Relación con F10 (audit-rules)

F3 audita **eventos de seguridad** con el mecanismo `@audit` ya disponible desde el bootstrap. No depende de F10, que formaliza la auditoría de **correcciones de documentos** (peso/costo) — alcance distinto. No se reordenan fases.

## 4. Riesgos y Rollback

### Riesgo Principal

Que el **bloqueo por cambio forzado** (`must_change_password`) se pueda **saltar**: si la permission
class global no cubre todos los endpoints de negocio, un usuario con contraseña temporal podría
operar sin cambiarla. Riesgo secundario: que el reset o la desactivación **no invaliden
efectivamente los refresh** (blacklist incompleto), dejando sesiones vivas con credenciales que
debían quedar revocadas.

### Criterio de Aborto

Condición técnica verificable: si las permission classes por perfil de F2 no están disponibles
(`apps/authz/permissions.py` ausente o `Profile` sin migrar), **abortar** — F3 no puede restringir la
administración al Jefe sin el motor de autorización de F2. Asimismo, si las pruebas de seguridad del
bloqueo por cambio forzado o de la invalidación de refresh fallan tras 2 intentos de corrección,
revertir el change.

### Plan de Rollback

- La migración `AddField must_change_password` es estándar y **reversible** (`migrate accounts <anterior>` elimina la columna sin pérdida de datos de negocio).
- No requiere data migration de limpieza ni recálculo de saldos (no toca Kardex ni CxC/CxP).
- Revertir el código de los endpoints admin no deja datos huérfanos: `User` y `Profile` preexisten a F3.

### Verificación de invariantes

No toca Kardex, período, costeo ni documentos. Respeta: solo el Jefe gestiona identidad (vía
permission classes de F2); SimpleJWT fijo y blacklist (F1); contrato de errores uniforme; soft
delete clase 2 para perfiles; `User` se desactiva (no se borra).
