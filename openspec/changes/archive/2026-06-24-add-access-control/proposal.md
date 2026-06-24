# Propuesta: add-access-control

## 1. El Problema o Necesidad de Negocio

F1 (`add-auth`) entregó identidad y autenticación con un campo `role` **nominal**, pero la
autorización quedó sin resolver: hoy cualquier usuario autenticado puede, en principio, ejecutar
cualquier acción y recibir cualquier campo en las respuestas. No existe forma de **gestionar los
permisos a nivel de perfil** (requerimiento 2.4), ni de **ocultar campos sensibles** según quién
consulta (p. ej. el costo), ni de habilitar **auto-aprobación por perfil** (requerimiento 6.5).

Si la autorización se clava en código por `role`, el cliente no podrá ajustar permisos sin tocar el
código — lo que contradice directamente el requisito de "gestionar a nivel de perfil". Esta
capability es **precondición de permisos** para F3, F4, F5, F8 y, de hecho, para todas las fases de
negocio siguientes: sin ella, cada módulo posterior quedaría sin un mecanismo uniforme para decidir
quién puede hacer qué y quién puede ver qué.

## 2. Alcance Crítico

### In-Scope (Lo que se va a construir)

**Decisión de alcance (opción C, validada):** perfil configurable pero **acotado** — permisos por
`(módulo, acción)` tomados de un **catálogo conocido y extensible**, más flags de capacidad. No es
un motor RBAC genérico arbitrario (violaría KISS/YAGNI) ni roles con permisos hardcodeados
(contradiría "gestionar a nivel de perfil"). Los cuatro roles del sistema se materializan como
**perfiles semilla**.

**Backend (dominio `access-control`, app Django `authz`):**
- Entidad **`Profile`**: nombre único, permisos por `(módulo, acción)` desde el catálogo, flag de
  capacidad `auto_approval`, y registro de campos sensibles visibles. Soft delete clase 2 (catálogo).
- **Asignación** usuario → perfil (FK `profile` en el modelo `accounts.User` de F1).
- **Motor de autorización** (permission classes de DRF) que resuelve por el perfil del usuario.
- **Mecanismo de campos invisibles:** serializer dinámico que **omite** de la respuesta los campos
  sensibles que el perfil no puede ver (no basta con marcarlos read-only).
- **Catálogo de módulos/acciones** y **registro de campos sensibles** como estructura central
  extensible por fase (constantes en `apps/authz/catalog.py`).
- **Cuatro perfiles semilla** (Jefe, Supervisor, Responsable de ruta, Usuario) vía data migration.
- Endpoints de **lectura** y **creación** de perfiles y de **asignación** perfil↔usuario; enriquecer
  `GET /auth/me` con el perfil. El endpoint de creación (`POST /authz/profiles`) es necesario para los
  escenarios del spec (crear / nombre duplicado / permiso fuera de catálogo); la **edición/baja** y la
  **UI** de administración quedan para F3. Nuevos contratos de datos: serializers DRF anotados con
  `drf-spectacular`; tipos/Zod generados del OpenAPI con los campos sensibles marcados **opcionales**.

**Frontend (feature `auth`, extendida):**
- Consumo del perfil desde `me` en el store de sesión; helpers de gating (`canDo` / `canSee`).
- Gating de acciones/columnas en los componentes ya existentes (defensa **secundaria**).

**Relación con el `role` de F1 (reconciliación):** `User.role` queda como **clasificación nominal**
de alto nivel. `Profile` es la **fuente de verdad de la autorización**: el sistema MUST resolver
siempre por el perfil, nunca por el `role` directamente. En el seed, cada role recibe su perfil
homónimo; el cliente puede crear perfiles adicionales más adelante sin tocar el `role`.

### Out-of-Scope (Prohibiciones Estrictas)
- **Backend:** Toda persistencia MUST ser PostgreSQL vía Django ORM. Sin SQL raw salvo justificación explícita.
- **Backend:** Las transacciones multi-tabla MUST usar `transaction.atomic()` con rollback total.
- **Backend:** Los modelos de catálogo/datos maestros MUST heredar del mixin de soft-delete (política de 3 clases). `Profile` es catálogo (clase 2). El Kardex y los documentos con flujo de estado MUST NOT usar soft delete (no aplican aquí).
- **Backend:** El cálculo financiero (FIFO, costo nominal/efectivo, merma, saldos CxC/CxP) MUST vivir en funciones puras sin dependencia del ORM. (No aplica en esta fase; sin cálculo financiero.)
- **Frontend:** Los colores hardcodeados MUST NOT usarse; todo estilo MUST usar tokens del theme (shadcn/Tailwind) con soporte de modo claro y oscuro.
- **Seguridad:** Las credenciales MUST NOT almacenarse en el código; MUST gestionarse vía `.env` / GCP Secret Manager.
- **Calidad:** Las refactorizaciones paralelas ajenas al dominio de este cambio MUST NOT introducirse (YAGNI).

**Fuera de alcance por dominio (se difiere a fases posteriores):**
- El campo `cost` invisible concreto y las reglas de auto-aprobación de ingreso → F12 (`intake`).
  Aquí solo el **mecanismo** y la **capacidad**, no su aplicación efectiva.
- La **UI de administración de perfiles** (pantallas de crear/editar perfil, asignar permisos) y la
  **edición/baja** de perfiles (`PATCH`/`DELETE`) → F3 (`user-management`). F2 entrega modelo,
  mecanismo, seed y los endpoints de lectura, creación y asignación.
- Motor RBAC genérico, jerarquías de roles y permisos por instancia (row-level) → YAGNI, no se hará.

## 3. Evaluación de Impacto

### Modelo de Datos (PostgreSQL)
- **Nueva tabla `profiles`** (app `authz`): `name` (único), `description` (opcional), `permissions`
  (estructura por módulo/acción validada contra el catálogo), `visible_sensitive_fields`,
  `auto_approval` (bool). Soft delete clase 2 → `deleted_at` + manager que filtra + **índice único
  parcial** sobre `name` (`WHERE deleted_at IS NULL`).
- **Nueva columna `profile_id`** (FK) en la tabla de usuario de `accounts`, apuntando a
  `authz.profiles`, con `on_delete=PROTECT` (un perfil en uso no puede borrarse). Nullable a nivel
  de DB para no romper filas existentes; la **data migration** de seed backfillea cada usuario hacia
  su perfil homónimo, de modo que tras migrar todo usuario tiene exactamente un perfil.
- **Migración sobre ambas apps** (`authz` + `accounts`), reversible (upgrade + downgrade). El seed de
  los cuatro perfiles va en una data migration con `reverse_code` que los elimina.
- **Ajuste en infraestructura compartida `apps/common/models.py` (F1):** `Profile` es el **primer**
  modelo concreto que hereda el mixin de soft delete clase 2, y los managers base estaban fijados al
  tipo base (`SoftDeleteManager(Manager["SoftDeleteModel"])`), lo que hacía que `Profile.objects`
  tipara como `SoftDeleteModel` y rompía `mypy --strict`. Se **generalizan** `SoftDeleteQuerySet` y
  `SoftDeleteManager` con un `TypeVar` acotado, de modo que cada catálogo que herede el mixin obtenga
  managers/querysets tipados a SU clase. Es un cambio de tipado (sin cambio de comportamiento ni de
  esquema), habilitador del dominio (no refactor ajeno); la suite de `apps/common` se reverifica intacta.
- No se crean ni alteran tablas de Kardex, período, costeo ni documentos.

### Lógica de Negocio y API
- Nuevos endpoints DRF derivados de necesidades concretas (no CRUD por defecto): `GET /authz/profiles`,
  `GET /authz/profiles/{id}` (lectura), `POST /authz/profiles` (creación, exigida por el spec) y
  `POST /authz/users/{id}/assign-profile` (acción explícita). Se **modifica** `GET /auth/me` (F1) para
  incluir el perfil.
- Nuevo servicio `apps/authz/services.py`: resolución de permisos `(perfil, módulo, acción) → bool`,
  construcción de la lista de campos visibles por perfil, asignación de perfil (con `@audit`) y seed
  de perfiles del sistema. ViewSets/serializers delgados que delegan.
- Nuevas permission classes (`apps/authz/permissions.py`) que devuelven **403 `{detail}`** al denegar,
  y un **mixin de serializer** que elimina del output los campos sensibles no permitidos.
- No se modifica FIFO, costeo, merma, CxC ni CxP (no existen aún).

### Flujo del Usuario (UI)
- **Sin pantallas nuevas** en esta fase (la administración de perfiles es F3). El frontend consume la
  identidad enriquecida (`me` con perfil) para condicionar la UI: oculta acciones/columnas según el
  perfil (defensa **secundaria**; la autoritativa es el backend).
- Roles afectados: los cuatro. Cada uno recibe su perfil semilla con permisos coherentes.
- Los errores 403 se muestran como aviso limpio (`{detail}`) vía el `notificationProvider`; nunca
  status crudo. Se respetan los estados vacío/carga/error/éxito y las áreas táctiles ≥44px existentes.

### Cadena de Trazabilidad
No se altera la cadena de trazabilidad (Ingreso → Kardex → Entrega → Cobro / Ingreso → CxP → Pago).
Este cambio no toca Kardex, período, costeo ni documentos de negocio.

## 4. Riesgos y Rollback

### Riesgo Principal
El **mecanismo de campos invisibles** debe garantizar que un campo no permitido **nunca se serializa**
(no que se devuelva enmascarado o read-only); un fallo aquí filtra datos sensibles (p. ej. costo) a
perfiles sin acceso. Riesgo secundario: el FK `profile` se añade sobre la tabla de usuario ya creada
en F1; si la columna se define `NOT NULL` sin backfill, la migración falla sobre usuarios existentes
(mitigación: columna nullable en DB + data migration de seed que backfillea y enforcement de "un
perfil por usuario" en servicio/seed).

### Criterio de Aborto
Condición técnica verificable, no subjetiva: si el modelo `User` de F1 **no** está establecido como
`AUTH_USER_MODEL` (comprobable con `python manage.py showmigrations accounts` y la config), **abortar**
— F2 no puede añadir el FK de perfil sin el custom user model en su sitio. También se aborta si la
migración combinada (`authz` + `accounts`) **no es reversible** (su `migrate ... zero`/reverse falla),
o si la prueba del serializer dinámico demuestra que un campo sensible aparece en el JSON para un
perfil sin acceso tras 2 intentos de corrección.

### Plan de Rollback
La migración de `authz` (incluida la data migration de seed) MUST tener `reverse_code` funcional:
`python manage.py migrate authz zero` elimina los perfiles semilla y la tabla; la migración de
`accounts` revierte el `AddField profile_id` sin pérdida de datos de negocio (no los hay aún en esta
fase). Revertir el code merge restaura el estado post-F1. No se requiere recálculo de saldos.
