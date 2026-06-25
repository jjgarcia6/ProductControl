# Propuesta: add-directory

> **Fase 4.** Capability `directory` (inicia) · `credit` (inicia) · **Depende de:** F1 (auth), F2
> (access-control) · **Desbloquea:** F6, F7, F12, F15, F16, F21 · **Requerimientos:** 3.1–3.4.
> **Fuente de verdad:** `openspec/config.yaml`. Ante conflicto, manda el `config.yaml`.

## 1. El Problema o Necesidad de Negocio

El sistema todavía no tiene dónde registrar a las entidades externas con las que opera el negocio
(clientes, proveedores, responsables de ruta, choferes). Sin ese registro maestro no se puede
avanzar a ninguna fase comercial ni financiera: un Ingreso necesita un proveedor, una Entrega un
cliente, una Ruta un chofer/responsable, y las CxC/CxP necesitan los términos de crédito del tercero.

El Directorio es la **base maestra** que consumen casi todas las fases posteriores. Es la primera fase
de dominio: entrega la ficha de tercero con su identificación validada (cédula/RUC/pasaporte), sus
roles múltiples, sus estados y sus términos de crédito por faceta. Es prioritario porque es
precondición dura de F6, F7, F12, F15, F16 y F21.

## 2. Alcance Crítico

### In-Scope (Lo que se va a construir)

- **Ficha de tercero** (`directory`): identificación (nombre/razón social, tipo CEDULA/RUC/PASAPORTE,
  número **validado** por dígito verificador), contacto (email, teléfono/WhatsApp), **roles múltiples**
  (≥1 de cliente/proveedor/responsable de ruta/chofer), estados ACTIVO → BLOQUEADO → INACTIVO con
  INACTIVO **reversible** (soft delete clase 3), y **vínculo opcional User ↔ Ficha** (1:1).
- **Términos de crédito por faceta** (`credit`): entidad `CreditTerms` con faceta CLIENTE/PROVEEDOR,
  límite, plazo en días y días de aviso; a lo sumo uno por (ficha, faceta). Aquí son **solo datos**.
- **Validadores de identificación ecuatoriana** estrenados en `apps/common/validations.py` (módulo 10/11).
- **Contratos de datos:** serializers DRF de `Ficha` y `CreditTerms` (write/read separados) → OpenAPI;
  el frontend **genera** tipos TS + Zod desde el schema.
- **Frontend:** listado de Directorio (filtro por rol/estado), formulario de ficha (roles múltiples,
  identificación, contacto), sub-formulario de términos de crédito por faceta, acciones de estado.

### Out-of-Scope (Prohibiciones Estrictas)

- **Backend:** Toda persistencia MUST ser PostgreSQL vía Django ORM. Sin SQL raw salvo justificación explícita.
- **Backend:** Las transacciones multi-tabla (ficha + términos, transición + auditoría) MUST usar `transaction.atomic()` con rollback total.
- **Backend:** La ficha de Directorio usa soft delete **clase 3** (estado INACTIVO); MUST NOT heredar `SoftDeleteModel` ni usar `deleted_at`. `CreditTerms` es dato dependiente: sin máquina de estado ni soft delete propio.
- **Frontend:** Los colores hardcodeados MUST NOT usarse; todo estilo MUST usar tokens del theme (shadcn/Tailwind) con modo claro y oscuro.
- **Seguridad:** Las credenciales MUST NOT almacenarse en el código; MUST gestionarse vía `.env` / GCP Secret Manager.
- **Calidad:** Las refactorizaciones paralelas ajenas al dominio de este cambio MUST NOT introducirse (YAGNI).
- **Dominio — diferido a fases posteriores:**
  - **Comportamiento de crédito** (vencimiento → alerta → bloqueo automático → escalamiento) → F21 (`add-credit-control`). En F4 los términos son solo datos.
  - **Regla "bloqueo genera entrega en BORRADOR"** → F16 (`add-deliveries`). En F4 BLOQUEADO solo existe como estado y transición manual.
  - **Lista de precios asignada** → F6 (`add-pricing`), que modifica `directory` para añadir el FK. La tabla `PriceList` no existe aún; el FK NO se crea en F4.
  - Sin historial de cambios de la ficha más allá de la auditoría existente (`@audit`).

## 3. Evaluación de Impacto

### Modelo de Datos (PostgreSQL)

- **Tabla `directory_fichas`** (app `directory`, nueva): identificación (`identification_type`,
  `identification_number`), contacto (`email`, `phone`), `roles` (ArrayField de enum, índice GIN),
  `status` (ACTIVO/BLOQUEADO/INACTIVO, default ACTIVO), `user` (O2O nullable a `accounts.User`,
  `on_delete=SET_NULL`). **Unicidad parcial** del número de identificación entre fichas no inactivas
  (`UniqueConstraint(identification_number, condition=~Q(status="INACTIVO"))`). Migración reversible.
- **Tabla `credit_terms`** (app `credit`, nueva): FK a `Ficha`, `facet` (CLIENTE/PROVEEDOR),
  `credit_limit` (Decimal, default 0), `term_days` (int, default 0), `notice_days` (int, default 2),
  con `UniqueConstraint(ficha, facet)`. Migración reversible.
- **Catálogo de autorización:** se registra el módulo `directory` (constante `MODULE_DIRECTORY = "directory"`,
  estilo kebab inglés como `access-control`) y sus acciones en `apps/authz/catalog.py` (extensión de F2;
  sin tocar el seed existente).
- **Invariantes:** no toca Kardex, período cerrado, costeo ni documentos con fecha (la ficha es
  maestro). Soft delete clase 3. Ver checklist completa en `design.md` §1.

### Lógica de Negocio y API

- **Endpoints DRF nuevos** (derivados de flujos de estado, no CRUD genérico): CRUD acotado de ficha +
  transiciones explícitas (`block`/`unblock`/`deactivate`/`reactivate`/`link-user`); crear/editar
  términos de crédito. Detalle en `design.md` §2.
- **Servicios:** `apps/directory/services.py` (validación de identificación vía `apps.common.validations`,
  transiciones de estado, vínculo con usuario, unicidad) y `apps/credit/services.py` (integridad
  faceta↔rol, unicidad por (ficha, faceta)). ViewSets delgados que delegan. Auditoría con `@audit`.
- **No** se modifica FIFO, costeo, merma, ni la aplicación de cobros/pagos (no existen aún).

### Flujo del Usuario (UI)

- **Recursos/rutas nuevos (protegidos):** `/directory` (listado con filtros por rol y estado;
  excluye INACTIVO por defecto) y el formulario de ficha (alta/edición + sub-formulario de términos
  de crédito por faceta + acciones de estado).
- **Roles afectados:** Jefe y Supervisor gestionan el Directorio y las condiciones comerciales
  (la autorización efectiva se resuelve **por perfil**, no por el `role` nominal — F2).
- Estados de pantalla vacío/carga/error/éxito REQUIRED; áreas táctiles ≥44px; inputs ≥16px en iOS.

### Cadena de Trazabilidad

No se altera la cadena de trazabilidad (Ingreso → Kardex → Entrega → Cobro / Ingreso → CxP → Pago):
la ficha es un dato maestro, no un documento con efectos en Kardex o saldos. F4 **provee** la entidad
que esas cadenas referenciarán en fases posteriores, sin participar todavía en ningún flujo.

## 4. Riesgos y Rollback

### Riesgo Principal

El algoritmo del **dígito verificador ecuatoriano** (enrutado por tipo: módulo 10 para cédula/RUC de
persona natural; módulo 11 para sociedades privadas —3er dígito 9— y sector público —3er dígito 6—).
Un validador incorrecto rechaza identificaciones válidas o admite inválidas, contaminando la base
maestra. Se mitiga aislándolo en funciones puras en `apps/common/validations.py` con cobertura alta de
casos válidos/inválidos por cada variante antes de cablearlo al serializer.

### Criterio de Aborto

Si el catálogo de módulos/acciones de `access-control` (F2, `apps/authz/catalog.py`) no está
disponible, **abortar**: la ficha no puede registrar su módulo ni proteger sus acciones por perfil sin
él. Adicionalmente, abortar si las pruebas de los validadores de identificación o de los endpoints
fallan tras 2 intentos de corrección, o si la migración Django no es reversible (el downgrade falla).

### Plan de Rollback

Ambas migraciones (`directory`, `credit`) son **CreateModel**, con reverse estándar de Django (drop de
las tablas nuevas); no hay data migration ni recálculo de saldos. El registro del módulo en
`apps/authz/catalog.py` es aditivo y se revierte quitando la entrada. Rollback = revertir el PR +
`migrate directory zero` / `migrate credit zero`.
