# Change: add-user-management — Fase 3

**Capability:** `user-management` (inicia) · modifica `auth` y `access-control` · **Depende de:** F1, F2 · **Desbloquea:** — (consola operativa de identidad; no bloquea módulos de negocio, que se sirven con usuarios sembrados)
**Fuente de verdad:** `openspec/config.yaml`. Ante conflicto, manda el `config.yaml`.
**Requerimientos:** 2.5 (roles). El ciclo de vida de identidad es un **gap** respecto a v1.1.

> **Cómo usar este archivo.** Consolida los cuatro artefactos del change. Cada sección de primer nivel mapea a un archivo dentro de `openspec/changes/add-user-management/`:
> - `## 1) PROPOSAL` → `proposal.md`
> - `## 2) SPECS` → tres deltas: `specs/user-management/spec.md`, `specs/auth/spec.md`, `specs/access-control/spec.md`
> - `## 3) DESIGN` → `design.md`
> - `## 4) TASKS` → `tasks.md`
>
> Requirements en RFC 2119 (MUST/MUST NOT/SHALL); Scenarios en español (DADO/CUANDO/ENTONCES). Código e identificadores en inglés; documentación en español.

---

## 1) PROPOSAL → proposal.md

### 1. El Problema o Necesidad de Negocio

F1 entregó autenticación y F2 el motor de autorización por perfil, pero **no existe forma de operar
la identidad sin tocar la base de datos a mano**: no se pueden dar de alta usuarios, cambiarles el
perfil, resetear una contraseña olvidada ni desactivar a quien deja la empresa. Sin esta consola, el
go-live exige sembrar usuarios por migración o shell — inviable para el Jefe, que es quien
administra. Este change cierra el hueco de **ciclo de vida de identidad** que los requerimientos
v1.1 no cubrían, y completa la administración de perfiles que F2 dejó deliberadamente en
modelo + mecanismo + seed.

### 2. Alcance Crítico

**Decisión de alcance:** un solo change cohesivo — es la misma consola de administración. Toca tres
capabilities porque administrar identidad cruza las tres:

- **`user-management`** (inicia): CRUD de usuarios, reset, desactivación, auditoría de eventos de seguridad.
- **`auth`** (modifica): flag de cambio forzado de contraseña en el primer acceso.
- **`access-control`** (modifica): administración de perfiles (CRUD + configuración de permisos) que completa lo iniciado en F2.

#### In-Scope (Lo que se va a construir)

- **CRUD de usuarios** (crear, editar, desactivar, reactivar), restringido al perfil Jefe, con el `role` nominal sincronizado al perfil. La creación fija el perfil inline.
- **Extensión de la asignación de perfil de F2** (`POST /authz/users/{id}/assign-profile`): además de cambiar el perfil, ahora **sincroniza el `role`** e **invalida (blacklist) los refresh** vigentes para que los permisos nuevos surtan efecto sin esperar a que expire el token. Es un retoque de comportamiento sobre F2, no un endpoint nuevo.
- **Reset administrativo** de contraseña: temporal (definida por el admin o generada por el sistema) + activación del flag de cambio forzado + blacklist de refresh.
- **Contraseña temporal con cambio forzado** en el primer acceso (flag `must_change_password`).
- **Desactivación que invalida (blacklist) el refresh** del usuario; reactivación.
- **Administración de perfiles** (editar permisos por (módulo, acción) + flags; baja con soft delete clase 2 validando que no haya usuarios asignados), completando F2.
- **Auditoría de eventos de seguridad** (reset, desactivación/reactivación, cambio de perfil) usando el mecanismo `@audit` del bootstrap.
- **Nuevos contratos de datos:** serializers DRF de administración de usuarios y perfiles (anotados con `drf-spectacular`) → tipos TS + Zod **generados** del OpenAPI.

#### Out-of-Scope (Prohibiciones Estrictas)

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

### 3. Evaluación de Impacto

#### Modelo de Datos (PostgreSQL)

- **`accounts.User`**: añadir `must_change_password` (`BooleanField`, default `False`, not null). Migración `AddField` sobre `accounts`, reversible.
- **No se crean tablas nuevas.** La administración opera sobre `User` (F1) y `Profile` (F2). Los eventos de seguridad se registran con el modelo de log de auditoría del bootstrap.
- Sin nuevos índices ni constraints; sin impacto en unicidad parcial. El `username`/identificador único ya existe en `User` (F1).

#### Lógica de Negocio y API

- **Endpoints admin de usuarios** en `apps/accounts` (crear, editar, desactivar, reactivar, reset) como acciones explícitas — NO CRUD genérico ciego.
- **Endpoints admin de perfiles** en `apps/authz` (editar permisos, dar de baja), completando los de lectura/creación de F2.
- **Asignación de perfil:** se reutiliza `POST /authz/users/{id}/assign-profile` de F2, extendido para sincronizar `role` + blacklist. No se crea endpoint nuevo de cambio de perfil.
- **Lógica en `services/`**: reset, desactivación viven en `apps/accounts/services.py`; la asignación de perfil (extendida) y la administración de perfiles en `apps/authz/services.py`. ViewSets delgados.
- **Autorización por perfil** (permission classes de F2): todos exigen un perfil con permiso de administración (Jefe); 403 `{detail}` al denegar. La autorización se resuelve por el **perfil**, nunca por el `role` nominal.
- **No se toca** FIFO, costeo, merma, saldos CxC/CxP, período ni Kardex.

#### Flujo del Usuario (UI)

- **Consola de administración** (recurso protegido, visible solo para Jefe vía `accessControlProvider`): listado + formularios de usuarios; listado + formularios de perfiles con su matriz de permisos.
- **Flujo de primer acceso**: si `GET /auth/me` indica `must_change_password`, el cliente redirige a la pantalla de cambio de contraseña y **bloquea la navegación** hasta completarlo.
- Estados vacío/carga/error/éxito obligatorios; tokens del theme; `FieldError` compartido; inputs ≥16px iOS; áreas táctiles ≥44px.
- Roles afectados: **Jefe** (único actor de administración). Los demás perfiles no ven la consola.

#### Cadena de Trazabilidad

**No se altera la cadena de trazabilidad** (Ingreso → Kardex → Entrega → Cobro / Ingreso → CxP → Pago). F3 opera exclusivamente sobre identidad y autorización; no genera ni modifica documentos de negocio ni movimientos de Kardex.

#### Relación con F10 (audit-rules)

F3 audita **eventos de seguridad** con el mecanismo `@audit` ya disponible desde el bootstrap. No depende de F10, que formaliza la auditoría de **correcciones de documentos** (peso/costo) — alcance distinto. No se reordenan fases.

### 4. Riesgos y Rollback

#### Riesgo Principal

Que el **bloqueo por cambio forzado** (`must_change_password`) se pueda **saltar**: si la permission
class global no cubre todos los endpoints de negocio, un usuario con contraseña temporal podría
operar sin cambiarla. Riesgo secundario: que el reset o la desactivación **no invaliden
efectivamente los refresh** (blacklist incompleto), dejando sesiones vivas con credenciales que
debían quedar revocadas.

#### Criterio de Aborto

Condición técnica verificable: si las permission classes por perfil de F2 no están disponibles
(`apps/authz/permissions.py` ausente o `Profile` sin migrar), **abortar** — F3 no puede restringir la
administración al Jefe sin el motor de autorización de F2. Asimismo, si las pruebas de seguridad del
bloqueo por cambio forzado o de la invalidación de refresh fallan tras 2 intentos de corrección,
revertir el change.

#### Plan de Rollback

- La migración `AddField must_change_password` es estándar y **reversible** (`migrate accounts <anterior>` elimina la columna sin pérdida de datos de negocio).
- No requiere data migration de limpieza ni recálculo de saldos (no toca Kardex ni CxC/CxP).
- Revertir el código de los endpoints admin no deja datos huérfanos: `User` y `Profile` preexisten a F3.

### Verificación de invariantes

No toca Kardex, período, costeo ni documentos. Respeta: solo el Jefe gestiona identidad (vía
permission classes de F2); SimpleJWT fijo y blacklist (F1); contrato de errores uniforme; soft
delete clase 2 para perfiles; `User` se desactiva (no se borra).

---

## 2) SPECS

### 2.1 → specs/user-management/spec.md

# Delta para la capability `user-management`

## ADDED Requirements

### Requirement: Gestión de usuarios
Un usuario cuyo perfil lo autorice (Jefe) MUST poder crear, editar, desactivar y reactivar usuarios. La creación MUST asignar un perfil y dejar el `role` nominal sincronizado. Quien no esté autorizado MUST recibir 403. Los errores de validación MUST seguir el contrato uniforme `{campo: [mensajes]}`.

#### Scenario: Jefe crea un usuario con datos válidos
- DADO un usuario con perfil Jefe en la consola de administración
- Y que los datos (identificador único, perfil, datos básicos) cumplen el Diccionario de Datos
- CUANDO el Frontend envía la solicitud a `POST /auth/users`
- ENTONCES el Backend MUST procesarla dentro de `transaction.atomic()` y persistir el usuario con su perfil y su `role` sincronizado
- Y el Backend MUST registrar la operación en `audit_log` con acción `CREATE`
- Y el usuario MUST quedar disponible para autenticarse
- Y el Frontend MUST mostrar una notificación de éxito usando tokens del theme

#### Scenario: Usuario sin autorización intenta crear un usuario
- DADO un usuario cuyo perfil no permite administrar usuarios
- CUANDO intenta acceder a `POST /auth/users`
- ENTONCES el Backend MUST retornar HTTP `403 Forbidden` con `{detail}` genérico en español
- Y el Backend MUST NOT crear el usuario
- Y el Frontend MUST mostrar el mensaje de acceso denegado sin exponer detalles internos

#### Scenario: Jefe crea un usuario con identificador duplicado
- DADO que ya existe un usuario activo con ese identificador
- CUANDO el Frontend intenta crear otro con el mismo identificador en `POST /auth/users`
- ENTONCES el Backend MUST NOT crear el usuario
- Y el Backend MUST retornar HTTP `400 Bad Request` con `{campo: [mensajes]}` en el campo del identificador
- Y el Frontend MUST mostrar el error en el campo correspondiente del formulario

> **Nota de alcance:** el *cambio de perfil de un usuario* no se especifica aquí. Vive en el delta de
> `access-control` como `## MODIFIED Requirements` sobre la requirement de F2 *"Asignación de perfil a
> usuario"* (sección 2.3), extendida con sincronización de `role` + blacklist. Se evita duplicar la
> misma regla en dos capabilities (DRY/KISS).

### Requirement: Reset administrativo de contraseña
El administrador (Jefe) MUST poder restablecer la contraseña de un usuario sin conocer la anterior. El reset MUST fijar una contraseña temporal (definida por el administrador o generada por el sistema), activar el flag `must_change_password` e invalidar (blacklist) los refresh vigentes del usuario.

#### Scenario: Jefe resetea la contraseña de un usuario
- DADO un usuario existente y un administrador con perfil Jefe
- CUANDO el Frontend envía la solicitud a `POST /auth/users/{id}/reset-password`
- ENTONCES el Backend MUST procesarla dentro de `transaction.atomic()`, fijar la contraseña temporal y activar `must_change_password`
- Y el Backend MUST invalidar (blacklist) los refresh vigentes del usuario
- Y el Backend MUST registrar la operación en `audit_log` con acción `UPDATE`
- Y el Backend MUST NOT loggear la contraseña temporal en claro
- Y el Frontend MUST mostrar la contraseña temporal una sola vez usando tokens del theme

#### Scenario: Reset con contraseña temporal que no cumple la política
- DADO que el administrador define una contraseña temporal que no cumple las reglas de complejidad
- CUANDO el Frontend envía la solicitud a `POST /auth/users/{id}/reset-password`
- ENTONCES el Backend MUST NOT cambiar la contraseña
- Y el Backend MUST retornar HTTP `400 Bad Request` con `{campo: [mensajes]}` en el campo de la contraseña
- Y el Frontend MUST mostrar el error en el campo correspondiente

#### Scenario: Usuario sin autorización intenta resetear una contraseña
- DADO un usuario cuyo perfil no permite administrar identidad
- CUANDO intenta acceder a `POST /auth/users/{id}/reset-password`
- ENTONCES el Backend MUST retornar HTTP `403 Forbidden` con `{detail}` genérico
- Y el Backend MUST NOT modificar la contraseña del usuario

### Requirement: Desactivación y reactivación
El administrador (Jefe) MUST poder desactivar y reactivar usuarios. La desactivación MUST invalidar (blacklist) todos los refresh del usuario; un usuario desactivado MUST NOT poder autenticarse ni renovar sesión.

#### Scenario: Jefe desactiva un usuario e invalida su sesión
- DADO un usuario activo con un refresh válido
- CUANDO el Frontend envía la solicitud a `POST /auth/users/{id}/deactivate`
- ENTONCES el Backend MUST procesarla dentro de `transaction.atomic()`, marcar `is_active=False` e invalidar sus refresh
- Y el Backend MUST registrar la operación en `audit_log` con acción `UPDATE`
- Y el usuario MUST NOT poder renovar ni iniciar sesión
- Y el Frontend MUST mostrar una notificación de éxito usando tokens del theme

#### Scenario: Jefe reactiva un usuario desactivado
- DADO un usuario desactivado
- CUANDO el Frontend envía la solicitud a `POST /auth/users/{id}/reactivate`
- ENTONCES el Backend MUST marcar `is_active=True` y registrar la operación en `audit_log`
- Y el usuario MUST poder volver a autenticarse

#### Scenario: Usuario sin autorización intenta desactivar a otro
- DADO un usuario cuyo perfil no permite administrar identidad
- CUANDO intenta acceder a `POST /auth/users/{id}/deactivate`
- ENTONCES el Backend MUST retornar HTTP `403 Forbidden` con `{detail}` genérico
- Y el Backend MUST NOT modificar el estado del usuario

### Requirement: Auditoría de eventos de seguridad
El sistema MUST registrar en el `audit_log` (vía el decorador `@audit`) los eventos de reset de contraseña, desactivación, reactivación y cambio de perfil, con el usuario que ejecuta la acción, el usuario afectado, el tipo de evento, la fecha/hora y —cuando aplique— el valor anterior y el nuevo del campo modificado. El registro de auditoría MUST ser atómico con la operación: si el registro falla, la operación completa MUST revertirse.

#### Scenario: El reset queda auditado
- DADO un administrador que resetea la contraseña de un usuario
- CUANDO el reset se ejecuta con éxito
- ENTONCES el Backend MUST registrar en `audit_log` el ejecutor, el afectado, el tipo de evento y la fecha/hora

#### Scenario: Fallo al auditar revierte la operación de seguridad
- DADO un administrador que ejecuta una desactivación
- CUANDO el registro en `audit_log` falla dentro de la transacción
- ENTONCES el Backend MUST revertir la desactivación (rollback total) y MUST NOT dejar el usuario en estado inconsistente
- Y el Backend MUST retornar un error del contrato uniforme

### 2.2 → specs/auth/spec.md

# Delta para la capability `auth`

## ADDED Requirements

### Requirement: Cambio de contraseña forzado en el primer acceso
Cuando un usuario tiene activo el flag `must_change_password`, el sistema MUST exigir el cambio de contraseña antes de permitir cualquier otra operación. Mientras el flag esté activo, solo el cambio de contraseña propio, `GET /auth/me` y el cierre de sesión MUST estar disponibles; cualquier otra operación MUST rechazarse con HTTP `403 Forbidden` y `{detail}` indicando la obligación de cambio. Tras un cambio exitoso, el flag MUST desactivarse.

#### Scenario: Login con cambio forzado pendiente
- DADO un usuario con el flag `must_change_password` activo
- CUANDO inicia sesión con su contraseña temporal en `POST /auth/login`
- ENTONCES el Backend MUST autenticarlo y emitir tokens
- Y la respuesta de `GET /auth/me` MUST indicar que debe cambiar su contraseña
- Y el Frontend MUST redirigir a la pantalla de cambio de contraseña

#### Scenario: Operación bloqueada mientras el cambio está pendiente
- DADO un usuario autenticado con el flag activo
- CUANDO intenta una operación distinta de cambiar su contraseña, `GET /auth/me` o logout
- ENTONCES el Backend MUST retornar HTTP `403 Forbidden` con `{detail}` que exige el cambio de contraseña
- Y el Backend MUST NOT ejecutar la operación solicitada
- Y el Frontend MUST mantener al usuario en la pantalla de cambio de contraseña

#### Scenario: El cambio de contraseña desactiva el flag
- DADO un usuario con el flag activo
- CUANDO cambia su contraseña con éxito en `POST /auth/change-password`
- ENTONCES el Backend MUST desactivar `must_change_password` dentro de `transaction.atomic()`
- Y el usuario MUST poder operar normalmente según su perfil

### 2.3 → specs/access-control/spec.md

# Delta para la capability `access-control`

## ADDED Requirements

### Requirement: Administración de perfiles
Un usuario autorizado (Jefe) MUST poder editar y dar de baja perfiles (soft delete clase 2) y configurar sus permisos por (módulo, acción) desde el catálogo conocido y sus flags de capacidad. Un perfil con usuarios asignados MUST NOT poder darse de baja sin reasignar antes a esos usuarios.

#### Scenario: Jefe edita los permisos de un perfil
- DADO un perfil existente y un administrador con perfil Jefe
- CUANDO el Frontend envía la solicitud a `PATCH /authz/profiles/{id}` con permisos por (módulo, acción) del catálogo
- ENTONCES el Backend MUST procesarla dentro de `transaction.atomic()` y persistir los permisos actualizados
- Y el Backend MUST registrar la operación en `audit_log` con acción `UPDATE`
- Y los usuarios con ese perfil MUST resolver su autorización con los permisos nuevos
- Y el Frontend MUST mostrar una notificación de éxito usando tokens del theme

#### Scenario: Jefe da de baja un perfil sin usuarios
- DADO un perfil sin usuarios asignados
- CUANDO el Frontend envía la solicitud a `DELETE /authz/profiles/{id}`
- ENTONCES el Backend MUST marcarlo como eliminado (soft delete clase 2, `deleted_at`) y registrar la operación en `audit_log` con acción `SOFT_DELETE`
- Y el perfil MUST dejar de ofrecerse para asignación

#### Scenario: Jefe intenta dar de baja un perfil en uso
- DADO un perfil con al menos un usuario asignado
- CUANDO el Frontend intenta `DELETE /authz/profiles/{id}`
- ENTONCES el Backend MUST NOT darlo de baja
- Y el Backend MUST retornar HTTP `409 Conflict` con `{detail}` indicando que hay usuarios asignados (baja bloqueada por dependencias)
- Y el Frontend MUST mostrar el mensaje indicando que primero debe reasignar a esos usuarios

#### Scenario: Usuario sin autorización intenta administrar perfiles
- DADO un usuario cuyo perfil no permite administrar perfiles
- CUANDO intenta acceder a `PATCH /authz/profiles/{id}` o `DELETE /authz/profiles/{id}`
- ENTONCES el Backend MUST retornar HTTP `403 Forbidden` con `{detail}` genérico
- Y el Backend MUST NOT modificar el perfil

## MODIFIED Requirements

### Requirement: Asignación de perfil a usuario
Cada usuario MUST estar asociado a exactamente un perfil. La autorización del sistema MUST resolverse por el perfil del usuario, no por su `role` nominal. Solo el `Jefe` MUST poder asignar perfiles. Al asignar o cambiar el perfil de un usuario, el sistema MUST sincronizar su `role` nominal con el perfil e **invalidar (blacklist) los refresh vigentes** del usuario, de modo que los permisos nuevos surtan efecto sin esperar a la expiración del token.
*(Anteriormente: la asignación cambiaba el perfil y registraba `audit_log`, pero NO sincronizaba el `role` ni invalidaba las sesiones activas — el usuario conservaba sus permisos previos hasta que expirara el refresh.)*

#### Scenario: Cambiar el perfil sincroniza el rol e invalida la sesión
- DADO un usuario con un perfil asignado y un refresh válido
- CUANDO el `Jefe` envía la solicitud a `POST /authz/users/{id}/assign-profile` con un perfil distinto
- ENTONCES el Backend MUST procesarla dentro de `transaction.atomic()`, actualizar el perfil y sincronizar el `role` nominal
- Y el Backend MUST invalidar (blacklist) los refresh vigentes del usuario
- Y el Backend MUST registrar la operación en `audit_log` con acción `UPDATE`
- Y el usuario MUST renovar su sesión para operar con los permisos actualizados

---

## 3) DESIGN → design.md

### 1. Capa de Datos (PostgreSQL + Django ORM)

#### Tablas e Índices

| Tabla | Índice / Constraint | Tipo | Justificación |
| :--- | :--- | :--- | :--- |
| `accounts_user` | `must_change_password` | columna `boolean not null default false` | Sin índice: no se filtra por este campo; se lee del registro ya cargado por id en autenticación. |
| `accounts_user` | `username` (existente, F1) | `unique` | Identificador único del usuario; el escenario de duplicado (400) se apoya en él. |
| `authz_profile` | `deleted_at` (existente, F2) | `partial-unique` sobre `name WHERE deleted_at IS NULL` | Soft delete clase 2 ya definido en F2; F3 no lo altera, solo lo consume en la baja. |

#### Modelo Django

```python
# Modelo Django — Tabla: accounts_user (MODIFICA el modelo de F1; no se crea tabla nueva)
# Mixins existentes de F1 (AbstractUser + TimeStampedMixin). NO es catálogo: sin SoftDeleteMixin.

class User(AbstractUser):           # F1; F2 añadió FK profile
    # ... campos de F1/F2 ...
    must_change_password = models.BooleanField(
        default=False,
        help_text="Obliga al usuario a cambiar su contraseña en el primer acceso tras un reset administrativo.",
    )
```

`authz.Profile` ya existe (F2): F3 **no añade modelo**; añade endpoints de administración y la regla
de baja con usuarios asignados. La auditoría usa el modelo de log + el decorador `@audit` del
bootstrap; no se crea modelo nuevo.

#### Migración Django

```
# Archivo: accounts/migrations/000X_user_must_change_password.py
# operations: AddField(model_name="user", name="must_change_password", BooleanField(default=False))
# Generar con: python manage.py makemigrations accounts
# Aplicar con:  python manage.py migrate
# Reverse de prueba: python manage.py migrate accounts <migracion_anterior>   # elimina la columna, sin pérdida de datos
```

#### Impacto en Invariantes del Sistema

- **Período cerrado:** No aplica — F3 no crea documentos con fecha.
- **Kardex FIFO / append-only:** No se afecta — F3 no genera movimientos de Kardex.
- **Doble costeo:** No se afecta.
- **Cuadre de ruta:** No se afecta.
- **Snapshot inmutable de entrega:** No se afecta.
- **Nota de crédito vinculada:** No se afecta.
- **Soft delete (3 clases):** `Profile` = catálogo (soft delete clase 2, ya en F2); `User` = ficha de identidad → se **desactiva** (`is_active=False`), no se borra ni usa `deleted_at`.
- **Trazabilidad:** No se altera Ingreso → Kardex → Entrega → Cobro / Ingreso → CxP → Pago.

---

### 2. Capa de API y Contratos (Fuente de Verdad)

#### Diccionario de Datos Vivo

| Entidad | Campo | Tipo (Py / TS) | Descripción (Uso y Propósito) | Restricciones |
| :--- | :--- | :--- | :--- | :--- |
| `User` | `username` | `str / string` | Identificador único de acceso (F1). | Unique, requerido |
| `User` | `profile` | `UUID / string` | Perfil que resuelve la autorización (F2). | FK `authz.Profile` activo, requerido |
| `User` | `role` | `str / string` | Rol nominal sincronizado al perfil (no autoriza). | Enum de roles del sistema |
| `User` | `is_active` | `bool / boolean` | Estado de activación; `False` impide autenticar. | Default `True` |
| `User` | `must_change_password` | `bool / boolean` | Flag de cambio forzado en el primer acceso. | Default `False`, not null |
| `ResetPassword` (write) | `temporary_password` | `str / string` | Contraseña temporal definida por el admin (opcional). | Write-only, cumple política; mutuamente excluyente con `generate` |
| `ResetPassword` (write) | `generate` | `bool / boolean` | Si `True`, el sistema genera la temporal. | Default `False` |
| `ResetPassword` (read) | `temporary_password` | `str / string` | Temporal generada, devuelta una sola vez. | Read-only, solo en la respuesta del reset |

#### Backend: Serializers DRF

```python
# Entrada (write) y salida (read) separadas. Cada campo con help_text para el OpenAPI.
# UserAdminWriteSerializer  — crear/editar usuario (username, profile, datos básicos)
# UserAdminReadSerializer   — salida (sin password; expone is_active, profile, must_change_password)
# ResetPasswordWriteSerializer — temporary_password (write-only, opcional) XOR generate
# ResetPasswordReadSerializer  — temporary_password generada (read-only, una sola vez)
# ProfileAdminWriteSerializer  — permisos por (módulo, acción) del catálogo + flags (editar)
# (La asignación de perfil reutiliza el serializer/endpoint assign-profile de F2, extendido en services.)
# El ViewSet NO contiene lógica: delega en services/.
```

#### Frontend: Tipos generados (Zod + TypeScript)

```typescript
// Generado desde el OpenAPI de DRF con `npm run codegen` — NO editar a mano.
// userAdminSchema, resetPasswordSchema, profileAdminSchema (Zod) + z.infer<>.
// La asignación de perfil reutiliza el assignProfileSchema generado en F2.
// Formularios con React Hook Form + zodResolver(...).
```

#### Endpoints de DRF

| Verbo | Ruta | Write Serializer | Read Serializer | Códigos HTTP | Roles (perfil) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/auth/users` | — | `UserAdminRead` | `200/403` | Jefe |
| `POST` | `/auth/users` | `UserAdminWrite` | `UserAdminRead` | `201/400/403` | Jefe |
| `PATCH` | `/auth/users/{id}` | `UserAdminWrite` | `UserAdminRead` | `200/400/403/404` | Jefe |
| `POST` | `/auth/users/{id}/deactivate` | — | `UserAdminRead` | `200/403/404` | Jefe |
| `POST` | `/auth/users/{id}/reactivate` | — | `UserAdminRead` | `200/403/404` | Jefe |
| `POST` | `/auth/users/{id}/reset-password` | `ResetPasswordWrite` | `ResetPasswordRead` | `200/400/403/404` | Jefe |
| `POST` | `/authz/users/{id}/assign-profile` *(F2, extendido)* | `AssignProfileWrite` (F2) | `UserAdminRead` | `200/400/403/404` | Jefe |
| `PATCH` | `/authz/profiles/{id}` | `ProfileAdminWrite` | `ProfileRead` (F2) | `200/400/403/404` | Jefe |
| `DELETE` | `/authz/profiles/{id}` | — | — | `204/403/404/409` | Jefe |

> `POST /authz/profiles` (crear), `GET /authz/profiles` (listar) y `POST /authz/users/{id}/assign-profile`
> ya existen en F2. F3 **completa** `PATCH` (editar permisos) y `DELETE` (baja) de perfiles, y **extiende
> el comportamiento** de `assign-profile` (sincronizar `role` + blacklist de refresh) sin crear un
> endpoint nuevo de cambio de perfil. Ver `## MODIFIED Requirements` en el delta de access-control.

#### Servicio de Negocio

| Servicio | Método | Responsabilidad única | Transaccional |
| :--- | :--- | :--- | :--- |
| `apps/accounts/services.py` | `create_user()` | Crea usuario, asigna perfil, sincroniza `role`. | Sí |
| `apps/accounts/services.py` | `update_user()` | Edita datos básicos del usuario. | Sí |
| `apps/accounts/services.py` | `reset_password()` | Fija temporal (dada o generada), activa flag, blacklist de refresh. | Sí |
| `apps/accounts/services.py` | `deactivate_user()` / `reactivate_user()` | Cambia `is_active`; al desactivar, blacklist de refresh. | Sí |
| `apps/authz/services.py` | `assign_profile()` *(F2, extendido)* | Cambia perfil, **sincroniza `role` + blacklist de refresh** (delta de F3). | Sí |
| `apps/authz/services.py` | `update_profile_permissions()` | Persiste permisos por (módulo, acción) del catálogo + flags. | Sí |
| `apps/authz/services.py` | `deactivate_profile()` | Soft delete clase 2 validando que no haya usuarios asignados. | Sí |

> Todos los métodos aplican `@audit(action, entity)`. F3 no tiene cálculo financiero: no hay
> funciones puras en `utils/`.

---

### 3. Capa de Presentación (UI — React + Refine)

#### Árbol de Directorios de las Features

```
src/features/users/
├── components/
│   ├── UsersAdminConsole.tsx     # Contenedor: orquesta hooks y sub-componentes
│   ├── UserForm.tsx              # Presentacional: alta/edición (RHF + zodResolver)
│   └── ResetPasswordDialog.tsx   # Presentacional: reset + muestra temporal una vez
├── hooks/
│   ├── useUsersList.ts           # useList de Refine
│   ├── useUserMutations.ts       # useCreate/useUpdate
│   └── useUserAdminActions.ts    # useCustomMutation: deactivate/reactivate/reset/assign-profile
├── types/
│   └── users.types.ts            # Re-exporta tipos generados del OpenAPI
└── index.ts                      # Contrato público

src/features/profiles/
├── components/
│   ├── ProfilesAdminConsole.tsx  # Contenedor
│   ├── PermissionMatrix.tsx      # Presentacional: matriz (módulo × acción) + flags
│   └── ProfileForm.tsx           # Presentacional
├── hooks/
│   ├── useProfilesList.ts        # useList
│   └── useProfileAdminActions.ts # useUpdate (editar) / useCustomMutation (baja)
├── types/
│   └── profiles.types.ts
└── index.ts

src/features/auth/                # MODIFICA F1
└── components/
    └── ForcePasswordChangeGuard.tsx  # Bloquea navegación si me.must_change_password
```

#### Custom Hooks

| Hook | Responsabilidad única | Endpoint / resource | Refine hook |
| :--- | :--- | :--- | :--- |
| `useUsersList` | Listar usuarios. | `GET /auth/users` / `users` | `useList` |
| `useUserMutations` | Crear / editar usuario. | `POST·PATCH /auth/users` / `users` | `useCreate` / `useUpdate` |
| `useUserAdminActions` | Acciones de ciclo de vida (deactivate/reactivate/reset; asignar perfil vía endpoint de F2). | `POST /auth/users/{id}/...` · `POST /authz/users/{id}/assign-profile` | `useCustomMutation` |
| `useProfilesList` | Listar perfiles. | `GET /authz/profiles` / `profiles` | `useList` |
| `useProfileAdminActions` | Editar permisos / dar de baja. | `PATCH·DELETE /authz/profiles/{id}` | `useUpdate` / `useCustomMutation` |

#### Resources y Páginas (`src/pages/`)

| Ruta / Resource | Tipo | Página | Componente Contenedor | Roles permitidos |
| :--- | :--- | :--- | :--- | :--- |
| `/admin/users` | Protegida | `UsersAdminPage.tsx` | `UsersAdminConsole` | Jefe |
| `/admin/profiles` | Protegida | `ProfilesAdminPage.tsx` | `ProfilesAdminConsole` | Jefe |
| `/auth/change-password` | Protegida | (F1) | (F1) + `ForcePasswordChangeGuard` | Todos (forzado si flag) |

> El gating por perfil se resuelve en el `accessControlProvider` de Refine (F2). El
> `ForcePasswordChangeGuard` consume `GET /auth/me`: si `must_change_password`, redirige a
> `/auth/change-password` y bloquea toda otra ruta. Estados vacío/carga/error/éxito obligatorios;
> cero hex literales; inputs ≥16px iOS; áreas táctiles ≥44px.

---

### 4. Configuración y DevSecOps

#### Gestión de Secretos

- **Backend:** F3 **no introduce variables de entorno nuevas**. La generación de contraseñas temporales usa el RNG criptográfico de la stdlib; no hay claves nuevas. Las temporales MUST NOT loggearse.
- **Frontend:** Sin variables `VITE_*` nuevas.

#### Seguridad Proactiva

- **Backend:** `ruff`, `mypy --strict`, `bandit` limpios en `apps/accounts` y `apps/authz`.
- **Frontend:** `eslint` y `tsc` limpios en `src/features/users`, `src/features/profiles` y el guard de auth.
- **SCA:** F3 no añade dependencias; `pip-audit` y `npm audit` deben seguir limpios.

---

### 5. Cambios Estructurales

#### Nuevas Dependencias

Ninguna. F3 se resuelve con la stack existente (DRF, SimpleJWT, Refine, RHF + Zod).

#### Migraciones de Base de Datos

`AddField accounts.User.must_change_password` (boolean, default `False`, not null). Reverse funcional
(elimina la columna). No requiere data migration: el default cubre las filas existentes.

---

## 4) TASKS → tasks.md

> Orden obligatorio del `config.yaml`: Contrato (OpenAPI) → Migraciones Django → Backend (services) → Frontend → Seguridad → Pruebas. Cada tarea nombra el archivo/módulo exacto. Definition of done global: todos los gates del pipeline en verde localmente antes de declarar el change completo.

### A. Contrato y modelo (OpenAPI + datos)
- [ ] A.1 Añadir `must_change_password` (boolean, default `false`, not null) al modelo `accounts.User` con `help_text`.
- [ ] A.2 Definir serializers de administración de usuarios en `apps/accounts/serializers.py` (`UserAdminWrite/Read`, `ResetPasswordWrite/Read`), con `help_text` por campo.
- [ ] A.3 Definir serializers de administración de perfiles en `apps/authz/serializers.py` (`ProfileAdminWrite`: editar permisos; baja con validación de usuarios asignados). Reutilizar el `AssignProfileWrite` de F2 para el cambio de perfil.
- [ ] A.4 Anotar los endpoints con `drf-spectacular` y regenerar `schema.yml`.

### B. Migraciones
- [ ] B.1 `makemigrations accounts` (campo `must_change_password`); confirmar reversibilidad (`AddField` estándar).
- [ ] B.2 `migrate`, verificar arranque limpio y probar el reverse (`migrate accounts <anterior>` → re-aplicar).

### C. Backend (services + vistas)
- [ ] C.1 Implementar en `apps/accounts/services.py`: `create_user`, `update_user`, `reset_password` (temporal + flag + blacklist), `deactivate_user`/`reactivate_user` (blacklist), todo bajo `@audit` y `transaction.atomic()`.
- [ ] C.2 Implementar en `apps/authz/services.py`: **extender `assign_profile` de F2** para sincronizar `role` + blacklist de refresh; `update_profile_permissions` y `deactivate_profile` (soft delete clase 2 con validación de usuarios asignados). Todo bajo `@audit` y `transaction.atomic()`.
- [ ] C.3 Implementar las vistas admin delgadas en `apps/accounts/views.py` y `apps/authz/views.py`, protegidas por la permission class de Jefe (F2); registrar rutas en los `urls.py`.
- [ ] C.4 Implementar la permission class / middleware de cambio forzado que bloquea todo (403 `{detail}`) salvo `change-password`, `me` y `logout` cuando `must_change_password` está activo.
- [ ] C.5 Verificar que `POST /auth/change-password` (F1) desactiva el flag y que `GET /auth/me` lo expone.
- [ ] C.6 Verificar que todos los errores salen por el contrato uniforme (`{detail}` para 401/403/404; `{campo: [mensajes]}` para 400).

### D. Frontend
- [ ] D.1 Regenerar tipos + Zod desde `schema.yml` (`npm run codegen`).
- [ ] D.2 Construir la consola de usuarios en `src/features/users/` (hooks `useUsersList`/`useUserMutations`/`useUserAdminActions`, `UsersAdminConsole`, `UserForm`, `ResetPasswordDialog`), visible solo para Jefe (gating de F2).
- [ ] D.3 Construir la administración de perfiles en `src/features/profiles/` (`ProfilesAdminConsole`, `PermissionMatrix`, hooks), visible solo para Jefe.
- [ ] D.4 Implementar `ForcePasswordChangeGuard` en `src/features/auth/`: si `me.must_change_password`, redirigir a `/auth/change-password` y bloquear navegación hasta completarlo.
- [ ] D.5 Estados vacío/carga/error/éxito, tokens del theme, `FieldError` compartido, inputs ≥16px iOS, áreas táctiles ≥44px.

### E. Seguridad
- [ ] E.1 Verificar server-side que solo el perfil Jefe accede a la administración (usuarios y perfiles) → 403 en caso contrario.
- [ ] E.2 Verificar que reset, desactivación y cambio de perfil invalidan los refresh (blacklist) de forma efectiva.
- [ ] E.3 Verificar que el bloqueo por cambio forzado no puede saltarse (ningún endpoint de negocio responde con el flag activo).
- [ ] E.4 Verificar que los eventos de seguridad quedan auditados con ejecutor, afectado, tipo y fecha/hora, y que el fallo de auditoría revierte la operación.
- [ ] E.5 Verificar que la contraseña temporal no se loggea en claro y que no hay secretos en el código.

### F. Pruebas (gate)
- [ ] F.1 Tests de backend en `apps/accounts/tests/` y `apps/authz/tests/` cubriendo todos los Scenarios (crear usuario; 403 sin autorización; identificador duplicado → 400; cambio de perfil + invalidación; perfil inexistente → 404; reset + temporal + flag + blacklist; temporal inválida → 400; desactivar/reactivar; auditoría y rollback por fallo de auditoría; cambio forzado bloquea operaciones → 403 y se desactiva al cambiar; editar perfil; baja de perfil sin usuarios; baja de perfil en uso → 409).
- [ ] F.2 Tests de frontend (Vitest + RTL) de las consolas de administración y del `ForcePasswordChangeGuard` (flujo de primer acceso), incluyendo estados vacío/carga/error.
- [ ] F.3 Ejecutar y dejar en verde: `ruff`, `mypy --strict`, `bandit`, `pip-audit`, `pytest` (cobertura ≥80%); `eslint`, `tsc`, `npm audit`, `vitest`; `Trivy` sobre la imagen del backend en el pipeline de deploy (sin CVEs conocidos). Confirmar antes de declarar el change completo.
