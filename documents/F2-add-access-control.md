# Change: add-access-control — Fase 2

**Capability:** `access-control` (inicia) · **Depende de:** F1 (auth) · **Desbloquea:** F3, F4, F5, F8 (y precondición de permisos para el resto)
**Fuente de verdad:** `openspec/config.yaml`. Ante conflicto, manda el `config.yaml`.
**Requerimientos:** 2.4, 2.5.

> **Cómo usar este archivo.** Consolida los cuatro artefactos del change. Cada sección de primer nivel mapea a un archivo dentro de `openspec/changes/add-access-control/`:
> - `## 1) PROPOSAL` → `proposal.md`
> - `## 2) SPECS` → `specs/access-control/spec.md` (delta)
> - `## 3) DESIGN` → `design.md`
> - `## 4) TASKS` → `tasks.md`
>
> Requirements en RFC 2119 (MUST/MUST NOT/SHALL); Scenarios en español (DADO/CUANDO/ENTONCES). Código e identificadores en inglés; documentación en español.

---

## 1) PROPOSAL → proposal.md

### Intent

Establecer el control de acceso por **perfil** sobre la identidad creada en F1. El requerimiento gestiona los permisos a nivel de perfil (2.4) y habilita la auto-aprobación individualmente en el perfil (6.5), de modo que la autorización no puede quedar clavada en código. Este change entrega la entidad Perfil configurable, su asignación a usuarios, el motor de autorización por (módulo, acción), el mecanismo de campos invisibles y la capacidad de auto-aprobación. Es precondición de permisos para todas las fases siguientes.

### Decisión de alcance (opción C, validada)

Perfil configurable, pero acotado: permisos por (módulo, acción) tomados de un **catálogo conocido y extensible**, más flags de capacidad. No es un motor RBAC genérico arbitrario (eso violaría KISS/YAGNI), ni roles con permisos hardcodeados (eso contradiría "gestionar a nivel de perfil"). Los cuatro roles del sistema se materializan como **perfiles semilla**.

### Scope (qué cambia)

- Entidad **`Profile`**: nombre único, permisos por (módulo, acción), flags de capacidad (auto-aprobación), y registro de campos sensibles ocultos.
- **Asignación** usuario → perfil (FK en el modelo User de F1).
- **Motor de autorización** (permission classes de DRF) que resuelve por el perfil del usuario.
- **Mecanismo de campos invisibles:** serializer dinámico que **omite** de la respuesta los campos sensibles que el perfil no puede ver.
- **Flag de auto-aprobación** como capacidad consultable.
- **Catálogo de módulos/acciones** y **registro de campos sensibles** como estructura central extensible por fase.
- **Cuatro perfiles semilla** (Jefe, Supervisor, Responsable de ruta, Usuario).

### Impacto en el modelo de datos (antes que UI — DIP)

- Nueva tabla `Profile` (app `authz`). Soft delete clase 2 (catálogo configurable).
- FK `profile` añadido al modelo `User` (app `accounts`) → migración sobre ambas apps, reversible.
- Estructura de permisos por (módulo, acción) y de campos sensibles. El catálogo arranca con los módulos ya existentes (identidad); cada fase posterior registra su módulo, sus acciones y sus campos sensibles.

### Relación con el `role` de F1 (reconciliación)

`User.role` (F1) queda como **clasificación nominal** de alto nivel. `Profile` (F2) es la **fuente de verdad de la autorización**. La autorización del sistema MUST resolverse siempre por el perfil, nunca por el `role` directamente. En el seed, cada role recibe su perfil homónimo; el cliente puede crear perfiles adicionales más adelante sin tocar el `role`.

### Fuera de alcance

- El campo `cost` invisible concreto y las reglas de auto-aprobación de ingreso → F12 (`intake`). Aquí solo el mecanismo y la capacidad.
- La **UI de administración de perfiles** (crear/editar perfil, asignar permisos) → F3 (`user-management`), que es la consola de identidad. F2 entrega modelo, mecanismo, seed y endpoints de lectura/asignación.

### Verificación de invariantes

No toca Kardex, período, costeo ni documentos. Respeta el contrato de errores uniforme (403 → `{detail}`; validación → `{campo: [mensajes]}`) y el soft delete de tres clases (Profile = clase 2).

### Criterio de aborto (verificable)

Si el modelo `User` de F1 no está establecido como `AUTH_USER_MODEL` (verificable con `showmigrations accounts` y la config), abortar: F2 no puede añadir el FK de perfil sin el custom user model en su sitio.

---

## 2) SPECS → specs/access-control/spec.md

# Delta para la capability `access-control`

## ADDED Requirements

### Requirement: Perfil de permisos
El sistema MUST permitir definir perfiles que agrupan permisos. Cada perfil MUST tener un nombre único y un conjunto de permisos por (módulo, acción) tomados de un catálogo conocido, además de flags de capacidad. Los perfiles son catálogo configurable (soft delete clase 2). Los errores de validación MUST seguir el contrato uniforme.

#### Scenario: Crear un perfil con permisos
- DADO un catálogo de módulos y acciones conocido
- CUANDO se crea un perfil con un nombre único y un conjunto de permisos
- ENTONCES el sistema persiste el perfil con sus permisos
- Y el perfil queda disponible para asignación

#### Scenario: Nombre de perfil duplicado
- DADO un perfil existente con un nombre
- CUANDO se intenta crear otro perfil con el mismo nombre
- ENTONCES el sistema responde 400 con `{campo: [mensajes]}` en el campo del nombre

### Requirement: Asignación de perfil a usuario
Cada usuario MUST estar asociado a exactamente un perfil. La autorización del sistema MUST resolverse por el perfil del usuario, no por su `role` nominal.

#### Scenario: Usuario con perfil asignado
- DADO un usuario y un perfil existentes
- CUANDO se asigna el perfil al usuario
- ENTONCES las decisiones de autorización del usuario se resuelven según ese perfil

#### Scenario: Identidad incluye el perfil
- DADO un usuario autenticado con perfil asignado
- CUANDO consulta su identidad
- ENTONCES la respuesta incluye el perfil del usuario además de su rol

### Requirement: Autorización por módulo y acción
El sistema MUST permitir o denegar cada acción sobre un módulo según el perfil del usuario. Cuando se deniega, MUST responder 403 con `{detail}` en español.

#### Scenario: Acción permitida por el perfil
- DADO un usuario cuyo perfil permite una acción sobre un módulo
- CUANDO ejecuta esa acción
- ENTONCES el sistema la autoriza

#### Scenario: Acción denegada por el perfil
- DADO un usuario cuyo perfil no permite una acción sobre un módulo
- CUANDO intenta ejecutar esa acción
- ENTONCES el sistema responde 403 con `{detail}` en español

### Requirement: Campos invisibles por perfil
El sistema MUST omitir de la respuesta serializada los campos registrados como sensibles cuando el perfil del usuario no tiene permiso de verlos. Un campo invisible MUST NOT aparecer en la respuesta (no basta con marcarlo de solo lectura).

#### Scenario: Campo sensible omitido para perfil sin acceso
- DADO un recurso con un campo registrado como sensible
- Y un usuario cuyo perfil no puede ver ese campo
- CUANDO consulta el recurso
- ENTONCES la respuesta no incluye ese campo

#### Scenario: Campo sensible visible para perfil con acceso
- DADO un recurso con un campo registrado como sensible
- Y un usuario cuyo perfil puede ver ese campo
- CUANDO consulta el recurso
- ENTONCES la respuesta incluye ese campo con su valor

### Requirement: Capacidad de auto-aprobación
El perfil MUST exponer un flag de auto-aprobación consultable. Aquí la capacidad es solo estructural; su aplicación efectiva (llevar un ingreso de BORRADOR a VERIFICADO sin supervisor) se define en `intake`.

#### Scenario: Perfil con auto-aprobación habilitada
- DADO un perfil con el flag de auto-aprobación habilitado
- CUANDO se consulta la capacidad del perfil
- ENTONCES el sistema indica que la auto-aprobación está habilitada

### Requirement: Perfiles semilla del sistema
El sistema MUST proveer cuatro perfiles semilla correspondientes a los roles Jefe, Supervisor, Responsable de ruta y Usuario, con permisos por defecto coherentes con cada rol.

#### Scenario: Perfiles semilla disponibles tras la inicialización
- DADO un sistema recién inicializado
- CUANDO se siembran los perfiles del sistema
- ENTONCES existen los cuatro perfiles (Jefe, Supervisor, Responsable de ruta, Usuario)
- Y cada uno queda disponible para asignación

---

## 3) DESIGN → design.md

### Capa de datos

- **App `authz`** (autorización) para `Profile` y el motor de permisos. La capability OpenSpec es `access-control`; la app Django se llama `authz` por SRP y para no colisionar con los permisos nativos de Django.
- **`Profile`**: `name` (único), descripción opcional, relación de permisos por (módulo, acción), flags de capacidad (`auto_approval`), y la relación con campos sensibles visibles. Soft delete clase 2 (`deleted_at` + manager que filtra + índice único parcial sobre `name`).
- **FK `profile`** en `accounts.User` (apunta a `authz.Profile`). Migración sobre ambas apps, reversible.
- **Catálogo de módulos/acciones:** constantes centralizadas (no hardcoding disperso), extensibles por fase. F2 registra los módulos ya existentes (identidad/perfiles); cada fase posterior añade su módulo, sus acciones y sus campos sensibles a este catálogo.
- **Registro de campos sensibles:** estructura central que asocia (recurso, campo) → permiso de visibilidad. F2 entrega el mecanismo; el primer campo real (`cost` en ingresos) lo registra F12.

### Capa de API

- **Contrato OpenAPI primero:** endpoints de lectura de perfiles y de asignación perfil↔usuario anotados con `drf-spectacular`. La administración completa (crear/editar perfil) es F3; aquí, lectura y asignación.
- **Permission classes de DRF** custom que resuelven por el perfil del usuario (módulo + acción del endpoint). Devuelven 403 `{detail}` al denegar.
- **Serializer dinámico** (mixin en `apps/common` o `authz`) que, en tiempo de serialización, **elimina** del output los campos sensibles que el perfil no puede ver. No los marca read-only: los omite.
- **Lógica en services:** la resolución de permisos y la construcción de la lista de campos visibles viven en `apps/authz/services.py`; viewsets y serializers delgados.

### Contrato OpenAPI y campos opcionales (nota importante)

Como el serializer omite campos según perfil, un mismo recurso puede responder con o sin el campo sensible. El `schema.yml` MUST declarar esos campos como **opcionales** (pueden faltar), y el frontend MUST tolerar su ausencia sin romper. El tipo generado (TS + Zod) marca el campo como opcional. Esto evita que el front asuma la presencia de un campo que su perfil no recibe.

### Capa de frontend

- **Gating por perfil:** el frontend oculta acciones/columnas según la identidad (perfil) devuelta por `me`. El ocultamiento de UI es **defensa secundaria**; la autoritativa es el backend (un campo omitido por el serializer no llega nunca al cliente).
- **Sin pantallas de administración de perfiles aquí** (van en F3). F2 solo consume la identidad enriquecida con el perfil para condicionar la UI.
- Errores 403 mostrados como aviso limpio (`{detail}`) por el `notificationProvider`; nada de status crudo.

### Seguridad

- La autorización es **server-side**: ninguna decisión de acceso depende solo del frontend.
- Los campos sensibles se omiten en el backend; no se confía en el cliente para ocultarlos.
- 403 con `{detail}` en español; sin filtrar qué permiso faltó si eso revela estructura interna sensible (mensaje genérico de permiso).

### Qué NO se hace (YAGNI)

Sin motor RBAC genérico con permisos arbitrarios sobre objetos; sin jerarquías de roles; sin permisos por instancia (row-level). El catálogo es conocido y se extiende por fase. La UI de administración de perfiles es F3.

---

## 4) TASKS → tasks.md

> Orden obligatorio del `config.yaml`: Contrato (OpenAPI) → Migraciones Django → Backend (services) → Frontend → Seguridad → Pruebas. Cada tarea nombra el archivo/módulo exacto. Definition of done global: todos los gates del pipeline en verde localmente antes de declarar el change completo.

### A. Contrato y modelo (OpenAPI + datos)
- [ ] A.1 Crear la app `authz` (`apps/authz/`) y definir `Profile` en `apps/authz/models.py` (nombre único, permisos por módulo/acción, flag `auto_approval`, relación de campos sensibles visibles, soft delete clase 2).
- [ ] A.2 Añadir el FK `profile` al modelo `accounts.User`.
- [ ] A.3 Definir el catálogo central de módulos/acciones y el registro de campos sensibles como constantes centralizadas (extensibles por fase) en `apps/authz/catalog.py`.
- [ ] A.4 Definir serializers de `Profile` (lectura) y de asignación perfil↔usuario en `apps/authz/serializers.py`.
- [ ] A.5 Anotar los endpoints con `drf-spectacular`, marcando los campos sensibles como opcionales en el schema; regenerar `schema.yml`.

### B. Migraciones
- [ ] B.1 `makemigrations authz accounts` (Profile + FK en User); confirmar reversibilidad (upgrade + downgrade).
- [ ] B.2 `migrate` y verificar arranque limpio.

### C. Backend (services + autorización)
- [ ] C.1 Implementar la resolución de permisos por perfil en `apps/authz/services.py` (módulo + acción → permitido/denegado).
- [ ] C.2 Implementar las permission classes de DRF en `apps/authz/permissions.py` que devuelven 403 `{detail}` al denegar.
- [ ] C.3 Implementar el serializer dinámico de campos invisibles (mixin) que omite del output los campos sensibles no permitidos por el perfil.
- [ ] C.4 Implementar los endpoints de lectura de perfiles y de asignación perfil↔usuario en `apps/authz/views.py` (delgados, delegan en services); registrar rutas.
- [ ] C.5 Implementar el seed de los cuatro perfiles del sistema (Jefe, Supervisor, Responsable de ruta, Usuario) con permisos por defecto.
- [ ] C.6 Enriquecer el endpoint `me` (de F1) para incluir el perfil del usuario.

### D. Frontend
- [ ] D.1 Regenerar tipos + Zod desde `schema.yml` (`npm run codegen`), con los campos sensibles como opcionales.
- [ ] D.2 Consumir el perfil desde `me` en el store de sesión y exponer helpers de gating (¿puede ver / puede hacer?) en `src/features/auth/`.
- [ ] D.3 Aplicar el gating a acciones/columnas en los componentes que ya existan (defensa secundaria); manejar 403 como aviso limpio.

### E. Seguridad
- [ ] E.1 Verificar que toda decisión de acceso es server-side y que los campos invisibles nunca se serializan para perfiles sin permiso (no solo ocultos en UI).
- [ ] E.2 Verificar que los 403 no filtran estructura interna sensible (mensaje genérico de permiso).

### F. Pruebas (gate)
- [ ] F.1 Tests de backend en `apps/authz/tests/` cubriendo todos los Scenarios (crear perfil; nombre duplicado; asignación; identidad con perfil; acción permitida/denegada → 403; campo sensible omitido/visible; auto-aprobación consultable; perfiles semilla).
- [ ] F.2 Test específico del serializer dinámico: el campo sensible **no aparece** en el JSON para un perfil sin acceso (no basta read-only).
- [ ] F.3 Tests de frontend (Vitest + RTL) del gating por perfil; tolerancia a la ausencia de campos opcionales.
- [ ] F.4 Ejecutar y dejar en verde: `ruff`, `mypy --strict`, `bandit`, `pip-audit`, `pytest` (cobertura ≥80%); `eslint`, `tsc`, `npm audit`, `vitest`. Confirmar antes de declarar el change completo.
