# Plan de fases — Sistema de gestión operativa

**Tipo:** Índice maestro de changes (hoja de ruta)
**Fuente de verdad:** `openspec/config.yaml`. Ante cualquier conflicto entre este plan y el `config.yaml`, manda el `config.yaml`.
**Ubicación esperada:** `documents/PLAN_DE_FASES.md`
**Versión:** 1.1

> **Cambios respecto a v1.0:** se añaden cuatro changes y se renumera de 21 a 25 fases. Nuevos: `add-user-management` (F3, ciclo de vida de identidad), `add-bulk-import` (F7, importación masiva de maestros), `add-system-settings` (F8, parámetros del sistema incl. toggle de costeo) y `add-opening-balances` (F20, carga inicial para go-live). Dependencias recalculadas. Ver registro de cambios al final.

---

## 0. Cómo se usa este plan

Este documento es el índice maestro de **changes** de OpenSpec. No contiene lógica de implementación: cada fase se desarrolla en su propio change (carpeta `openspec/changes/<change>/` con `proposal.md` + `specs/` + `design.md` + `tasks.md`).

Flujo por fase:

```
/opsx:explore  "revisa documents/PLAN_DE_FASES.md, continua con la fase N"
/opsx:proposal  → genera los artefactos del change
revisar specs/design  → /opsx:apply  → verificar (CI) → /opsx:archive
```

**Convención de numeración:**

- **Fase N** = un change = una carpeta OpenSpec. Numeración lineal y global, para que "la fase N" sea inequívoca.
- **Etapa** = agrupación temática. Solo organizativa, no ejecutable.
- **Fase 0** = bootstrap técnico (runbook `00-bootstrap-stack-y-repositorio.md`), ya entregado.

**Regla de orden:** una fase solo arranca cuando todas sus dependencias están en estado *done* (archivadas). Las dependencias no son sugerencias: construir fuera de orden produce capabilities incompletas.

**Orden de construcción ≠ orden de uso.** Algunas fases se construyen tarde pero se usan primero (p. ej. `add-opening-balances`, necesaria para el go-live, depende de que Kardex/CxC/CxP ya existan).

**Terminología delta:** una capability puede ser **iniciada** por un change (primer `ADDED` de requirements) y **modificada** por changes posteriores (`ADDED`/`MODIFIED` sobre la misma capability). Está señalado por fase.

---

## 1. Tabla resumen

| Fase | Change | Capability | Depende de |
|---|---|---|---|
| **Etapa 0 — Bootstrap** ||||
| 0 | bootstrap-stack-repo | — (habilitación técnica) | — |
| **Etapa A — Foundation** ||||
| 1 | add-auth | auth (+roles base) | F0 |
| 2 | add-access-control | access-control | F1 |
| 3 | add-user-management | user-management (+ modifica auth y access-control: admin de perfiles) | F1, F2 |
| 4 | add-directory | directory (+ inicia credit: parámetros) | F1, F2 |
| 5 | add-products | products | F1, F2 |
| 6 | add-pricing | pricing | F4, F5 |
| 7 | add-bulk-import | bulk-import | F4, F5 |
| **Etapa B — Inventory Core** ||||
| 8 | add-system-settings | system-settings | F1, F2 |
| 9 | add-period-validation | period (validación) | F1 |
| 10 | add-audit-rules | audit | F1 |
| 11 | add-kardex | kardex | F5, F8, F9, F10 |
| 12 | add-intake | intake (+ inicia payables: obligación) | F4, F9, F10, F11 |
| 13 | add-merma | merma | F5, F8, F11 |
| **Etapa C — Commercial** ||||
| 14 | add-routes | routes (+ modifica merma) | F12, F13 |
| 15 | add-orders | orders | F4, F5 |
| 16 | add-deliveries | deliveries (+ modifica pricing, inicia receivables) | F4, F6, F11, F15 |
| 17 | add-returns | returns (+ modifica kardex) | F11, F16 |
| **Etapa D — Financial** ||||
| 18 | add-receivables | receivables (gestión) | F16 |
| 19 | add-payables | payables (gestión) | F12 |
| 20 | add-opening-balances | opening-balances (+ modifica kardex, receivables, payables) | F11, F18, F19 |
| 21 | add-credit-control | credit (comportamiento) + job diario | F4, F18, F19, F20 |
| 22 | add-notifications | notifications | F12, F16, F18, F19, F21 |
| **Etapa E — Analytics & Closing** ||||
| 23 | add-reports | reports | F11, F12, F14, F16, F18, F19 |
| 24 | add-dashboards | dashboards | F18, F19, F21 |
| 25 | add-period-closing | period (proceso de cierre) | todo |

---

## 2. Detalle por fase

> Cada ficha referencia las secciones del documento de requerimientos (v1.1) para trazabilidad. Donde se indica "gap", el alcance excede los requerimientos v1.1 (ver nota al final).

### Etapa 0 — Bootstrap

#### Fase 0 — bootstrap-stack-repo
- **Capability:** ninguna de negocio (habilitación técnica).
- **Depende de:** — · **Desbloquea:** todo.
- **Alcance:** monorepo, backend (Django/DRF/SimpleJWT), frontend (React 19/Vite/Refine v5/Shadcn), contrato de errores uniforme, tooling de calidad, CI/CD path-triggered, configuración de repositorio.
- **Fuera de alcance:** toda lógica de negocio.
- **Estado:** entregado (ver `00-bootstrap-stack-y-repositorio.md`).

### Etapa A — Foundation

#### Fase 1 — add-auth
- **Capability:** inicia `auth`; inicia la base de roles (modelo de usuario y roles del sistema).
- **Depende de:** F0 · **Desbloquea:** F2, F3, F4, F5, F8, F9, F10.
- **Alcance:** modelo de usuario; login (access + refresh); refresh; invalidación (blacklist del refresh); endpoint de usuario actual; **cambio de contraseña del usuario autenticado** (auto-servicio); roles base (Jefe, Supervisor, Responsable de ruta, Usuario) como estructura.
- **Fuera de alcance:** permisos finos por campo/acción y perfiles configurables (F2); gestión administrativa de usuarios y reset (F3).
- **Invariantes config:** SimpleJWT fijo (sin Supabase Auth); access 15 min / refresh 7 d; rate limiting en login.
- **Requerimientos:** 2.5.
- **Pendiente cliente:** —.

#### Fase 2 — add-access-control
- **Capability:** inicia `access-control`.
- **Depende de:** F1 · **Desbloquea:** F3, F4, F5, F8 (y precondición de permisos para el resto).
- **Alcance:** perfiles de usuario; matriz de permisos por perfil (módulos/acciones/campos); mecanismo de **campos invisibles** (no solo bloqueados) a nivel serializer; flag de **auto-aprobación** por perfil (la capacidad).
- **Fuera de alcance:** el campo costo invisible concreto y las reglas de auto-aprobación de ingreso (ambos en F12).
- **Invariantes config:** campos invisibles por perfil; control de acceso por perfil.
- **Requerimientos:** 2.4, 2.5.
- **Pendiente cliente:** —.

#### Fase 3 — add-user-management
- **Capability:** inicia `user-management`; modifica `auth` (flag de cambio forzado) y `access-control` (administración de perfiles, completando F2).
- **Depende de:** F1, F2 · **Desbloquea:** — (operativamente necesaria para el go-live; no bloquea la construcción de módulos de negocio, que se sirven con usuarios sembrados).
- **Alcance:** CRUD de usuarios (crear/editar/desactivar/reactivar); asignación y cambio de perfil (extiende el `assign-profile` de F2 para sincronizar el `role` nominal e invalidar el refresh); **reset administrativo** de contraseña; contraseña temporal con **cambio forzado en el primer login**; **desactivación que invalida (blacklist) el refresh** del usuario; **administración de perfiles** (editar permisos por módulo/acción + flags; baja con soft delete clase 2 validando que no haya usuarios asignados), completando lo que F2 dejó en modelo + mecanismo + seed.
- **Fuera de alcance:** cambio de contraseña propio (queda en F1); recuperación self-service por email (diferida a post-F25, solo si el cliente la pide — depende de la infraestructura de email de F22).
- **Invariantes config:** solo el Jefe gestiona identidad (usuarios y perfiles); auditoría de eventos de seguridad (reset, desactivación, cambio de perfil).
- **Requerimientos:** 2.5 (roles). El ciclo de vida de identidad es un **gap** respecto a v1.1.
- **Pendiente cliente:** —.

#### Fase 4 — add-directory
- **Capability:** inicia `directory`; inicia `credit` (solo campos de parámetros: plazo, límite, días de aviso).
- **Depende de:** F1, F2 · **Desbloquea:** F6, F7, F12, F15, F16, F21.
- **Alcance:** ficha de tercero (identificación con validación de cédula/RUC/pasaporte, contacto, roles múltiples: cliente/proveedor/chofer/responsable de ruta); condiciones comerciales (referencia a lista de precios, plazo de crédito, límite, días de anticipación default 2); estados (ACTIVO → BLOQUEADO → INACTIVO); **vínculo opcional User ↔ Ficha** (FK).
- **Fuera de alcance:** comportamiento de crédito (vencimiento/bloqueo automático/escalamiento → F21); la asignación efectiva de lista de precios requiere F6.
- **Invariantes config:** soft delete clase 3 (ficha = estado INACTIVO). Estrena los validadores de identificación ecuatoriana de `apps/common/validations.py`. Período cerrado N/A (maestro).
- **Requerimientos:** 3.1–3.4.
- **Pendiente cliente:** —.

#### Fase 5 — add-products
- **Capability:** inicia `products`.
- **Depende de:** F1, F2 · **Desbloquea:** F6, F7, F11, F13, F15.
- **Alcance:** categorías (nombre, días de caducidad default 7, tipo de ingreso gaveta/peso, **estructura** del rango de merma min/max); productos (nombre, categoría, UoM); tabla de unidades de medida (base: libras; factores de conversión).
- **Fuera de alcance:** los **valores** numéricos del rango de merma (pendiente cliente #1); la aplicación de merma (F13).
- **Invariantes config:** soft delete clase 2; pesos decimales en libras.
- **Requerimientos:** 4.1, 4.3, 16.2.
- **Pendiente cliente:** #1 (solo el valor del rango).

#### Fase 6 — add-pricing
- **Capability:** inicia `pricing`.
- **Depende de:** F4, F5 · **Desbloquea:** F16.
- **Alcance:** listas de precios (tipo normal/descarte); productos con precio por lista; asignación de lista a ficha de cliente desde Directorio.
- **Fuera de alcance:** inmutabilidad del precio en la entrega y marca de venta de descarte (se completan en F16).
- **Invariantes config:** soft delete clase 2.
- **Requerimientos:** 4.2.
- **Pendiente cliente:** —.

#### Fase 7 — add-bulk-import
- **Capability:** inicia `bulk-import`.
- **Depende de:** F4, F5 · **Desbloquea:** —.
- **Alcance:** importación masiva desde CSV/Excel de **maestros**: productos (con categorías y UoM) y fichas de Directorio; validación por fila; reporte de errores; modo **dry-run** (previsualizar antes de confirmar); idempotencia (no duplicar en re-cargas).
- **Fuera de alcance:** listas de precios; stock inicial y saldos (van en F20, `opening-balances`).
- **Invariantes config:** soft delete clase 2/3 según la entidad destino; contrato de errores uniforme (reporte de errores por fila).
- **Requerimientos:** **gap** de go-live (no en v1.1).
- **Pendiente cliente:** —.

### Etapa B — Inventory Core

#### Fase 8 — add-system-settings
- **Capability:** inicia `system-settings`.
- **Depende de:** F1, F2 · **Desbloquea:** F11, F13.
- **Alcance:** parámetros globales del sistema; **toggle de costeo nominal/efectivo** (cada base activable/desactivable de forma independiente); solo el Jefe edita.
- **Fuera de alcance:** la lógica de costeo que lee el toggle (vive en kardex/merma/reports).
- **Invariantes config:** doble costeo en paralelo (activable de forma independiente).
- **Requerimientos:** 14.2.
- **Pendiente cliente:** —.

#### Fase 9 — add-period-validation
- **Capability:** inicia `period` (regla de validación de período cerrado).
- **Depende de:** F1 · **Desbloquea:** F11, F12 (y todo documento con fecha).
- **Alcance:** entidad período (mes contable) con estado abierto/cerrado; regla transversal: antes de crear/modificar cualquier documento, validar que su fecha no pertenezca a un período cerrado; rechazo con error.
- **Fuera de alcance:** el proceso de cierre mensual —ejecución, acta, reversión— que llega en F25.
- **Invariantes config:** período cerrado.
- **Requerimientos:** 2.2.
- **Pendiente cliente:** —.

#### Fase 10 — add-audit-rules
- **Capability:** inicia `audit` (reglas sobre el mecanismo `@audit` del bootstrap).
- **Depende de:** F1 · **Desbloquea:** F11, F12 (correcciones auditables).
- **Alcance:** reglas de qué se audita: toda corrección sobre un documento generado registra fecha/hora, usuario, campo, valor anterior y valor nuevo; consulta del log.
- **Fuera de alcance:** las correcciones específicas (peso/costo) que se conectan en F11/F12.
- **Invariantes config:** auditoría de correcciones.
- **Requerimientos:** 2.3.
- **Pendiente cliente:** —.

#### Fase 11 — add-kardex
- **Capability:** inicia `kardex`.
- **Depende de:** F5, F8, F9, F10 · **Desbloquea:** F12, F13, F16, F17, F20, F23.
- **Alcance:** estructura del Kardex por categoría; tipos de movimiento (ingreso, despiece, entrega, devolución, merma, baja por caducidad); identificador propio de gaveta; despiece total/parcial vinculado a la unidad origen; **FIFO** para despacho (saldo nunca negativo); alertas de caducidad por categoría; baja por caducidad; corrección de peso posterior con recálculo en cascada (rango de merma + costo nominal/efectivo); exportes PDF/Excel.
- **Fuera de alcance:** el origen de los movimientos (ingreso real F12, entrega F16, devolución F17); el costeo de merma (F13).
- **Invariantes config:** kardex append-only; FIFO; doble costeo (recálculo); período cerrado; auditoría (corrección).
- **Requerimientos:** 5.1–5.9.
- **Pendiente cliente:** —.

#### Fase 12 — add-intake
- **Capability:** inicia `intake`; inicia `payables` (entidad obligación CxP).
- **Depende de:** F4, F9, F10, F11 · **Desbloquea:** F14, F19, F22, F23.
- **Alcance:** ingreso de mercadería con 4 estados (BORRADOR → VERIFICADO → COSTEO → GENERADO); responsables por etapa; afectación de Kardex en VERIFICADO; costeo con último costo sugerido; campo costo **invisible** para responsable de ruta (uso real del mecanismo de F2); corrección de peso/costo incluso en GENERADO (cascada + auditoría); **auto-aprobación** (uso real del flag de F2); generación automática de **obligación CxP** al pasar a GENERADO (entidad + vencimiento por plazo del proveedor).
- **Fuera de alcance:** gestión de pagos/cheques/notas de crédito (F19); cuadre al cierre de ruta (F14).
- **Invariantes config:** campos invisibles (costo); auto-aprobación; kardex append-only; período cerrado; auditoría; doble costeo; transacción atómica (Kardex+CxP+estado).
- **Requerimientos:** 6.1–6.6, 12.2.
- **Pendiente cliente:** —.

#### Fase 13 — add-merma
- **Capability:** inicia `merma`.
- **Depende de:** F5, F8, F11 · **Desbloquea:** F14.
- **Alcance:** parametrización de rango por categoría (consume la estructura de F5); fórmulas de **doble costeo** como funciones puras testeables (nominal = precio ÷ peso de ingreso; efectivo = precio ÷ peso utilizable; merma valorizada); aplicación en despiece (diferencia de peso entre unidad origen y partes).
- **Fuera de alcance:** el registro de merma al cierre de ruta (F14); los reportes de merma (F23).
- **Invariantes config:** doble costeo. Gate de cobertura ≥90% por ser cálculo financiero (funciones puras sin ORM).
- **Requerimientos:** 16.1–16.6, 14.2.
- **Pendiente cliente:** #1 (valores de rango).

### Etapa C — Commercial

#### Fase 14 — add-routes
- **Capability:** inicia `routes`; modifica `merma` (registro al cierre de ruta).
- **Depende de:** F12, F13 · **Desbloquea:** F23.
- **Alcance:** tipos de ruta A/B; estructura (camión con una ruta activa, paradas de retiro/entrega, 1..N entregas); asignación chofer/responsable; gastos de ruta; rentabilidad por ruta y global (costeo nominal/efectivo, gastos, valor de entregas); **cierre con cuadre** (peso ingresado = entregado + merma + sobrante) → genera el movimiento de merma en Kardex; bloqueo de cierre si excede el rango + observación justificada + aprobación.
- **Fuera de alcance:** las entregas en sí (F16).
- **Invariantes config:** cuadre de ruta; doble costeo; kardex append-only; período cerrado.
- **Requerimientos:** 7.1–7.8, 6.6, 16.4.
- **Pendiente cliente:** —.

#### Fase 15 — add-orders
- **Capability:** inicia `orders`.
- **Depende de:** F4, F5 · **Desbloquea:** F16.
- **Alcance:** pedido (cabecera cliente/fecha/ruta opcional; detalle con peso unitario opcional para peso variable); no reserva stock; conversión manual a entrega (pre-carga, consolidación de múltiples pedidos); cumplimiento parcial (estado PARCIAL, cierre manual); estados (CONFIRMADO → PARCIAL → COMPLETADO/CERRADO/CANCELADO).
- **Fuera de alcance:** la entrega resultante (F16).
- **Invariantes config:** período cerrado.
- **Requerimientos:** 8.1–8.6.
- **Pendiente cliente:** —.

#### Fase 16 — add-deliveries
- **Capability:** inicia `deliveries`; modifica `pricing` (inmutabilidad + descarte); inicia `receivables` (entidad obligación CxC).
- **Depende de:** F4, F6, F11, F15 · **Desbloquea:** F17, F18, F22, F23.
- **Alcance:** entrega (egreso, detalle, precio desde la lista asignada al cliente); **snapshot inmutable** de precios y datos del cliente al pasar a GENERADO; **FIFO** (consume Kardex); rebaja de Kardex en GENERADO; entrega con **cliente bloqueado** (BORRADOR → aprobación → GENERADO/DESCARTADO); **venta de descarte** (lista de tipo descarte → marca automática visible en rentabilidad); generación de **obligación CxC**.
- **Fuera de alcance:** gestión de cobros/cheques (F18); devoluciones (F17).
- **Invariantes config:** snapshot inmutable; FIFO; kardex append-only; período cerrado; transacción atómica (Kardex+CxC).
- **Requerimientos:** 9.1–9.5, 5.6.
- **Pendiente cliente:** —.

#### Fase 17 — add-returns
- **Capability:** inicia `returns`; modifica `kardex` (reintegro).
- **Depende de:** F11, F16 · **Desbloquea:** — (alimenta el ajuste de saldo de receivables).
- **Alcance:** devolución vinculada a una entrega de origen (obligatorio); reintegro del producto al Kardex; ajuste del saldo del cliente contra la entrega de origen (no crédito genérico); aprobación de jefe/supervisor.
- **Fuera de alcance:** —.
- **Invariantes config:** kardex append-only; período cerrado; reversión verifica restauración en Kardex y saldo.
- **Requerimientos:** 10.1–10.4.
- **Pendiente cliente:** —.

### Etapa D — Financial

#### Fase 18 — add-receivables
- **Capability:** modifica `receivables` (gestión de cobros sobre la entidad iniciada en F16).
- **Depende de:** F16 · **Desbloquea:** F20, F21, F22, F23, F24.
- **Alcance:** registro de cobros (efectivo/transferencia/depósito/cheque); flujo BORRADOR → APROBADO/RECHAZADO → ANULADO; aplicación al saldo CxC; cobro parcial; aplicación a múltiples entregas; **manejo de cheques** (fecha diferida; estados PENDIENTE DE COBRO/COBRADO/REBOTADO; cargo por rebote).
- **Fuera de alcance:** conciliación bancaria (pendiente #3); notificación de cobro validado (F22).
- **Invariantes config:** período cerrado; auditoría; transacción atómica.
- **Requerimientos:** 11.1–11.7.
- **Pendiente cliente:** #3 (conciliación bancaria).

#### Fase 19 — add-payables
- **Capability:** modifica `payables` (gestión de pagos sobre la entidad iniciada en F12).
- **Depende de:** F12 · **Desbloquea:** F20, F21, F22, F23, F24.
- **Alcance:** registro de pagos a proveedor (medios); flujo BORRADOR → APROBADO/RECHAZADO → ANULADO; aplicación al saldo CxP; pago parcial; aplicación a múltiples ingresos; cheques emitidos (estados); **notas de crédito de proveedor** (vinculadas a un ingreso, aplicación inmediata sin aprobación, notifican a jefe/supervisor).
- **Fuera de alcance:** conciliación bancaria (pendiente #3); notificaciones (F22).
- **Invariantes config:** nota de crédito siempre vinculada a un ingreso; período cerrado; auditoría.
- **Requerimientos:** 12.1–12.8.
- **Pendiente cliente:** #3 (conciliación bancaria).

#### Fase 20 — add-opening-balances
- **Capability:** inicia `opening-balances`; modifica `kardex`, `receivables`, `payables`.
- **Depende de:** F11, F18, F19 · **Desbloquea:** F21.
- **Alcance:** carga **masiva desde archivo** (CSV/Excel) para el go-live: stock inicial en Kardex (movimiento de apertura que **no** genera CxP), saldos iniciales de CxC por cliente y de CxP por proveedor con sus vencimientos; misma validación por fila y dry-run que `bulk-import`.
- **Fuera de alcance:** importación masiva de catálogos (F7).
- **Invariantes config:** kardex append-only (apertura como movimiento especial trazable); período cerrado (la apertura define el punto de inicio).
- **Requerimientos:** **gap** de go-live (no en v1.1).
- **Pendiente cliente:** —.

#### Fase 21 — add-credit-control
- **Capability:** modifica `credit` (comportamiento); inicia el job diario (parte de vencimientos).
- **Depende de:** F4, F18, F19, F20 · **Desbloquea:** F22, F24.
- **Alcance:** comportamiento de crédito para CxC y CxP: secuencia vencimiento → alerta → bloqueo de ficha → escalamiento al jefe; notificación anticipada (N días configurable por ficha, default 2); job diario de Cloud Scheduler **idempotente** que dispara los vencimientos; la entrega con ficha bloqueada genera BORRADOR con alerta (conecta con F16).
- **Fuera de alcance:** el canal de notificación en sí (F22). La caducidad disparada por el job vive en `kardex` (F11) y se referencia aquí.
- **Invariantes config:** período cerrado; idempotencia del job diario.
- **Requerimientos:** 3.3, 13.2.
- **Pendiente cliente:** —.

#### Fase 22 — add-notifications
- **Capability:** inicia `notifications`.
- **Depende de:** F12, F16, F18, F19, F21 · **Desbloquea:** —.
- **Alcance:** infraestructura de email (Resend con dominio verificado) y WhatsApp (Meta Cloud API directo, sin BSP); motor de plantillas; eventos (ingreso registrado, entrega generada, cobro validado, nota de crédito, vencimientos próximos, escalamiento); notificaciones unidireccionales; integración con el job diario.
- **Fuera de alcance:** —.
- **Invariantes config:** —.
- **Requerimientos:** 13.1–13.3.
- **Pendiente cliente:** #2 (plantillas de texto y formato de adjunto).

### Etapa E — Analytics & Closing

#### Fase 23 — add-reports
- **Capability:** inicia `reports`.
- **Depende de:** F11, F12, F14, F16, F18, F19 · **Desbloquea:** —.
- **Alcance:** reportes operativos y financieros (Kardex; ingresos; entregas; ingresos con entregas; rutas con entregas; pedidos; cartera CxC; cartera CxP; merma; rentabilidad de rutas); exportación PDF (WeasyPrint) y Excel (openpyxl); doble costeo en rentabilidad; identificación de ventas de descarte; advertencia visible cuando hay ingresos sin costo (VERIFICADO/COSTEO).
- **Fuera de alcance:** dashboards (F24); los reportes adicionales del catálogo (pendiente #4).
- **Invariantes config:** doble costeo.
- **Requerimientos:** 14.1, 14.2, 5.9.
- **Pendiente cliente:** #4 (catálogo completo de reportes).

#### Fase 24 — add-dashboards
- **Capability:** inicia `dashboards`.
- **Depende de:** F18, F19, F21 · **Desbloquea:** —.
- **Alcance:** dashboard de cliente (CxC) y de proveedor (CxP), ambos como vistas de **consulta** (sin acciones): encabezado (límite/utilizado/disponible, % de utilización, promedio de días de pago, % a tiempo vs. atraso); entregas/ingresos pendientes de pago; historial de cobros/pagos.
- **Fuera de alcance:** cualquier acción ejecutable (son solo consulta).
- **Invariantes config:** —.
- **Requerimientos:** 14.3, 14.4.
- **Pendiente cliente:** —.

#### Fase 25 — add-period-closing
- **Capability:** modifica `period` (proceso de cierre mensual sobre la entidad iniciada en F9).
- **Depende de:** todo · **Desbloquea:** —.
- **Alcance:** cierre mensual (solo Jefe): validación de condiciones (sin pedidos abiertos; sin entregas BORRADOR; sin cobros/pagos en RECHAZADO o BORRADOR; único saldo permitido CxC/CxP); bloqueo del período; **acta versionada** (V1, V2…) generada por plantilla con `template_version`, sin persistir PDF; reversión (nota de reversión sobre el acta histórica, desbloqueo, nueva versión).
- **Fuera de alcance:** —.
- **Invariantes config:** período cerrado; acta por plantilla con `template_version` (sin persistir archivo).
- **Requerimientos:** 15.1–15.6.
- **Pendiente cliente:** —.

---

## 3. Pendientes de cliente consolidados

| # | Pendiente | Fase(s) afectada(s) | Bloquea |
|---|---|---|---|
| 1 | Valores de rango de merma (min/max en libras) por categoría | F5, F13, F14 | El **valor**, no la estructura del campo (F5) ni las fórmulas (F13) |
| 2 | Plantillas de texto y formato de adjunto de notificaciones | F22 | El contenido de las plantillas; la infraestructura puede construirse |
| 3 | Alcance de la conciliación bancaria | F18, F19 | El módulo de conciliación; cobros/pagos base no se bloquean |
| 4 | Catálogo completo de reportes adicionales | F23 | Reportes extra; los reportes base del requerimiento no se bloquean |

Ninguno de los cuatro pendientes bloquea las etapas Foundation ni Inventory Core. El primero que entra en juego es #1, y solo afecta valores numéricos, no estructura.

---

## 4. Notas de diseño no obvias

**1. `payables` y `receivables` se inician en el documento que los origina, no en Financial.**
La *entidad* de obligación CxP nace en `add-intake` (F12) y la CxC en `add-deliveries` (F16). La *gestión* (registrar pagos/cobros, cheques, aprobación) llega en F19/F18. Cada capability es alimentada por dos changes en momentos distintos — el modelo delta de OpenSpec lo soporta directamente.

**2. `credit` se reparte en dos.**
Los *parámetros* de crédito (plazo, límite, días de aviso) entran como campos en `add-directory` (F4). El *comportamiento* (vencimiento → alerta → bloqueo → escalamiento) llega en `add-credit-control` (F21), porque necesita los saldos que producen F18 y F19, más el job diario.

**3. `period` aparece en dos momentos.**
`add-period-validation` (F9) añade la regla de validación de período cerrado, que casi todo documento usa. `add-period-closing` (F25) añade el proceso de cierre, el acta versionada y la reversión sobre la misma capability.

**4. La carga de go-live se divide en dos capacidades, y se construye tarde aunque se use primero.**
`add-bulk-import` (F7) cubre los **maestros** (productos, fichas) y puede correr temprano. `add-opening-balances` (F20) cubre **stock inicial y saldos CxC/CxP**, y depende de que Kardex, receivables y payables existan — por eso se construye en Financial, aunque en la operación real es lo primero que se ejecuta al migrar desde Excel.

**5. Identidad repartida entre tres fases.**
`add-auth` (F1) cubre login y la contraseña propia del usuario autenticado; `add-access-control` (F2) los permisos por perfil; `add-user-management` (F3) la administración (alta/baja, rol, reset administrativo). El vínculo User ↔ Ficha se modela en F4 con un FK opcional.

---

## 5. Estado de fases

| Fase | Estado |
|---|---|
| 0 | entregado |
| 1–25 | pendiente |

*El estado se actualiza a medida que cada change se archiva (`/opsx:archive`).*

---

## 6. Registro de cambios

### v1.1
| # | Cambio | Tipo |
|---|---|---|
| 1 | `add-user-management` (F3): ciclo de vida de identidad — alta/baja, asignación/cambio de perfil, reset administrativo, contraseña temporal, desactivación que invalida refresh; más la administración de perfiles que completa F2 | Nueva fase |
| 2 | `add-bulk-import` (F7): importación masiva CSV/Excel de maestros (productos, fichas) | Nueva fase |
| 3 | `add-system-settings` (F8): parámetros del sistema, incl. toggle de costeo nominal/efectivo | Nueva fase |
| 4 | `add-opening-balances` (F20): carga inicial de stock y saldos CxC/CxP para go-live | Nueva fase |
| 5 | Renumeración global de 21 a 25 fases y recálculo de dependencias | Estructura |
| 6 | Vínculo User ↔ Ficha (FK opcional) explicitado en F4 y nota de diseño 5 | Modelado |
