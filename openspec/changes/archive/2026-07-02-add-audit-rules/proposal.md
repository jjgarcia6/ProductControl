# Propuesta: add-audit-rules

<!-- Fase 10 · Capability: audit · Depende de: F1 · Desbloquea: F11, F12 y todo service con correcciones campo-nivel (F13–F24) · Requerimiento: 2.3 -->
<!-- Fuente de verdad: openspec/config.yaml. Ante conflicto, manda config.yaml. -->

## 1. El Problema o Necesidad de Negocio

El requisito **2.3** exige que toda corrección sobre un documento generado deje un rastro de
auditoría **a nivel de campo**: fecha/hora, usuario, campo modificado, valor anterior y valor nuevo.

Hoy el mecanismo del bootstrap **no puede cumplirlo**. El decorador `@audit(action, entity)` solo
observa el valor de retorno del service (usuario / acción / entidad / `object_id`); **estructuralmente
no puede** calcular un diff anterior→nuevo porque no conoce el estado previo de la instancia. Los
campos `field / old_value / new_value` del modelo `AuditLog` existen pero quedan **vacíos**.

En consecuencia, el `config.yaml` (fuente de verdad, **L139–140**) afirma algo que el código no hace:
que `@audit` registra "campo, valor anterior y valor nuevo". Es una inexactitud estructural, no un bug
de implementación puntual.

F10 resuelve ambos frentes: (a) añade el mecanismo complementario `record_field_changes` para el diff
campo-nivel de correcciones; (b) define el **registro declarativo de qué se audita** y un vocabulario
de acciones canónico; (c) **reconcilia la redacción del invariante** en `config.yaml` para describir el
mecanismo real (dos piezas). Es una fase de **mecanismo + reglas, backend puro**: sin endpoints, sin UI,
sin permisos.

## 2. Alcance Crítico

### In-Scope (Lo que se va a construir)

- **Registro de reglas** (`apps/common/audit_rules.py`): vocabulario `AuditAction` canónico, convención
  de nombres de `entity`, y un registro declarativo `AUDITED_FIELDS: dict[str, frozenset[str]]`
  (`entity → campos auditados a nivel campo`) + helper `is_audited(entity, field)`. Extensible por cada
  fase consumidora (como el `PERMISSION_CATALOG` de `authz`): son **código**, no una entidad configurable.
- **Mecanismo de diff campo-nivel** (`record_field_changes` + `to_audit_str` en `apps/common/audit.py`):
  emite **una fila `AuditLog` por campo cambiado**, con normalización de valores. `@audit` se conserva
  para el evento grueso.
- **Acción `CORRECTION`** distinta de `UPDATE`, para correcciones post-generación de documentos.
- **Estandarización del vocabulario:** los ~20 call sites de `@audit` en F1–F7 pasan de literales al
  enum `AuditAction` (sustitución de constante, `value` idéntico al literal vigente: **sin cambio de
  comportamiento ni de datos persistidos**).
- **Reconciliación del invariante** en `config.yaml` L139–140.
- **Sin nuevos contratos de datos:** no se crean serializers DRF ni tipos/Zod (no hay superficie HTTP en F10).

### Out-of-Scope (Prohibiciones Estrictas)

- **Backend:** Toda persistencia MUST ser PostgreSQL vía Django ORM. Sin SQL raw.
- **Backend:** Las creaciones de `AuditLog` del helper MUST correr dentro del `transaction.atomic()`
  del service llamador (el helper NO abre transacción propia; es un contrato documentado).
- **Backend:** `AuditLog` es un rastro append-only: MUST NOT usar soft delete.
- **Frontend / Seguridad / Calidad:** sin colores hardcodeados, credenciales por `.env`/Secret Manager,
  sin refactorizaciones ajenas al dominio (YAGNI).

Fuera de alcance funcional (diferido, no se construye en F10):

- **Qué campos son corregibles por documento** (peso, costo, …): lo registra cada fase F11+ en
  `AUDITED_FIELDS` y llama al helper en su service de corrección.
- **Recálculos en cascada de Kardex** por corrección (config L150–151) → F11/F17.
- **Lectura / exposición del audit log** (endpoint, UI, permisos, respeto de la invisibilidad de campos
  sensibles 2.4 en salida) → **fase posterior**.
  > **Nota de alcance.** Una versión previa de `documents/PLAN_DE_FASES.md` (F10) listaba la
  > *"consulta del log"* dentro del alcance de F10. Esta propuesta **difiere deliberadamente** la
  > consulta/lectura del log: exponerla sin respetar aún la invisibilidad de campos sensibles (2.4)
  > sería inseguro (el rastro puede contener `costo`), y 2.4 no es dependencia de F10. **El plan ya fue
  > reconciliado** para mover la consulta del log a "Fuera de alcance" (fase posterior), por lo que no
  > queda desincronización pendiente.
- **Retrofit amplio** de diff campo-nivel a todos los updates de F1–F7 (descartado por Opción A, literal 2.3).

## 3. Evaluación de Impacto

### Modelo de Datos (PostgreSQL)

**Ninguno.** No hay `makemigrations`. El modelo `AuditLog` (que ya tiene `field / old_value / new_value`)
permanece intacto. Las reglas son **código**, no una tabla nueva. No se afectan índices, constraints ni
foreign keys existentes. No se impacta el Kardex FIFO, el snapshot de entrega ni la trazabilidad.

> **Nota crítica de ubicación:** `AuditLog` y `@audit` ya viven en `apps/common` desde el bootstrap.
> F10 **NO** crea un app `audit` ni mueve el modelo (rompería migraciones y los ~20 usos existentes).
> La capability `audit` es una agrupación **a nivel spec de OpenSpec**; el código sigue en `apps/common`.

### Lógica de Negocio y API

- **Endpoints DRF:** ninguno nuevo ni modificado.
- **`apps/common/audit.py`:** se añaden `to_audit_str()` y `record_field_changes()`; `@audit` conserva
  su comportamiento (solo se corrige su docstring).
- **`apps/common/audit_rules.py`** (nuevo): `AuditAction`, `AUDITED_FIELDS`, `is_audited()`.
- **~20 call sites** de `@audit` en `accounts`, `authz`, `directory`, `products`, `pricing`, `credit`:
  sustitución de literal por miembro del enum. **Los valores persistidos no cambian.**
- No se toca FIFO, costeo, merma, ni la aplicación de cobros/pagos.

### Flujo del Usuario (UI)

**N/A en F10.** Mecanismo de dominio consumido por servicios de backend. No hay recursos/rutas nuevos,
no cambia ninguna vista, no afecta ningún rol en pantalla. La eventual vista de consulta del log es de
una fase posterior.

### Cadena de Trazabilidad

**No se altera la cadena de trazabilidad** (Ingreso → Kardex → Entrega → Cobro / Ingreso → CxP → Pago).
`audit` es un mecanismo transversal de rastro; **soporta** la trazabilidad de correcciones (2.3) que
Kardex (F11/F17) y demás documentos usarán, sin producir ni consumir movimientos.

## 4. Riesgos y Rollback

### Riesgo Principal

**El retrofit de literales a enum rompe asserts de F1–F7.** Varios tests existentes asertan
`action == "UPDATE"` (string). Si el `value` del miembro del enum difiere del literal vigente, esos
tests fallan y los datos persistidos cambian de forma. Riesgos secundarios: (b) el helper puede
persistir `old_value/new_value` de campos sensibles (p. ej. `costo`) — mitigado porque el rastro es
**solo-escritura** en F10 (no hay salida) y se documenta como precondición que la futura vista de
lectura respete la invisibilidad de campos (2.4); (c) normalización inconsistente de decimales/fechas/
FKs/`None` — mitigada centralizando y testeando `to_audit_str`.

### Criterio de Aborto

Abortar (revertir el change) si cualquiera de estas condiciones **verificables** se cumple:
(a) algún valor de `AuditAction` difiere del literal vigente que reemplaza; **o**
(b) los tests de F1–F7 dejan de pasar tras el retrofit de constantes; **o**
(c) los Scenarios de `record_field_changes` no quedan en verde.

### Plan de Rollback

Rollback puramente de código, **sin migración ni datos que deshacer**: revertir el diff de
`apps/common/audit.py`, eliminar el nuevo `apps/common/audit_rules.py`, revertir los ~20 call sites y
la línea reconciliada de `openspec/config.yaml` (L139–140). No hay `reverse` de migración porque no
hubo `makemigrations`.
