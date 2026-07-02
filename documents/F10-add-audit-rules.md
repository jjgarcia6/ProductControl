# Change: add-audit-rules — Fase 10

**Capability:** `audit` (inicia como spec; el código vive en `apps/common`) · **Depende de:** F1 (auth) · **Desbloquea:** F11 (kardex), F12 (intake) y todo service con correcciones campo-nivel (F13–F24)
**Fuente de verdad:** `openspec/config.yaml`. Ante conflicto, manda el `config.yaml`.
**Requerimientos:** 2.3.

> **Cómo usar este archivo.** Consolida los cuatro artefactos del change. Cada sección de primer nivel mapea a un archivo dentro de `openspec/changes/add-audit-rules/`:
> - `## 1) PROPOSAL` → `proposal.md`
> - `## 2) SPECS` → un delta: `specs/audit/spec.md`
> - `## 3) DESIGN` → `design.md`
> - `## 4) TASKS` → `tasks.md`
>
> La `## 5) MODIFICACIONES PUNTUALES` NO es un artículo del change dir: son ediciones exactas sobre archivos existentes (`apps/common/audit.py`, `openspec/config.yaml`, y los ~20 call sites de `@audit` en services de F1–F7). Se aplican como *diffs* dirigidos, no como regeneración.
>
> **F10 es una fase de mecanismo + reglas, backend puro.** Sin endpoints, sin UI, sin permisos, sin tocar `apps/authz/catalog.py` ni `config/urls.py` (respeta "depende solo de F1"). Entrega el registro de reglas, el mecanismo de diff campo-nivel, la reconciliación del invariante y sus tests. Los consumidores reales del diff (correcciones de documentos) llegan en F11+.
>
> **Nota de implementación crítica.** `AuditLog` y `@audit` ya existen en `apps/common` desde el bootstrap. F10 **NO** crea un app `audit` ni mueve el modelo (rompería migraciones y los ~20 usos existentes). La capability `audit` es una agrupación a nivel spec de OpenSpec; el código sigue en `apps/common`.
>
> Requirements en RFC 2119 (MUST/MUST NOT/SHALL); Scenarios en español (DADO/CUANDO/ENTONCES). Código e identificadores en inglés; documentación en español.

---

## 1) PROPOSAL → proposal.md

### Intent

Definir las **reglas de qué se audita** (requisito 2.3) y dotar al mecanismo de auditoría del bootstrap de la capacidad de registrar correcciones **a nivel de campo** (fecha/hora, usuario, campo modificado, valor anterior, valor nuevo). El decorador `@audit(action, entity)` ya existe y registra eventos gruesos (quién / qué acción / sobre qué entidad); F10 añade el mecanismo complementario `record_field_changes` para el diff campo-nivel de correcciones, un registro declarativo de reglas y un vocabulario de acciones canónico. F10 **no** define qué campos son corregibles por documento (eso lo registra cada fase F11+) ni expone lectura del log (diferido).

### Contexto y reconciliación (root-cause)

- El `config.yaml` (fuente de verdad, L139–140) afirma que **`@audit(action, entity)`** registra "campo, valor anterior y valor nuevo". El decorador implementado solo registra `user/action/entity/object_id`; **estructuralmente no puede** calcular un diff anterior→nuevo, porque solo observa el valor de retorno del service (no el estado previo de la instancia). Los campos `field/old_value/new_value` del modelo `AuditLog` existen pero quedan vacíos.
- **Reconciliación (decisión validada):** el diff campo-nivel se implementa en un helper dedicado (`record_field_changes`), no en el decorador. Se corrige la redacción del invariante para describir el mecanismo real (dos piezas). Ver `## 5.2`.

### Scope (qué cambia)

- **Registro de reglas** (`apps/common/audit_rules.py`): vocabulario `AuditAction` canónico, convención de nombres de `entity`, y un registro declarativo `{entity → set de campos auditados a nivel campo}` (extensible por cada fase consumidora).
- **Mecanismo de diff campo-nivel** (`record_field_changes` en `apps/common/audit.py`): emite **una fila `AuditLog` por campo cambiado**, con normalización de valores. Se conserva `@audit` para eventos gruesos.
- **Acción `CORRECTION`** distinta de `UPDATE` para correcciones post-generación de documentos.
- **Estandarización del vocabulario:** `AuditAction` con valores idénticos a los literales actuales; los ~20 call sites de `@audit` en F1–F7 pasan de literales al enum (sustitución de constante, sin cambio de comportamiento ni de datos persistidos).
- **Reconciliación del invariante** en `config.yaml`.

### Decisiones de modelado (validadas)

- **Sin migración:** `AuditLog` ya tiene `field/old_value/new_value`. Las reglas son **código** (como el `PERMISSION_CATALOG` de `authz`), no una entidad configurable por el cliente.
- **Alcance estrecho (Opción A, literal 2.3):** el diff campo-nivel aplica a **correcciones de documentos** (F11+). Los updates de catálogos/usuarios de F1–F7 conservan `@audit` grueso; **sin retrofit masivo**. El único retrofit es la sustitución de literales por el enum.
- **Helper dedicado, no decorador diff-capable:** el service de corrección es el único lugar que tiene de forma fiable el estado antes/después; ahí se calcula el diff y se llama al helper. Un decorador que snapshotee la instancia es frágil (no conoce con certeza el objeto previo).
- **Una fila por campo cambiado:** coincide con el esquema singular `field/old_value/new_value`; evita un JSON de cambios que exigiría migración.
- **`AuditAction` con valores == literales actuales:** `CREATE`, `UPDATE`, `SOFT_DELETE`, `STATE_CHANGE` (+ nuevo `CORRECTION`). Como `TextChoices`/`StrEnum` con `value` igual al string vigente, los datos persistidos no cambian y los tests de F1–F7 que asertan `action == "UPDATE"` siguen en verde.
- **Backend puro (depende solo de F1):** sin endpoint, sin UI, sin permisos. La lectura del log se difiere; cuando exista, deberá respetar la invisibilidad de campos sensibles (2.4), porque el rastro puede contener `costo`.

### Impacto en el modelo de datos

Ninguno. No hay `makemigrations`. El modelo `AuditLog` permanece intacto.

### Flujo del usuario (UI)

**N/A en F10.** Mecanismo de dominio consumido por servicios de backend. La eventual vista de consulta del log es de una fase posterior.

### Cadena de trazabilidad

No se altera la cadena (Ingreso → Kardex → Entrega → Cobro / Ingreso → CxP → Pago). `audit` es un mecanismo transversal de rastro; **soporta** la trazabilidad de correcciones (2.3) que Kardex (F11/F17) y demás documentos usarán.

### Fuera de alcance

- **Qué campos son corregibles por documento** (peso, costo, etc.): lo registra cada fase F11+ en el registro de reglas y llama al helper en su service de corrección.
- **Recálculos en cascada de Kardex** por corrección (config L150–151) → F11/F17.
- **Lectura/exposición del audit log** (endpoint, UI, permisos, respeto de 2.4 en salida) → fase posterior.
- **Retrofit amplio** de diff campo-nivel a todos los updates de F1–F7 (descartado por Opción A).
- **Prohibiciones estrictas (heredadas):** persistencia SOLO PostgreSQL vía ORM; multi-tabla en `transaction.atomic()`; credenciales por `.env`/Secret Manager; sin refactor ajeno al dominio (YAGNI).

### Verificación de invariantes

- **Auditoría centralizada (config L139–140):** se cumple tras reconciliar la redacción; la lógica de logging no se duplica (helper + decorador en `apps/common`).
- **Kardex append-only (config L150–151):** F10 provee el mecanismo que Kardex usará para auditar correcciones; no toca Kardex.
- **Contrato de errores / período / soft delete / doble costeo:** no se tocan.

### Riesgos y rollback

- **Riesgo 1 — el retrofit de literales rompe asserts.** Mitigación: `AuditAction.value` idéntico a cada literal vigente; un test explícito confirma que el evento grueso de un service F1–F7 no cambió de valor persistido.
- **Riesgo 2 — fuga de valores sensibles en el rastro.** El helper puede persistir `old_value/new_value` de campos sensibles (p. ej. `costo`). Mitigación: el rastro es solo-escritura en F10 (no hay salida); se documenta como precondición que la futura vista de lectura respete la invisibilidad de campos (2.4).
- **Riesgo 3 — normalización inconsistente de valores.** Decimales, fechas, FKs y `None` deben serializarse de forma comparable. Mitigación: `to_audit_str` centralizado y testeado.
- **Criterio de aborto (verificable):** abortar si (a) algún valor de `AuditAction` difiere del literal vigente que reemplaza, o (b) los tests de F1–F7 dejan de pasar tras el retrofit, o (c) los Scenarios de `record_field_changes` no quedan en verde.
- **Plan de rollback:** revertir el diff de `apps/common/audit.py`, el nuevo `audit_rules.py`, los call sites y la línea de `config.yaml`. Sin migración ni datos que deshacer; rollback puramente de código.

---

## 2) SPECS

### 2.1 → specs/audit/spec.md

# Delta para la capability `audit`

> Scenarios de dominio del mecanismo (comportamiento de `record_field_changes` y del registro de reglas), no endpoints HTTP.

## ADDED Requirements

### Requirement: Vocabulario de acciones de auditoría
El sistema MUST exponer un conjunto canónico de acciones de auditoría (`CREATE`, `UPDATE`, `CORRECTION`, `SOFT_DELETE`, `STATE_CHANGE`). Los valores persistidos MUST coincidir con los literales ya usados por los services existentes para las acciones equivalentes.

#### Scenario: La acción de corrección se distingue de la actualización
- DADO una corrección post-generación sobre un documento
- CUANDO se registra el evento de auditoría
- ENTONCES la acción registrada es `CORRECTION` y no `UPDATE`

### Requirement: Registro de correcciones a nivel de campo
Toda corrección sobre un campo registrado como auditable MUST generar un registro de auditoría **por campo modificado**, con usuario, fecha/hora, campo, valor anterior y valor nuevo. Un campo no registrado como auditable MUST NOT generar registro. Un campo sin cambio real MUST NOT generar registro.

#### Scenario: Corrección de un campo auditado
- DADO una entidad con el campo `weight` registrado como auditable
- CUANDO se corrige `weight` de un valor anterior a uno nuevo
- ENTONCES el sistema crea un registro de auditoría con acción `CORRECTION`, el campo `weight`, el valor anterior, el valor nuevo y el usuario

#### Scenario: Corrección de múltiples campos
- DADO una entidad con `weight` y `cost` registrados como auditables
- CUANDO se corrigen ambos en una operación
- ENTONCES el sistema crea **dos** registros de auditoría, uno por campo

#### Scenario: Campo no auditable
- DADO una entidad con un campo no registrado como auditable
- CUANDO ese campo cambia
- ENTONCES el sistema NO crea registro para ese campo

#### Scenario: Sin cambio real
- DADO un campo auditable cuyo valor nuevo es igual al anterior
- CUANDO se procesa la operación
- ENTONCES el sistema NO crea registro para ese campo

### Requirement: Normalización de valores del rastro
Los valores anterior y nuevo MUST persistirse mediante una normalización consistente: los decimales como cadena en notación simple, las fechas en formato ISO, las claves foráneas como su identificador, y los valores nulos como cadena vacía.

#### Scenario: Normalización de un decimal
- DADO una corrección de un campo de peso con valor `Decimal("12.50")`
- CUANDO se registra
- ENTONCES el valor nuevo se persiste como `"12.50"` (sin notación científica ni ceros ambiguos)

### Requirement: Compatibilidad del evento grueso
El decorador `@audit(action, entity)` MUST seguir registrando el evento de acción (usuario, acción, entidad, identificador de objeto) sin diff campo-nivel. El comportamiento de los services existentes MUST NOT cambiar.

#### Scenario: Evento grueso preservado
- DADO un service existente decorado con `@audit`
- CUANDO se ejecuta con éxito
- ENTONCES se crea un registro con la acción y la entidad, sin campos de diff

---

## 3) DESIGN → design.md

> **Orden de trabajo adaptado.** Sin capa de contrato OpenAPI ni frontend. Orden: **Reglas/vocabulario → Mecanismo (helper) → Retrofit de call sites → Reconciliación de invariante → Seguridad → Pruebas.**

### Capa de reglas (`apps/common/audit_rules.py`)

- `AuditAction` (`TextChoices` o `StrEnum`): `CREATE="CREATE"`, `UPDATE="UPDATE"`, `CORRECTION="CORRECTION"`, `SOFT_DELETE="SOFT_DELETE"`, `STATE_CHANGE="STATE_CHANGE"`. Valores idénticos a los literales vigentes.
- **Convención de `entity`:** nombre del modelo en PascalCase (coherente con los usos actuales: `User`, `Ficha`, `Product`, `CreditTerms`, …).
- **Registro de campos auditables:** estructura `AUDITED_FIELDS: dict[str, frozenset[str]]` (`entity → campos`), inicialmente vacío o con lo que exista; cada fase F11+ añade su entrada (p. ej. `"KardexMovement": {"weight", "cost"}`). Un helper `is_audited(entity, field) -> bool` consulta el registro.

### Capa de mecanismo (`apps/common/audit.py`)

- Se conserva `@audit(action, entity)` (evento grueso) intacto en comportamiento; se corrige el docstring para referir el enum y el helper.
- `to_audit_str(value) -> str`: normaliza `Decimal` (formato simple, sin exponente), `date`/`datetime` (ISO), instancias de modelo/FK (pk como str), `None` (`""`), y el resto vía `str()`.
- `record_field_changes(*, user, entity, object_id, before: Mapping[str, Any], after: Mapping[str, Any], action: str = AuditAction.CORRECTION) -> list[AuditLog]`:
  - Para cada campo presente en `after`, si `is_audited(entity, field)` y `to_audit_str(before[field]) != to_audit_str(after[field])`, crea un `AuditLog` con `field`, `old_value`, `new_value`, `user`, `action`, `object_id`.
  - Devuelve la lista de registros creados (facilita aserciones en tests).
  - Las creaciones ocurren dentro del `transaction.atomic()` del service llamador (el helper no abre transacción propia; se documenta como contrato).

**Servicios / utilidades**

| Ubicación | Símbolo | Responsabilidad única |
| :--- | :--- | :--- |
| `common/audit_rules.py` | `AuditAction` | vocabulario canónico de acciones |
| `common/audit_rules.py` | `AUDITED_FIELDS` / `is_audited()` | registro declarativo de campos auditables |
| `common/audit.py` | `@audit` | evento grueso (sin cambios de comportamiento) |
| `common/audit.py` | `to_audit_str()` | normalización de valores del rastro |
| `common/audit.py` | `record_field_changes()` | una fila por campo corregido |

### Contrato para fases consumidoras (F11+)

- Cada fase con documentos corregibles registra sus campos en `AUDITED_FIELDS` y, en su service de corrección, calcula `before`/`after` sobre la instancia y llama a `record_field_changes(..., action=AuditAction.CORRECTION)` dentro de su transacción.
- Cada fase incluye su propio Scenario "corrección de campo auditado → una fila por campo con anterior/nuevo/usuario/fecha".

### Seguridad

- Sin superficie externa. El rastro puede contener valores sensibles (`costo`); al ser solo-escritura en F10 no hay fuga. **Precondición forward:** la futura vista de lectura del log DEBE aplicar la invisibilidad de campos por perfil (2.4).

### Qué NO se hace (YAGNI)

Sin endpoints, sin UI, sin permisos, sin registro en el catálogo de `access-control`, sin migración, sin recálculos de Kardex, sin retrofit amplio de diff, sin definir campos corregibles concretos (los define cada fase).

---

## 4) TASKS → tasks.md

> Definition of done global: gates de backend en verde localmente. Sin gates de frontend (no hay UI).

### A. Reglas y vocabulario
- [ ] A.1 Crear `apps/common/audit_rules.py` con `AuditAction` (valores == literales vigentes + `CORRECTION`), la convención de `entity` y el registro `AUDITED_FIELDS` + `is_audited()`.

### B. Mecanismo
- [ ] B.1 Añadir `to_audit_str()` en `apps/common/audit.py` (Decimal simple, fecha ISO, FK→pk, `None`→"").
- [ ] B.2 Añadir `record_field_changes(*, user, entity, object_id, before, after, action=CORRECTION)`: una fila por campo auditado con cambio real; sin abrir transacción propia (contrato: corre dentro de la del service).
- [ ] B.3 Corregir el docstring de `@audit` para referir `AuditAction` y `record_field_changes`; conservar su comportamiento grueso.

### C. Retrofit de call sites (constantes, sin cambio de comportamiento)
- [ ] C.1 Sustituir literales de acción por `AuditAction` en los `@audit` de: `apps/accounts/services.py`, `apps/authz/services.py`, `apps/directory/services.py`, `apps/products/services.py`, `apps/pricing/services.py`, `apps/credit/services.py`.

### D. Reconciliación del invariante
- [ ] D.1 Editar `openspec/config.yaml` L139–140 para describir el mecanismo real (`@audit` acción; `record_field_changes` diff campo/anterior/nuevo).

### E. Frontend
- [ ] E.1 N/A — F10 no tiene superficie de usuario.

### F. Seguridad (no negociable)
- [ ] F.1 `ruff check` + `mypy --strict` sobre `apps/common` y los services retrofiteados. Corregir todo.
- [ ] F.2 `bandit` sobre `apps/common`; confirmar que no hay SQL raw ni secretos en el diff.

### G. Pruebas (gate)
- [ ] G.1 Tests del mecanismo en `apps/common/tests/`: una fila por campo corregido; múltiples campos → múltiples filas; campo no auditable → sin fila; sin cambio real → sin fila; acción `CORRECTION` ≠ `UPDATE`; normalización de Decimal/fecha/FK/None. Usar una entidad existente real (sin retrofitear su service) o un modelo de prueba.
- [ ] G.2 Test de compatibilidad: el evento grueso de un service F1–F7 conserva su valor de acción persistido tras el retrofit.
- [ ] G.3 Ejecutar y dejar en verde: `ruff`, `mypy --strict`, `bandit`, `pip-audit`, `pytest` (cobertura ≥80%). Confirmar antes de declarar el change completo.

---

## 5) MODIFICACIONES PUNTUALES (archivos existentes del repo)

> Aplicar como *diffs* dirigidos. NO regenerar los archivos completos.

### 5.1 `apps/common/audit.py`

Añadir (sin alterar el `@audit` existente salvo su docstring):
```python
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.db.models import Model

from apps.common.audit_rules import AuditAction, is_audited


def to_audit_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Model):
        return str(value.pk)
    return str(value)


def record_field_changes(
    *,
    user: Any,
    entity: str,
    object_id: str,
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    action: str = AuditAction.CORRECTION,
) -> list["AuditLog"]:
    from apps.common.models import AuditLog

    created: list[AuditLog] = []
    for field, new in after.items():
        if not is_audited(entity, field):
            continue
        old_str = to_audit_str(before.get(field))
        new_str = to_audit_str(new)
        if old_str == new_str:
            continue
        created.append(
            AuditLog.objects.create(
                user=user,
                action=action,
                entity=entity,
                object_id=str(object_id),
                field=field,
                old_value=old_str,
                new_value=new_str,
            )
        )
    return created
```

### 5.2 `openspec/config.yaml` — invariante de auditoría (L139–140)

Reemplazar por una redacción que describa el mecanismo real:
```yaml
  - Auditoría centralizada (apps.common): el decorador `@audit(action, entity)` en services
    registra el EVENTO de acción (fecha/hora, usuario, acción, entidad, object_id); el helper
    `record_field_changes` registra el DIFF campo-nivel de correcciones (una fila por campo con
    valor anterior y valor nuevo). El vocabulario de acciones es `AuditAction`. NO se repite la
    lógica de logging.
```

### 5.3 Call sites de `@audit` (retrofit de constantes)

En cada service, sustituir el literal por el miembro del enum. Patrón (aplicar a los ~20 sitios):
```python
from apps.common.audit_rules import AuditAction

@audit(action=AuditAction.UPDATE, entity="User")      # antes: action="UPDATE"
@audit(action=AuditAction.CREATE, entity="Product")   # antes: action="CREATE"
@audit(action=AuditAction.SOFT_DELETE, entity="Profile")
@audit(action=AuditAction.STATE_CHANGE, entity="Ficha")
```
Archivos afectados: `apps/accounts/services.py`, `apps/authz/services.py`, `apps/directory/services.py`, `apps/products/services.py`, `apps/pricing/services.py`, `apps/credit/services.py`. **Los valores persistidos no cambian** (enum `value` == literal vigente).

> **Sin cambios** en `config/urls.py`, `apps/authz/catalog.py`, `config/settings/base.py` (no hay app nuevo) ni migraciones.
