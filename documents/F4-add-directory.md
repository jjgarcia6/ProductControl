# Change: add-directory — Fase 4

**Capability:** `directory` (inicia) · `credit` (inicia) · **Depende de:** F1 (auth), F2 (access-control) · **Desbloquea:** F6, F7, F12, F15, F16, F21
**Fuente de verdad:** `openspec/config.yaml`. Ante conflicto, manda el `config.yaml`.
**Requerimientos:** 3.1–3.4.

> **Cómo usar este archivo.** Consolida los cuatro artefactos del change. Cada sección de primer nivel mapea a un archivo dentro de `openspec/changes/add-directory/`:
> - `## 1) PROPOSAL` → `proposal.md`
> - `## 2) SPECS` → dos deltas: `specs/directory/spec.md`, `specs/credit/spec.md`
> - `## 3) DESIGN` → `design.md`
> - `## 4) TASKS` → `tasks.md`
>
> Requirements en RFC 2119 (MUST/MUST NOT/SHALL); Scenarios en español (DADO/CUANDO/ENTONCES). Código e identificadores en inglés; documentación en español.

---

## 1) PROPOSAL → proposal.md

### Intent

Entregar el Directorio: el registro centralizado de toda entidad externa (cliente, proveedor, responsable de ruta, chofer), con su identificación validada, sus roles múltiples, sus estados y sus términos de crédito. Es la primera fase de dominio y la base maestra que consumen casi todas las fases comerciales y financieras: ingresos (proveedor), entregas y pedidos (cliente), rutas (chofer/responsable), CxC/CxP (crédito).

### Scope (qué cambia)

- **Ficha de tercero** (`directory`): identificación (nombre/razón social, tipo cédula/RUC/pasaporte, número validado), contacto (email, teléfono/WhatsApp), **roles múltiples** (≥1 de cliente/proveedor/responsable de ruta/chofer).
- **Estados** ACTIVO → BLOQUEADO → INACTIVO, con INACTIVO **reversible**. Soft delete clase 3 (la baja es el estado, no `deleted_at`).
- **Vínculo opcional User ↔ Ficha** (1:1).
- **Términos de crédito por faceta** (`credit`): entidad `CreditTerms` con faceta CLIENTE/PROVEEDOR, límite, plazo en días y días de aviso; a lo sumo uno por (ficha, faceta).
- **Validadores de identificación ecuatoriana** estrenados en `apps/common/validations.py`.

### Decisiones de modelado (validadas)

- **Roles** como `ArrayField` de un enum (una columna, índice GIN, validación ≥1).
- **Vínculo** como `OneToOneField` en la Ficha hacia el User (`Ficha.user`, acceso reverso `user.ficha`), `on_delete=SET_NULL`.
- **Crédito separado por faceta** (`CreditTerms`, no campos en la ficha): cliente y proveedor tienen, cada uno, su límite + plazo + días de aviso. Coherente con que la fecha de vencimiento de CxP usa el plazo del proveedor y la de CxC el del cliente.

### Impacto en el modelo de datos (antes que UI — DIP)

- Tabla `Ficha` (app `directory`): identificación, contacto, `roles` (array), `status`, `user` (O2O nullable a `accounts.User`). Unicidad de número de identificación entre fichas no inactivas (índice único parcial). Migración reversible.
- Tabla `CreditTerms` (app `credit`): FK a `Ficha`, `facet` (CLIENTE/PROVEEDOR), `credit_limit`, `term_days`, `notice_days`, con `unique(ficha, facet)`.
- Módulo `directory` (y sus acciones) registrado en el catálogo de `access-control` (F2).

### Fuera de alcance

- **Comportamiento de crédito** (vencimiento → alerta → bloqueo automático → escalamiento) → F21 (`add-credit-control`). En F4 los términos son solo datos.
- **Regla "bloqueo genera entrega en BORRADOR"** → F16 (`add-deliveries`). En F4 BLOQUEADO solo existe como estado y transición manual.
- **Lista de precios asignada** → F6 (`add-pricing`), que modifica `directory` para añadir el FK. La tabla `PriceList` no existe aún.

### Verificación de invariantes

- Soft delete **clase 3** (Ficha = estado INACTIVO, nunca `deleted_at`).
- No toca Kardex, período cerrado, costeo ni documentos (la ficha es maestro, no documento con fecha).
- Errores por el contrato uniforme; permisos por perfil (F2).

### Criterio de aborto (verificable)

Si el catálogo de módulos/acciones de `access-control` (F2, `apps/authz/catalog.py`) no está disponible, abortar: la ficha no puede registrar su módulo ni proteger sus acciones por perfil sin él.

---

## 2) SPECS

### 2.1 → specs/directory/spec.md

# Delta para la capability `directory`

## ADDED Requirements

### Requirement: Ficha de tercero
La ficha MUST registrar nombre o razón social, tipo de identificación (cédula, RUC o pasaporte) y un número de identificación válido para ese tipo. El número MUST ser único entre las fichas no inactivas. La validación de cédula y RUC MUST usar el dígito verificador; el pasaporte se acepta sin checksum. Los errores MUST seguir el contrato uniforme.

#### Scenario: Crear una ficha con identificación válida
- DADO un tipo de identificación y un número válido para ese tipo
- CUANDO se crea la ficha con al menos un rol
- ENTONCES el sistema persiste la ficha en estado ACTIVO

#### Scenario: Identificación con dígito verificador inválido
- DADO un número de cédula o RUC que no pasa el dígito verificador
- CUANDO se intenta crear la ficha
- ENTONCES el sistema responde 400 con `{campo: [mensajes]}` en el campo del número

#### Scenario: Número de identificación duplicado
- DADO una ficha no inactiva con un número de identificación
- CUANDO se intenta crear otra ficha con el mismo número
- ENTONCES el sistema responde 400 con `{campo: [mensajes]}` en el campo del número

### Requirement: Roles de la ficha
La ficha MUST tener al menos un rol entre cliente, proveedor, responsable de ruta y chofer, y MAY tener varios. El sistema MUST rechazar una ficha sin rol.

#### Scenario: Ficha con múltiples roles
- DADO una entidad que es cliente y proveedor
- CUANDO se crea la ficha con ambos roles
- ENTONCES el sistema persiste la ficha con los dos roles

#### Scenario: Ficha sin rol
- CUANDO se intenta crear una ficha sin ningún rol
- ENTONCES el sistema responde 400 con `{campo: [mensajes]}` en el campo de roles

### Requirement: Contacto de la ficha
La ficha MUST poder almacenar email y teléfono/WhatsApp. Si se provee email, MUST tener formato válido.

#### Scenario: Email con formato inválido
- DADO un email mal formado
- CUANDO se guarda la ficha
- ENTONCES el sistema responde 400 con `{campo: [mensajes]}` en el campo del email

### Requirement: Estados de la ficha
La ficha MUST transitar entre ACTIVO, BLOQUEADO e INACTIVO. ACTIVO y BLOQUEADO son intercambiables por un perfil autorizado; INACTIVO es la baja lógica (soft delete clase 3) y MUST ser reversible a ACTIVO. Las fichas INACTIVO MUST quedar excluidas de los listados operativos por defecto.

#### Scenario: Bloquear y reactivar una ficha
- DADO una ficha ACTIVO
- CUANDO un perfil autorizado la bloquea
- ENTONCES la ficha queda en BLOQUEADO
- Y puede volver a ACTIVO

#### Scenario: Baja lógica reversible
- DADO una ficha ACTIVO
- CUANDO un perfil autorizado la da de baja
- ENTONCES la ficha queda en INACTIVO y deja de aparecer en los listados operativos
- Y puede reactivarse a ACTIVO

### Requirement: Vínculo opcional con un usuario
Una ficha MAY estar vinculada a un usuario del sistema en relación uno a uno. La baja del usuario MUST NOT borrar la ficha.

#### Scenario: Vincular una ficha a un usuario
- DADO una ficha y un usuario sin ficha previa
- CUANDO se vinculan
- ENTONCES el usuario accede a su ficha y la ficha a su usuario

### 2.2 → specs/credit/spec.md

# Delta para la capability `credit`

## ADDED Requirements

### Requirement: Términos de crédito por faceta
El sistema MUST permitir definir términos de crédito por faceta (CLIENTE o PROVEEDOR) para una ficha, con límite de crédito (default 0), plazo en días (default 0) y días de aviso de vencimiento (default 2). MUST existir a lo sumo un juego de términos por (ficha, faceta). Aquí los términos son solo datos; el comportamiento de vencimiento y bloqueo se define en `credit-control`.

#### Scenario: Definir términos de crédito de cliente
- DADO una ficha con rol cliente
- CUANDO se definen sus términos de crédito de faceta CLIENTE
- ENTONCES el sistema los persiste asociados a la ficha

#### Scenario: Términos duplicados para la misma faceta
- DADO una ficha con términos de faceta PROVEEDOR
- CUANDO se intenta crear otro juego de faceta PROVEEDOR para la misma ficha
- ENTONCES el sistema responde con un error de conflicto del contrato uniforme

### Requirement: Integridad entre faceta y rol
El sistema MUST NOT permitir términos de crédito de faceta CLIENTE si la ficha no tiene rol cliente, ni de faceta PROVEEDOR si no tiene rol proveedor.

#### Scenario: Términos de cliente sobre una ficha sin rol cliente
- DADO una ficha que solo tiene rol proveedor
- CUANDO se intenta definir términos de faceta CLIENTE
- ENTONCES el sistema responde 400 con `{campo: [mensajes]}` indicando la incompatibilidad

---

## 3) DESIGN → design.md

### Validadores de identificación (`apps/common/validations.py`)

- Se crea el módulo `apps/common/validations.py` (según `config.yaml`). Enruta por tipo: cédula y RUC de persona natural por **módulo 10**; sociedades privadas (3er dígito = 9) y sector público (3er dígito = 6) por **módulo 11**; pasaporte sin checksum. Funciones puras, testeables aisladas.
- El serializer de la ficha invoca el validador según el tipo y devuelve el error por campo (contrato uniforme).

### Capa de datos

- **App `directory`** — `Ficha`:
  - Identificación: `identification_type` (choices CEDULA/RUC/PASAPORTE), `identification_number` (CharField). Unicidad: `UniqueConstraint(identification_number, condition=~Q(status=INACTIVO))`.
  - `roles`: `ArrayField(CharField(choices))` con validación ≥1; índice GIN para consultar por rol.
  - Contacto: `email` (validado), `phone`.
  - `status`: choices ACTIVO/BLOQUEADO/INACTIVO (default ACTIVO). **No** hereda `SoftDeleteModel` (clase 2); la baja es el estado (clase 3).
  - `user`: `OneToOneField("accounts.User", null=True, blank=True, on_delete=SET_NULL, related_name="ficha")`.
- **App `credit`** — `CreditTerms`:
  - `ficha` (FK), `facet` (choices CLIENTE/PROVEEDOR), `credit_limit` (Decimal, default 0), `term_days` (int, default 0), `notice_days` (int, default 2).
  - `UniqueConstraint(ficha, facet)`.
  - La validación faceta↔rol vive en el service/serializer (la ficha debe tener el rol correspondiente).
- Migraciones reversibles en ambas apps.

### Capa de API

- **Contrato OpenAPI primero:** endpoints de ficha (CRUD + transiciones de estado) y de términos de crédito, anotados con `drf-spectacular`; regenerar `schema.yml`.
- **Permisos por perfil:** registrar el módulo `DIRECTORY` y sus acciones en `apps/authz/catalog.py`; proteger los endpoints con la permission class de F2. La asignación de términos de crédito (condición comercial) la realiza un perfil autorizado (supervisor/jefe), igual que en el requerimiento.
- **Lógica en services:** validación de identificación, transiciones de estado, integridad faceta↔rol y unicidad viven en `apps/directory/services.py` y `apps/credit/services.py`; viewsets delgados.
- **Listados:** excluyen INACTIVO por defecto, con parámetro explícito para incluirlas.

### Capa de frontend

- **Validación de identificación:** Zod (generado del OpenAPI) valida formato y longitud por tipo (cédula 10 dígitos, RUC 13, numérico); **el dígito verificador lo valida el backend** (no se duplica el algoritmo en el cliente — DRY). El error del backend se mapea al campo.
- **Pantallas de Directorio:** listado con filtro por rol y estado; formulario de ficha con selección múltiple de roles, identificación, contacto; sub-formulario de **términos de crédito por faceta** que solo ofrece la faceta cuyo rol tiene la ficha. Acciones de estado (bloquear/reactivar/dar de baja) según perfil.
- Estados vacío/carga/error/éxito; tokens del theme; `FieldError` compartido; inputs ≥16px iOS.

### Seguridad

- Identificación validada **server-side** (la del cliente es conveniencia).
- Acceso por perfil; los listados y acciones respetan los permisos de F2.

### Qué NO se hace (YAGNI)

Sin comportamiento de crédito (F21), sin lista de precios (F6), sin la regla de entrega-en-BORRADOR por bloqueo (F16). Sin historial de cambios de la ficha más allá de la auditoría existente.

---

## 4) TASKS → tasks.md

> Orden obligatorio del `config.yaml`: Contrato (OpenAPI) → Migraciones Django → Backend (services) → Frontend → Seguridad → Pruebas. Cada tarea nombra el archivo/módulo exacto. Definition of done global: todos los gates del pipeline en verde localmente antes de declarar el change completo.

### A. Contrato y modelo (OpenAPI + datos)
- [ ] A.1 Crear `apps/common/validations.py` con los validadores de cédula/RUC/pasaporte (funciones puras, enrutadas por tipo y dígito verificador).
- [ ] A.2 Crear la app `directory` y el modelo `Ficha` (identificación, roles ArrayField, contacto, status, O2O `user`), con la unicidad parcial del número entre fichas no inactivas y el índice GIN de roles.
- [ ] A.3 Crear la app `credit` y el modelo `CreditTerms` (ficha, facet, límite, plazo, días de aviso) con `unique(ficha, facet)`.
- [ ] A.4 Definir serializers de `Ficha` (read/write, con validación de identificación y ≥1 rol) y de `CreditTerms` (con validación faceta↔rol) en sus apps.
- [ ] A.5 Registrar el módulo `DIRECTORY` y sus acciones en `apps/authz/catalog.py`.
- [ ] A.6 Anotar los endpoints con `drf-spectacular` y regenerar `schema.yml`.

### B. Migraciones
- [ ] B.1 `makemigrations directory credit`; confirmar reversibilidad (upgrade + downgrade).
- [ ] B.2 `migrate` y verificar arranque limpio.

### C. Backend (services + vistas)
- [ ] C.1 Implementar en `apps/directory/services.py` la validación de identificación (vía `apps/common/validations`), las transiciones de estado (ACTIVO↔BLOQUEADO, →INACTIVO reversible) y el vínculo con usuario.
- [ ] C.2 Implementar en `apps/credit/services.py` la creación/edición de términos con la integridad faceta↔rol y la unicidad por (ficha, faceta).
- [ ] C.3 Implementar los viewsets delgados de ficha (CRUD + acciones de estado) y de términos de crédito, protegidos por la permission class de F2 (módulo `DIRECTORY`); registrar rutas. Listados excluyen INACTIVO por defecto.
- [ ] C.4 Verificar que todos los errores salen por el contrato uniforme.

### D. Frontend
- [ ] D.1 Regenerar tipos + Zod desde `schema.yml` (`npm run codegen`).
- [ ] D.2 Construir el listado de Directorio en `src/features/directory/` (filtros por rol y estado, exclusión de INACTIVO por defecto).
- [ ] D.3 Construir el formulario de ficha (roles múltiples, identificación con validación de formato Zod, contacto) y el sub-formulario de términos de crédito por faceta (solo facetas cuyo rol tiene la ficha).
- [ ] D.4 Implementar las acciones de estado (bloquear/reactivar/dar de baja) según perfil; mapear los errores del backend a los campos.
- [ ] D.5 Estados vacío/carga/error/éxito, tokens del theme, `FieldError` compartido, inputs ≥16px iOS.

### E. Seguridad
- [ ] E.1 Verificar que la validación de identificación es efectiva server-side (no se confía en el cliente).
- [ ] E.2 Verificar que las acciones del Directorio respetan los permisos por perfil (F2).

### F. Pruebas (gate)
- [ ] F.1 Tests de `apps/common/validations.py` con casos válidos e inválidos de cédula, RUC (natural, sociedad, público) y pasaporte (funciones puras; cobertura alta).
- [ ] F.2 Tests de backend en `apps/directory/tests/` y `apps/credit/tests/` cubriendo todos los Scenarios (identificación válida/inválida/duplicada; roles múltiples/sin rol; email inválido; estados bloquear/reactivar/baja reversible; vínculo usuario; términos por faceta; faceta duplicada → conflicto; integridad faceta↔rol → 400).
- [ ] F.3 Tests de frontend (Vitest + RTL) del formulario de ficha y del sub-formulario de crédito por faceta.
- [ ] F.4 Ejecutar y dejar en verde: `ruff`, `mypy --strict`, `bandit`, `pip-audit`, `pytest` (cobertura ≥80%); `eslint`, `tsc`, `npm audit`, `vitest`. Confirmar antes de declarar el change completo.
