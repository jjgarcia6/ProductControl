# Diseño Técnico: add-audit-rules

<!-- Orden DIP: Datos → API → UI. F10 es backend puro: las capas de UI (§3) no aplican y se declaran N/A. -->
<!-- Orden de trabajo real: Reglas/vocabulario → Mecanismo (helper) → Retrofit de call sites → -->
<!-- Reconciliación de invariante → Seguridad → Pruebas. -->

## 1. Capa de Datos (PostgreSQL + Django ORM)

### Tablas e Índices

**Sin cambios de esquema.** F10 reutiliza el modelo `AuditLog` existente del bootstrap; no crea, altera
ni elimina tablas, índices, constraints ni foreign keys.

| Tabla | Índice / Constraint | Tipo | Justificación |
| :--- | :--- | :--- | :--- |
| `audit_logs` (existente) | — | — | Sin cambios. Ya contiene `field / old_value / new_value`, hoy vacíos; F10 los llena vía `record_field_changes`. |

### Modelo Django

**Sin modificación.** `AuditLog` permanece intacto. Es un rastro **append-only** (no hereda
`SoftDeleteMixin`): los registros no se editan ni se borran. F10 no añade campos "por si acaso" (YAGNI):
el esquema singular `field / old_value / new_value` ya soporta "una fila por campo cambiado", lo que
evita un JSON de cambios que exigiría migración.

### Migración Django

**Ninguna.** No hay `makemigrations`. Al no haber migración, no hay `reverse` que probar; el rollback es
puramente de código (ver proposal §4).

### Impacto en Invariantes del Sistema

- **Período cerrado:** N/A — el mecanismo de auditoría no crea documentos con fecha; no valida ni altera períodos.
- **Kardex FIFO / append-only:** No se toca Kardex. F10 **provee** el mecanismo que Kardex (F11/F17) usará
  para auditar sus correcciones sin borrar movimientos; el propio `AuditLog` es append-only.
- **Doble costeo:** N/A — no se calcula ni altera costo nominal/efectivo.
- **Cuadre de ruta:** N/A.
- **Snapshot inmutable de entrega:** N/A.
- **Nota de crédito vinculada:** N/A.
- **Soft delete (3 clases):** `AuditLog` es rastro append-only (no catálogo, no soft delete). No se añade
  modelo con soft delete.
- **Trazabilidad:** No se altera Ingreso → Kardex → Entrega → Cobro / Ingreso → CxP → Pago.
- **Auditoría centralizada (config L139–140):** **se reconcilia la redacción** para describir el mecanismo
  real de dos piezas (ver §5). La lógica de logging NO se duplica: helper + decorador conviven en `apps/common`.

---

## 2. Capa de API y Contratos (Fuente de Verdad)

### Diccionario de Datos Vivo

Sin contrato HTTP nuevo. Este cuadro documenta los campos **existentes** de `AuditLog` que el mecanismo
de F10 pasa a poblar (antes vacíos para eventos de corrección):

| Entidad | Campo | Tipo (Py) | Descripción (Uso y Propósito) | Restricciones |
| :--- | :--- | :--- | :--- | :--- |
| `AuditLog` | `action` | `str` (`AuditAction`) | Acción canónica: `CREATE/UPDATE/CORRECTION/SOFT_DELETE/STATE_CHANGE`. | `value` == literal vigente |
| `AuditLog` | `entity` | `str` | Nombre del modelo en PascalCase (`User`, `Ficha`, `Product`, …). | — |
| `AuditLog` | `object_id` | `str` | Identificador de la instancia afectada. | — |
| `AuditLog` | `field` | `str` | Nombre del campo corregido (solo en diff campo-nivel). | Vacío en evento grueso |
| `AuditLog` | `old_value` | `str` | Valor anterior normalizado por `to_audit_str`. | `""` si `None` |
| `AuditLog` | `new_value` | `str` | Valor nuevo normalizado por `to_audit_str`. | `""` si `None` |

### Backend: Serializers DRF

**N/A.** F10 no expone lectura ni escritura del audit log por HTTP. No se crean `WriteSerializer` ni
`ReadSerializer`. La eventual vista de consulta (con serializer que respete la invisibilidad de campos
sensibles, 2.4) es de una fase posterior.

### Frontend: Tipos generados (Zod + TypeScript)

**N/A.** Sin superficie HTTP no hay cambios en el OpenAPI y por tanto no hay `npm run codegen` ni tipos/Zod nuevos.

### Endpoints de DRF

**N/A.** Ningún endpoint nuevo ni modificado. No se toca `config/urls.py` ni `apps/authz/catalog.py`
(respeta "depende solo de F1").

### Servicio de Negocio

El "servicio" de F10 es el mecanismo transversal en `apps/common`. Cada símbolo tiene una responsabilidad única:

| Ubicación | Símbolo | Responsabilidad única | Transaccional |
| :--- | :--- | :--- | :--- |
| `common/audit_rules.py` | `AuditAction` | Vocabulario canónico de acciones (`TextChoices`/`StrEnum`, `value` == literal vigente). | No |
| `common/audit_rules.py` | `AUDITED_FIELDS` / `is_audited()` | Registro declarativo `entity → frozenset[campos]`; consulta de auditabilidad. | No |
| `common/audit.py` | `@audit` | Evento grueso (usuario/acción/entidad/object_id). **Sin cambio de comportamiento.** | Hereda del service |
| `common/audit.py` | `to_audit_str()` | Normalización de valores del rastro (Decimal simple, fecha ISO, FK→pk, `None`→`""`). | No (función pura) |
| `common/audit.py` | `record_field_changes()` | Una fila `AuditLog` por campo auditado con cambio real. | Corre **dentro** de la del service (no abre transacción propia) |

**Diseño de referencia** (ilustrativo; el código exacto se aplica en `/opsx:apply`):

```python
# apps/common/audit_rules.py
class AuditAction(models.TextChoices):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    CORRECTION = "CORRECTION"        # nuevo — corrección post-generación
    SOFT_DELETE = "SOFT_DELETE"
    STATE_CHANGE = "STATE_CHANGE"

# entity → campos auditados a nivel campo. Cada fase F11+ añade su entrada.
AUDITED_FIELDS: dict[str, frozenset[str]] = {
    # "KardexMovement": frozenset({"weight", "cost"}),  # ejemplo F11+
}

def is_audited(entity: str, field: str) -> bool:
    return field in AUDITED_FIELDS.get(entity, frozenset())
```

```python
# apps/common/audit.py (añadidos; @audit intacto salvo docstring)
def to_audit_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return format(value, "f")          # simple, sin exponente
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Model):
        return str(value.pk)
    return str(value)

def record_field_changes(*, user, entity, object_id, before, after,
                         action=AuditAction.CORRECTION) -> list[AuditLog]:
    created = []
    for field, new in after.items():
        if not is_audited(entity, field):
            continue
        old_str, new_str = to_audit_str(before.get(field)), to_audit_str(new)
        if old_str == new_str:
            continue
        created.append(AuditLog.objects.create(
            user=user, action=action, entity=entity, object_id=str(object_id),
            field=field, old_value=old_str, new_value=new_str,
        ))
    return created
```

### Contrato para fases consumidoras (F11+)

- Cada fase con documentos corregibles registra sus campos en `AUDITED_FIELDS` y, en su service de
  corrección, calcula `before`/`after` sobre la instancia y llama a
  `record_field_changes(..., action=AuditAction.CORRECTION)` **dentro** de su `transaction.atomic()`.
- Cada fase incluye su propio Scenario "corrección de campo auditado → una fila por campo con
  anterior/nuevo/usuario/fecha".

---

## 3. Capa de Presentación (UI — React + Refine)

**N/A — F10 no tiene superficie de usuario.** Sin árbol de feature, sin hooks, sin páginas ni resources
de Refine. La eventual vista de consulta del audit log (con respeto de la invisibilidad de campos
sensibles por perfil, 2.4) se diseñará en una fase posterior.

---

## 4. Configuración y DevSecOps

### Gestión de Secretos

- **Backend:** ninguna variable de entorno nueva. Sin cambios en `.env.example`.
- **Frontend:** N/A.

### Seguridad Proactiva

- **Análisis Estático Backend:** `ruff check`, `ruff format --check`, `mypy --strict` y `bandit` limpios
  sobre `apps/common` y los services retrofiteados. Sin SQL raw ni secretos en el diff.
- **Análisis Estático Frontend:** N/A.
- **SCA (Dependencias):** sin dependencias nuevas; `pip-audit` se corre igual como gate global.
- **Superficie externa:** ninguna. El rastro puede contener valores sensibles (`costo`); al ser
  **solo-escritura** en F10 no hay fuga. **Precondición forward:** la futura vista de lectura DEBE aplicar
  la invisibilidad de campos por perfil (2.4).

---

## 5. Cambios Estructurales

### Nuevas Dependencias

Ninguna.

### Migraciones de Base de Datos

Ninguna. No se añaden, renombran ni eliminan columnas. No hay data migration.

### Reconciliación de la fuente de verdad (`openspec/config.yaml`)

Se edita el invariante de auditoría (**L139–140**) para describir el mecanismo real de dos piezas.
Redacción propuesta:

```yaml
  - Auditoría centralizada (apps.common): el decorador `@audit(action, entity)` en services
    registra el EVENTO de acción (fecha/hora, usuario, acción, entidad, object_id); el helper
    `record_field_changes` registra el DIFF campo-nivel de correcciones (una fila por campo con
    valor anterior y valor nuevo). El vocabulario de acciones es `AuditAction`. NO se repite la
    lógica de logging.
```

### Retrofit de call sites (constantes, sin cambio de comportamiento)

En cada service, sustituir el literal de acción por el miembro del enum (`value` == literal vigente):

```python
from apps.common.audit_rules import AuditAction

@audit(action=AuditAction.UPDATE, entity="User")      # antes: action="UPDATE"
@audit(action=AuditAction.CREATE, entity="Product")   # antes: action="CREATE"
@audit(action=AuditAction.SOFT_DELETE, entity="Profile")
@audit(action=AuditAction.STATE_CHANGE, entity="Ficha")
```

Archivos afectados: `apps/accounts/services.py`, `apps/authz/services.py`, `apps/directory/services.py`,
`apps/products/services.py`, `apps/pricing/services.py`, `apps/credit/services.py`.

> **Sin cambios** en `config/urls.py`, `apps/authz/catalog.py`, `config/settings/base.py` (no hay app
> nuevo) ni migraciones.

### Qué NO se hace (YAGNI)

Sin endpoints, sin UI, sin permisos, sin registro en el catálogo de `access-control`, sin migración, sin
recálculos de Kardex, sin retrofit amplio de diff, sin definir campos corregibles concretos (los define
cada fase F11+), sin lectura/exposición del audit log.
