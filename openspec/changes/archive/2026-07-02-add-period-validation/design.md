# Diseño Técnico: add-period-validation

> **Fase sin API ni UI.** Se conserva el esqueleto canónico de 5 secciones; las secciones que no
> aplican (API/Contratos, Presentación) se marcan **N/A** con su justificación. El orden DIP se
> respeta: la Capa de Datos define la abstracción de la que depende el validador.

## 1. Capa de Datos (PostgreSQL + Django ORM)

### Tablas e Índices

| Tabla | Índice / Constraint | Tipo | Justificación |
| :--- | :--- | :--- | :--- |
| `period` | `(year, month)` | unique | un solo período por mes contable; cubre el lookup del validador |
| `period` | `1 <= month <= 12` | check constraint | integridad del mes a nivel de DB |

### Modelo Django

```python
# Modelo Django — Tabla: period
# Mixins: TimeStampedModel (siempre). NO hereda SoftDeleteModel (soft delete clase 1:
# máquina de estado OPEN/CLOSED, sin borrado; la transición la ejecuta F25).

class Period(TimeStampedModel):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Abierto"
        CLOSED = "CLOSED", "Cerrado"

    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField()  # validado 1–12 por CheckConstraint
    status = models.CharField(max_length=6, choices=Status.choices, default=Status.OPEN)

    class Meta:
        db_table = "period"
        constraints = [
            models.UniqueConstraint(fields=["year", "month"], name="period_unique_year_month"),
            models.CheckConstraint(
                check=Q(month__gte=1) & Q(month__lte=12), name="period_month_range"
            ),
        ]
```

### Migración Django

```
# Archivo: apps/period/migrations/0001_initial.py
# operations: CreateModel(Period) + AddConstraint(unique) + AddConstraint(check)
# Generar con: uv run python manage.py makemigrations period
# Aplicar con:  uv run python manage.py migrate
# Reverse de prueba: uv run python manage.py migrate period zero
# SIN data migration de seed (semántica implícita-abierta).
```

### Impacto en Invariantes del Sistema

- **Período cerrado:** implementado aquí. `status=CLOSED` es la condición de bloqueo.
- **Kardex FIFO / append-only:** no se toca (no existe aún).
- **Doble costeo:** no se toca.
- **Cuadre de ruta:** no se toca.
- **Snapshot inmutable de entrega:** no se toca.
- **Nota de crédito vinculada:** no se toca.
- **Soft delete (3 clases):** `Period` = clase 1 (máquina de estado, sin borrado; transición por
  `status`, ejecutada por F25). Coherente con la política.
- **Trazabilidad:** no se altera; `period` la protege sin generar movimientos.

---

## 2. Capa de API y Contratos (Fuente de Verdad)

**N/A en F9.** No hay endpoints, serializers ni tipos Zod. Exponer una API de lectura de períodos
arrastraría F2 (permisos) y rompería la dependencia "solo F1". La superficie de API/UI de cierre
llega en F25.

El único "contrato" de F9 es la **precondición documentada para fases consumidoras (F11+)**:

- Los documentos con fecha DEBEN modelar su fecha contable como `DateField` (no `DateTimeField`).
- La fecha se interpreta en zona local **America/Guayaquil (UTC-5, sin DST)**; `(year, month)` se
  extraen de esa fecha.
- Cada service de documento DEBE invocar `assert_date_operable` en create y update, e incluir su
  propio Scenario de "fecha en período cerrado → 400 `non_field_errors`".

### Servicio de Negocio

| Servicio | Método | Responsabilidad única | Transaccional |
| :--- | :--- | :--- | :--- |
| `period/selectors.py` | `get_period(year, month)` | resolver el período de un `(año, mes)` o `None` | No |
| `period/services.py` | `is_period_closed(doc_date)` | decidir si una fecha cae en período cerrado | No |
| `period/services.py` | `assert_date_operable(doc_date)` | levantar el error de contrato (`ValidationError` → 400 `non_field_errors`) si la fecha no es operable | No |

Detalle del validador:

- `get_period(year, month) -> Period | None`: lookup por `(year, month)`; `None` si no existe (mes
  implícitamente abierto).
- `is_period_closed(doc_date) -> bool`: deriva `(year, month)` de `doc_date`, consulta `get_period`;
  `True` solo si existe y `status=CLOSED`.
- `assert_date_operable(doc_date) -> None`: si `is_period_closed(doc_date)`, levanta
  `rest_framework.exceptions.ValidationError(["La fecha pertenece a un período cerrado."])`; en caso
  contrario no hace nada. El `EXCEPTION_HANDLER` de `apps.common` lo mapea a
  `{"non_field_errors": [...]}` con HTTP 400 (forma verificada en
  `apps/common/tests/test_exceptions.py`).

---

## 3. Capa de Presentación (UI — React + Refine)

**N/A en F9.** Sin superficie de usuario: es un mecanismo de dominio consumido por servicios de
backend en fases posteriores. La pantalla y los permisos de cierre/reversión son de F25.

---

## 4. Configuración y DevSecOps

### Gestión de Secretos

- **Backend:** ninguna variable de entorno nueva. F9 no introduce secretos ni configuración externa.
- **Frontend:** N/A (sin UI).

### Seguridad Proactiva

- **Análisis Estático Backend:** resultado limpio esperado de `ruff`, `mypy --strict` y `bandit`
  sobre `apps/period`. Confirmar que no hay SQL raw, secretos ni credenciales en el diff.
- **Análisis Estático Frontend:** N/A.
- **SCA (Dependencias):** sin dependencias nuevas; `pip-audit` en verde.

---

## 5. Cambios Estructurales

### Nuevas Dependencias

Ninguna.

### Migraciones de Base de Datos

Una migración inicial (`0001_initial`) que crea la tabla `period` y sus dos constraints. Reverse
funcional (`migrate period zero`). Sin data migration ni columnas sobre tablas existentes.

### Registro de la app

`apps.period` se añade a `LOCAL_APPS` en `config/settings/base.py` (tras `apps.system_settings`).
Sin cambios en `config/urls.py` (no hay endpoints), en `apps/authz/catalog.py` (no hay permisos) ni
en `openspec/config.yaml` (el invariante "período cerrado" ya existe).
