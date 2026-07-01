# Propuesta: add-system-settings

> **Fase 8.** Capability `system-settings` (inicia) · modifica `access-control` (registro de módulo +
> parche de perfiles semilla) · **Depende de:** F1 (auth), F2 (access-control) · **Desbloquea:** F11
> (kardex), F13 (merma) · **Requerimientos:** 14.2.
> **Fuente de verdad:** `openspec/config.yaml`. Ante conflicto, manda el `config.yaml`.

## 1. El Problema o Necesidad de Negocio

El sistema calcula y persiste SIEMPRE ambas bases de costeo en paralelo —costo nominal (peso de
factura) y costo efectivo (peso real tras merma)—, pero el negocio necesita decidir **cuál de las dos
se muestra** en reportes y dashboards sin alterar el cálculo. Hoy no existe ningún parámetro global
que gobierne esa presentación: cada fase posterior (kardex, merma, reportes) no tiene de dónde leer la
preferencia.

`system-settings` entrega los **parámetros globales del sistema** como un singleton editable, con los
dos **toggles de costeo** activables de forma independiente. El toggle es un **filtro de
presentación**: ambos costos se siguen calculando y persistiendo en paralelo (invariante de doble
costeo); el flag solo determina qué base **muestran** reportes y dashboards. Es prioritario porque es
precondición dura de F11 (kardex) y F13 (merma): sin este parámetro, esas fases no pueden resolver qué
base presentar. Solo el Jefe edita; el Supervisor consulta.

## 2. Alcance Crítico

### In-Scope (Lo que se va a construir)

- **Singleton de configuración** (`SystemSettings`): fila única garantizada a nivel de base de datos,
  con `costing_nominal_enabled` y `costing_effective_enabled` (ambos `True` por defecto). Sin máquina
  de estado, sin soft delete.
- **Invariante nuevo — al menos una base activa:** el sistema MUST rechazar dejar ambas bases
  desactivadas (400 en `non_field_errors`).
- **API de configuración:** `GET` (retrieve del singleton) y `PATCH` (update parcial de los toggles).
  Sin `POST`/`DELETE`.
- **Autorización (mecanismo de F2):** nuevo módulo `system-settings` con acciones `read`/`update`; el
  **Jefe** lo lleva con `read`+`update`, el **Supervisor** solo `read`. Se propaga tanto a
  instalaciones nuevas (seed) como a entornos ya sembrados (data migration de parche en `authz`).
- **Auditoría del cambio:** el `PATCH` registra un evento de auditoría (usuario/fecha/campo/valor
  anterior/valor nuevo) con el decorador `@audit` del bootstrap.

### Out-of-Scope (Prohibiciones Estrictas)

- **La lectura del flag en cálculos/reportes** (qué base se muestra en rentabilidad, dashboards y
  Kardex) → F11, F13, F23. En F8 el flag solo se almacena y se protege.
- **Cualquier otro parámetro global** (umbrales de caducidad, defaults de merma, plazos, etc.) →
  pertenece a su propia capability. YAGNI estricto: F8 solo lleva los dos toggles de costeo.
- **Backend:** toda persistencia MUST ser PostgreSQL vía Django ORM; sin SQL raw. Operaciones
  multi-tabla en `transaction.atomic()` con rollback total.
- **Frontend:** cero colores hardcodeados; todo estilo con tokens del theme (claro y oscuro).
- **Seguridad:** credenciales SOLO por `.env` / GCP Secret Manager; nunca en el repo.
- **Calidad:** sin refactorizaciones ajenas al dominio de este cambio (YAGNI).

### Decisiones de modelado (validadas)

- **Singleton a nivel de DB, no por convención:** campo centinela `lock` (`BooleanField`,
  `unique=True`, `editable=False`, default `True`) + `CheckConstraint(lock=True)`. Garantiza
  exactamente una fila; imposible crear una segunda ni por ORM ni por SQL directo.
- **El toggle es filtro de presentación, no de cálculo:** consistente con el invariante *doble costeo
  en paralelo*. F8 NO recalcula, NO cascada, NO interactúa con período. Por eso depende de F1/F2 y
  **no** de F9.
- **Excepción explícita a la política de soft delete (3 clases):** un singleton de configuración no es
  catálogo (clase 2), ni documento con estado (clase 1), ni ficha (clase 3). No se borra nunca; hereda
  solo `TimeStampedModel`.
- **"Solo el Jefe edita" = permiso de perfil:** la fuente única de autorización sigue siendo
  `authz.Profile`. No se introduce un segundo eje por `role`. El Jefe lleva `system-settings.update`
  por su perfil semilla.
- **Consumo por otras fases:** el service `get_settings()` retorna el singleton para lectura directa de
  kardex/merma/reports, **sin** pasar por los permisos del usuario final (esas fases lo consultan como
  regla de negocio, no como acción de UI).

## 3. Evaluación de Impacto

### Modelo de Datos (PostgreSQL)

- Nueva app `system_settings`. Tabla `system_settings` (una sola fila) con `costing_nominal_enabled`,
  `costing_effective_enabled`, `lock` (centinela único) y marcas de tiempo (`TimeStampedModel`).
  Migración reversible.
- **Data migration (misma app):** siembra la fila única con ambos toggles en `True`.
- **Data migration en `authz`:** parchea idempotentemente los perfiles semilla EXISTENTES (`JEFE` +=
  `read`,`update`; `SUPERVISOR` += `read`) sobre `system-settings`. Necesaria porque
  `seed_system_profiles()` usa `get_or_create(defaults=...)` y NO actualiza perfiles ya creados.
  Reversible (retira la clave `system-settings` de esos perfiles).
- Módulo `system-settings` y sus acciones registrados en el catálogo de `access-control` (F2).

### Lógica de Negocio y API

- Endpoints `GET` (retrieve) y `PATCH` (update parcial) del singleton; sin `id` en la ruta.
- Servicios en `apps/system_settings/services.py`: `get_settings()` (obtención del singleton) y
  `update_settings()` (valida "≥1 base activa", aplica toggles, audita). El view es delgado y delega.
- No se toca FIFO, costeo nominal/efectivo, merma, ni saldos CxC/CxP: F8 solo almacena los flags.

### Flujo del Usuario (UI)

- El **Jefe** (perfil con `system-settings` en `read`+`update`) ve y edita los toggles. El
  **Supervisor** (`read`) los ve en **solo lectura** (controles deshabilitados). El **Responsable de
  ruta** y el **Usuario** no ven ni acceden la pantalla (gating por perfil).
- Ruta protegida nueva; pantalla con dos interruptores. Estados vacío/carga/error/éxito requeridos; el
  error de "al menos una base activa" se muestra como **aviso general** (no atado a un campo). Tokens
  del theme; sin hex literales; áreas táctiles ≥44px.

### Cadena de Trazabilidad

No se altera la cadena de trazabilidad (Ingreso → Kardex → Entrega → Cobro / Ingreso → CxP → Pago).
`system-settings` es configuración global: no genera movimientos de Kardex, documentos ni saldos. Solo
**provee** los flags que kardex/merma/reports consumirán en fases posteriores.

## 4. Riesgos y Rollback

### Riesgo Principal

**El parche de perfiles en entornos ya sembrados.** Editar `SYSTEM_PROFILES` NO alcanza a perfiles
preexistentes (`get_or_create` no actualiza). Sin la data migration de parche, el Jefe de un entorno
F1–F7 ya corrido **no** podría editar la configuración. Mitigación: data migration idempotente que
fusiona la clave `system-settings` en `permissions` de `JEFE`/`SUPERVISOR` sin pisar otros permisos.
Riesgo secundario: que un seed corra dos veces o un test cree una segunda fila y rompa la unicidad;
mitigado con `CheckConstraint(lock=True)` + `unique=True` en `lock` + `get_or_create(lock=True)`.

### Criterio de Aborto

Abortar si (a) `authz` (F2) no está migrado —el módulo y el parche de perfiles lo requieren—, o (b) la
migración inversa (`migrate authz <anterior>` y `migrate system_settings zero`) falla tras 2 intentos
de corrección, o (c) los tests de los Scenarios no quedan en verde, o (d) tras el seed queda más de una
fila en `system_settings`.

### Plan de Rollback

Revertir en orden inverso: primero la data migration de `authz` (retira `system-settings` de los
perfiles semilla), luego `migrate system_settings zero` (elimina tabla + fila). Ambas reversibles; sin
dependencias de datos de negocio.
