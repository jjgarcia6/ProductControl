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

### Intent

Entregar la consola de administración de identidad: el ciclo de vida del usuario (alta, edición, baja), la asignación de perfil/rol, el reset administrativo de contraseña con cambio forzado, y la administración de perfiles que F2 dejó en modelo + mecanismo + seed. Es lo que permite operar el sistema sin sembrar usuarios a mano. Cierra el hueco de identidad que los requerimientos v1.1 no cubrían.

### Decisión de alcance

Un solo change cohesivo: es la misma consola de administración. Toca tres capabilities:

- **`user-management`** (inicia): CRUD de usuarios, reset, desactivación, auditoría de eventos de seguridad.
- **`auth`** (modifica): flag de cambio forzado de contraseña en el primer acceso.
- **`access-control`** (modifica): administración de perfiles (CRUD + configuración de permisos) que completa lo iniciado en F2.

### Scope (qué cambia)

- **CRUD de usuarios** (crear, editar, desactivar, reactivar), restringido al perfil Jefe.
- **Asignación y cambio de perfil**, con el `role` nominal sincronizado.
- **Reset administrativo** de contraseña: temporal (definida por el admin o generada por el sistema) + activación del flag de cambio forzado.
- **Contraseña temporal con cambio forzado** en el primer acceso (flag `must_change_password`).
- **Desactivación que invalida (blacklist) el refresh** del usuario.
- **Administración de perfiles** (CRUD + permisos por módulo/acción + flags), completando F2.
- **Auditoría de eventos de seguridad** (reset, desactivación/reactivación, cambio de perfil) usando el mecanismo `@audit` del bootstrap.

### Impacto en el modelo de datos (antes que UI — DIP)

- `accounts.User`: añadir `must_change_password` (boolean, default `false`). Migración sobre `accounts`, reversible.
- No se crean tablas nuevas: la administración opera sobre `User` (F1) y `Profile` (F2). Los eventos de seguridad se registran con el modelo de log de auditoría del bootstrap.

### Relación con F10 (audit-rules)

F3 audita **eventos de seguridad** (reset, desactivación, cambio de perfil) con el mecanismo `@audit` ya disponible desde el bootstrap. No depende de F10, que formaliza la auditoría de **correcciones de documentos** (peso/costo) — alcance distinto. No se reordenan fases.

### Fuera de alcance

- Cambio de contraseña propio del usuario autenticado → ya está en F1.
- Recuperación self-service por email → diferida a post-F25 (depende de la infraestructura de email de F22).
- Vínculo User ↔ Ficha de Directorio → se modela en F4.
- MFA, SSO, invitaciones por correo → YAGNI.

### Verificación de invariantes

No toca Kardex, período, costeo ni documentos. Respeta: solo el Jefe gestiona identidad (vía permission classes de F2); SimpleJWT fijo y blacklist (F1); contrato de errores uniforme; soft delete clase 2 para perfiles.

### Criterio de aborto (verificable)

Si las permission classes por perfil de F2 no están disponibles (verificable: `apps/authz/permissions.py` ausente o `Profile` sin migrar), abortar: F3 no puede restringir la administración al Jefe sin el motor de autorización de F2.

---

## 2) SPECS

### 2.1 → specs/user-management/spec.md

# Delta para la capability `user-management`

## ADDED Requirements

### Requirement: Gestión de usuarios
Un usuario cuyo perfil lo autorice (Jefe) MUST poder crear, editar, desactivar y reactivar usuarios. La creación MUST asignar un perfil y dejar el `role` nominal sincronizado. Quien no esté autorizado MUST recibir 403. Los errores de validación MUST seguir el contrato uniforme.

#### Scenario: Crear usuario por administrador autorizado
- DADO un usuario con perfil Jefe
- CUANDO crea un usuario con identificador único, perfil y datos válidos
- ENTONCES el sistema persiste el usuario con su perfil y su `role` sincronizado
- Y el usuario queda disponible para autenticarse

#### Scenario: Crear usuario sin autorización
- DADO un usuario cuyo perfil no permite administrar usuarios
- CUANDO intenta crear un usuario
- ENTONCES el sistema responde 403 con `{detail}`

#### Scenario: Identificador duplicado
- DADO un identificador ya existente
- CUANDO se intenta crear otro usuario con el mismo identificador
- ENTONCES el sistema responde 400 con `{campo: [mensajes]}` en el campo del identificador

### Requirement: Asignación y cambio de perfil
El administrador MUST poder asignar o cambiar el perfil de un usuario, con el `role` nominal sincronizado. Cambiar el perfil de un usuario con sesión activa MUST invalidar sus refresh vigentes para forzar un nuevo inicio de sesión con los permisos actualizados.

#### Scenario: Cambiar el perfil de un usuario
- DADO un usuario con un perfil asignado
- CUANDO el administrador le asigna un perfil distinto
- ENTONCES el sistema actualiza el perfil y sincroniza el `role`
- Y invalida los refresh vigentes del usuario

### Requirement: Reset administrativo de contraseña
El administrador MUST poder restablecer la contraseña de un usuario sin conocer la anterior. El reset MUST fijar una contraseña temporal (definida por el administrador o generada por el sistema), activar el flag de cambio forzado e invalidar los refresh vigentes del usuario.

#### Scenario: Reset administrativo
- DADO un usuario existente
- CUANDO el administrador resetea su contraseña
- ENTONCES el sistema fija la contraseña temporal
- Y activa el flag de cambio forzado del usuario
- Y invalida los refresh vigentes del usuario

### Requirement: Desactivación y reactivación
El administrador MUST poder desactivar y reactivar usuarios. La desactivación MUST invalidar (blacklist) todos los refresh del usuario; un usuario desactivado MUST NOT poder autenticarse ni renovar sesión.

#### Scenario: Desactivar usuario invalida su sesión
- DADO un usuario activo con un refresh válido
- CUANDO el administrador lo desactiva
- ENTONCES el sistema invalida sus refresh
- Y el usuario no puede renovar ni iniciar sesión

#### Scenario: Reactivar usuario
- DADO un usuario desactivado
- CUANDO el administrador lo reactiva
- ENTONCES el usuario puede volver a autenticarse

### Requirement: Auditoría de eventos de seguridad
El sistema MUST registrar en el log de auditoría los eventos de reset de contraseña, desactivación, reactivación y cambio de perfil, con el usuario que ejecuta la acción, el usuario afectado, el tipo de evento y la fecha/hora.

#### Scenario: El reset queda auditado
- DADO un administrador que resetea la contraseña de un usuario
- CUANDO se ejecuta el reset
- ENTONCES el sistema registra el evento con ejecutor, afectado, tipo y fecha/hora

#### Scenario: La desactivación queda auditada
- DADO un administrador que desactiva un usuario
- CUANDO se ejecuta la desactivación
- ENTONCES el sistema registra el evento en el log de auditoría

### 2.2 → specs/auth/spec.md

# Delta para la capability `auth`

## ADDED Requirements

### Requirement: Cambio de contraseña forzado en el primer acceso
Cuando un usuario tiene activo el flag de cambio forzado, el sistema MUST exigir el cambio de contraseña antes de permitir cualquier otra operación. Mientras el flag esté activo, solo el cambio de contraseña propio MUST estar disponible; cualquier otra operación MUST rechazarse con un error del contrato uniforme que indique la obligación de cambio. Tras un cambio exitoso, el flag MUST desactivarse.

#### Scenario: Login con cambio forzado pendiente
- DADO un usuario con el flag de cambio forzado activo
- CUANDO inicia sesión con su contraseña temporal
- ENTONCES el sistema lo autentica
- Y la identidad indica que debe cambiar su contraseña

#### Scenario: Operación bloqueada mientras el cambio está pendiente
- DADO un usuario autenticado con el flag activo
- CUANDO intenta una operación distinta del cambio de contraseña
- ENTONCES el sistema responde con un error del contrato uniforme que exige el cambio

#### Scenario: El cambio de contraseña desactiva el flag
- DADO un usuario con el flag activo
- CUANDO cambia su contraseña con éxito
- ENTONCES el sistema desactiva el flag
- Y el usuario puede operar normalmente

### 2.3 → specs/access-control/spec.md

# Delta para la capability `access-control`

## ADDED Requirements

### Requirement: Administración de perfiles
Un usuario autorizado (Jefe) MUST poder crear, editar y dar de baja perfiles (soft delete clase 2) y configurar sus permisos por (módulo, acción) desde el catálogo conocido y sus flags de capacidad. Un perfil con usuarios asignados MUST NOT poder darse de baja sin reasignar antes a esos usuarios.

#### Scenario: Editar los permisos de un perfil
- DADO un perfil existente
- CUANDO el administrador modifica sus permisos por módulo y acción
- ENTONCES el sistema persiste los permisos actualizados
- Y los usuarios con ese perfil resuelven su autorización con los permisos nuevos

#### Scenario: Dar de baja un perfil sin usuarios
- DADO un perfil sin usuarios asignados
- CUANDO el administrador lo da de baja
- ENTONCES el sistema lo marca como eliminado (soft delete) y deja de ofrecerlo para asignación

#### Scenario: Intentar dar de baja un perfil en uso
- DADO un perfil con al menos un usuario asignado
- CUANDO el administrador intenta darlo de baja
- ENTONCES el sistema responde 400 con `{campo: [mensajes]}` indicando que hay usuarios asignados

---

## 3) DESIGN → design.md

### Capa de datos

- **`accounts.User`**: añadir `must_change_password` (boolean, default `false`). Migración sobre `accounts`, reversible.
- **`authz.Profile`**: ya existe (F2). F3 no añade modelo; añade endpoints de administración y la regla de baja con usuarios asignados.
- **Auditoría**: se usa el modelo de log + el decorador/función `@audit` del bootstrap. No se crea modelo nuevo.

### Capa de API

- **Administración de usuarios** en `apps/accounts` (endpoints admin): crear, editar, desactivar, reactivar, resetear contraseña, cambiar perfil. Transiciones explícitas, no CRUD genérico ciego.
- **Administración de perfiles** en `apps/authz` (endpoints admin): crear, editar permisos, dar de baja. Completa los endpoints de solo lectura/asignación de F2.
- **Permission classes de F2**: todos estos endpoints exigen un perfil con permiso de administración (Jefe). 403 `{detail}` al denegar.
- **Lógica en services**: el reset (temporal + flag + blacklist), la desactivación (blacklist), el cambio de perfil (sincroniza role + blacklist) viven en `apps/accounts/services.py`; la administración de perfiles en `apps/authz/services.py`. Viewsets delgados.
- **Contrato OpenAPI**: anotar con `drf-spectacular`; regenerar `schema.yml`.

### Cambio forzado de contraseña (mecanismo)

- Una **permission class global** (o middleware DRF) revisa `must_change_password`: si está activo, solo deja pasar el cambio de contraseña propio (`/auth/change-password`), `me` y `logout`; cualquier otro endpoint responde con el error del contrato que exige el cambio.
- El endpoint de cambio de contraseña (F1) desactiva el flag al completarse con éxito.
- La identidad (`me`) expone el flag para que el frontend redirija a la pantalla de cambio.

### Contraseña temporal

- El reset acepta una contraseña temporal escrita por el administrador **o** la genera el sistema (configurable en la llamada). Se comunica fuera de banda (no por email en esta fase).
- El reset siempre activa `must_change_password` y blacklistea los refresh vigentes.

### Capa de frontend

- **Consola de administración** (solo visible para Jefe, gating por perfil de F2): listado y formularios de usuarios; listado y formularios de perfiles con su matriz de permisos.
- **Flujo de primer acceso**: si `me` indica cambio forzado, el cliente redirige a la pantalla de cambio de contraseña y bloquea la navegación hasta completarlo.
- Estados vacío/carga/error/éxito; tokens del theme; `FieldError` compartido; inputs ≥16px iOS; áreas táctiles ≥44px.

### Seguridad

- Toda la administración exige perfil Jefe, resuelto server-side (permission classes de F2).
- Reset, desactivación y cambio de perfil invalidan refresh vía blacklist (infraestructura de F1).
- Eventos de seguridad auditados con `@audit`.
- Mensajes de error por el contrato uniforme; sin filtrar estructura interna en los 403.

### Qué NO se hace (YAGNI)

Sin recuperación por email, sin invitaciones, sin MFA, sin SSO, sin jerarquía de administradores. La recuperación self-service se evaluará post-F22 si el cliente la pide.

---

## 4) TASKS → tasks.md

> Orden obligatorio del `config.yaml`: Contrato (OpenAPI) → Migraciones Django → Backend (services) → Frontend → Seguridad → Pruebas. Cada tarea nombra el archivo/módulo exacto. Definition of done global: todos los gates del pipeline en verde localmente antes de declarar el change completo.

### A. Contrato y modelo (OpenAPI + datos)
- [ ] A.1 Añadir `must_change_password` (boolean, default `false`) al modelo `accounts.User`.
- [ ] A.2 Definir serializers de administración de usuarios en `apps/accounts/serializers.py` (crear/editar, reset, cambio de perfil, desactivar/reactivar).
- [ ] A.3 Definir serializers de administración de perfiles en `apps/authz/serializers.py` (crear/editar permisos, baja con validación de usuarios asignados).
- [ ] A.4 Anotar los endpoints con `drf-spectacular` y regenerar `schema.yml`.

### B. Migraciones
- [ ] B.1 `makemigrations accounts` (campo `must_change_password`); confirmar reversibilidad.
- [ ] B.2 `migrate` y verificar arranque limpio.

### C. Backend (services + vistas)
- [ ] C.1 Implementar en `apps/accounts/services.py`: reset (temporal + flag + blacklist), desactivación/reactivación (blacklist), cambio de perfil (sincroniza `role` + blacklist), todo bajo `@audit`.
- [ ] C.2 Implementar en `apps/authz/services.py` la administración de perfiles (crear/editar permisos; baja con validación de usuarios asignados).
- [ ] C.3 Implementar las vistas admin delgadas en `apps/accounts/views.py` y `apps/authz/views.py`, protegidas por la permission class de Jefe (F2); registrar rutas.
- [ ] C.4 Implementar la permission class / middleware de cambio forzado que bloquea todo salvo `change-password`, `me` y `logout` cuando `must_change_password` está activo.
- [ ] C.5 Verificar que el endpoint de cambio de contraseña (F1) desactiva el flag y que `me` lo expone.
- [ ] C.6 Verificar que todos los errores salen por el contrato uniforme.

### D. Frontend
- [ ] D.1 Regenerar tipos + Zod desde `schema.yml` (`npm run codegen`).
- [ ] D.2 Construir la consola de administración de usuarios en `src/features/users/` (listado + formularios), visible solo para Jefe (gating de F2).
- [ ] D.3 Construir la administración de perfiles en `src/features/profiles/` (listado + matriz de permisos), visible solo para Jefe.
- [ ] D.4 Implementar el flujo de primer acceso: si `me` indica cambio forzado, redirigir a cambio de contraseña y bloquear navegación hasta completarlo.
- [ ] D.5 Estados vacío/carga/error/éxito, tokens del theme, `FieldError` compartido, inputs ≥16px iOS.

### E. Seguridad
- [ ] E.1 Verificar server-side que solo el perfil Jefe accede a la administración (usuarios y perfiles).
- [ ] E.2 Verificar que reset, desactivación y cambio de perfil invalidan los refresh (blacklist) de forma efectiva.
- [ ] E.3 Verificar que el bloqueo por cambio forzado no puede saltarse (ningún endpoint de negocio responde con el flag activo).
- [ ] E.4 Verificar que los eventos de seguridad quedan auditados con ejecutor, afectado, tipo y fecha/hora.

### F. Pruebas (gate)
- [ ] F.1 Tests de backend en `apps/accounts/tests/` y `apps/authz/tests/` cubriendo todos los Scenarios (CRUD usuarios; 403 sin autorización; identificador duplicado; cambio de perfil + invalidación; reset + temporal + flag + blacklist; desactivar/reactivar; auditoría; cambio forzado bloquea operaciones y se desactiva al cambiar; administración de perfiles; baja de perfil en uso → 400).
- [ ] F.2 Tests de frontend (Vitest + RTL) de la consola de administración y del flujo de primer acceso (cambio forzado).
- [ ] F.3 Ejecutar y dejar en verde: `ruff`, `mypy --strict`, `bandit`, `pip-audit`, `pytest` (cobertura ≥80%); `eslint`, `tsc`, `npm audit`, `vitest`. Confirmar antes de declarar el change completo.
