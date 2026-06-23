# Delta para {{domain}}
<!-- DRY: Antes de añadir un requisito, verificar que no exista ya en los specs base del dominio. -->
<!-- SRP: Cada escenario valida exactamente UNA condición. Sin escenarios combinados. -->
<!-- Dominios válidos: base, auth, usuarios, directorio, productos, kardex, ingresos, rutas, -->
<!-- pedidos, entregas, devoluciones, cobros, pagos, notificaciones, reportes, cierre, merma, trazabilidad. -->
<!-- Keywords Gherkin en español (DADO/CUANDO/ENTONCES/Y); keywords normativos RFC 2119 en inglés. -->

## ADDED Requirements

### Requirement: {{nombre descriptivo del requisito — qué hace el sistema, no cómo}}
<!-- Clean Code: El nombre del requisito MUST ser autoexplicativo. -->
<!-- Usa RFC 2119 (keywords en inglés): MUST, MUST NOT, SHOULD, MAY. -->
El sistema MUST...

#### Scenario: {{Actor}} {{realiza acción}} con {{condición de éxito}}
<!-- SRP: Este escenario cubre ÚNICAMENTE el flujo exitoso (Happy Path). -->
- **DADO** que el usuario con rol `{{Jefe|Supervisor|Responsable de ruta|Usuario}}` se encuentra en {{nombre de la vista}}
- **Y** que los datos ingresados cumplen con el esquema definido en el Diccionario de Datos
- **Y** que la fecha del documento NO pertenece a un período cerrado
- **CUANDO** el usuario ejecuta {{acción concreta, ej: "hace clic en 'Guardar'"}}
- **ENTONCES** el Frontend MUST enviar la solicitud al endpoint `{{VERBO /ruta}}`
- **Y** el Backend MUST procesar la solicitud dentro de `transaction.atomic()` y persistir en PostgreSQL
- **Y** el Backend MUST registrar la operación en `audit_log` con acción `{{CREATE|UPDATE|STATE_CHANGE|SOFT_DELETE}}`
- **Y** el Frontend MUST mostrar una notificación de éxito usando tokens del theme

#### Scenario: {{Actor}} {{realiza acción}} con {{condición de error de validación}}
<!-- SRP: Este escenario cubre ÚNICAMENTE el error de validación de entrada (400). -->
- **DADO** que el payload NO cumple con las restricciones del Diccionario de Datos
- **CUANDO** el Frontend intenta enviar la solicitud al endpoint `{{VERBO /ruta}}`
- **ENTONCES** el Backend MUST NOT procesar la solicitud
- **Y** el Backend MUST retornar HTTP `400 Bad Request` con el detalle del campo inválido (serializer DRF)
- **Y** el Frontend MUST mostrar el mensaje de error específico al usuario sin exponer detalles internos

#### Scenario: {{Actor}} {{realiza acción}} sin {{autorización requerida}}
<!-- SRP: Este escenario cubre ÚNICAMENTE el error de autenticación/autorización (401/403). -->
<!-- Incluir este escenario SOLO si el endpoint es protegido. Eliminar si es público. -->
- **DADO** que el usuario no tiene una sesión activa (token SimpleJWT) o su rol es `{{rol insuficiente}}`
- **CUANDO** intenta acceder al endpoint `{{VERBO /ruta}}`
- **ENTONCES** el Backend MUST retornar HTTP `401 Unauthorized` o `403 Forbidden`
- **Y** el Frontend MUST redirigir al usuario a la vista de login (authProvider de Refine)

#### Scenario: {{Actor}} {{realiza acción}} que causa conflicto de unicidad
<!-- SRP: Este escenario cubre ÚNICAMENTE el error de duplicado (409). -->
<!-- Incluir SOLO si aplica: identificación duplicada en Directorio, identificador de gaveta, etc. -->
- **DADO** que ya existe un registro activo con {{campo único}} = {{valor}}
- **CUANDO** el usuario intenta crear un nuevo registro con el mismo {{campo único}}
- **ENTONCES** el Backend MUST retornar HTTP `409 Conflict` con mensaje descriptivo
- **Y** el Frontend MUST mostrar el mensaje al usuario indicando el duplicado

---

### Escenarios específicos del dominio (usar cuando aplique)

#### Scenario: Operación afecta saldo de Kardex
<!-- Obligatorio cuando el cambio genera ingresos o egresos en el Kardex. -->
- **DADO** que el producto `{{codigo_producto}}` tiene saldo_cantidad = {{N}} y saldo_peso = {{P}} en el Kardex
- **CUANDO** se ejecuta la operación de {{ingreso|egreso}} por cantidad = {{M}} / peso = {{W}}
- **ENTONCES** el saldo MUST actualizarse a los nuevos valores
- **Y** el saldo NUNCA MUST ser negativo — si lo fuera, la operación MUST bloquearse con HTTP `400`
- **Y** se MUST registrar un nuevo `kardex_movement` con tipo = `{{ingreso|egreso|despiece|merma|devolucion|baja}}`
- **Y** el `kardex_movement` MUST ser append-only (no se edita ni se borra)

#### Scenario: Egreso consume lotes FIFO
<!-- Obligatorio cuando el egreso (entrega) consume stock de múltiples lotes. -->
- **DADO** que el producto tiene lotes [Lote A: qty={{X}} (más antiguo), Lote B: qty={{Y}}]
- **CUANDO** se genera una entrega por cantidad = {{Z}} donde Z > X
- **ENTONCES** el sistema MUST consumir primero el Lote A completo ({{X}} unidades)
- **Y** MUST consumir {{Z - X}} unidades del Lote B
- **Y** se MUST registrar cada consumo con su trazabilidad al lote de origen

#### Scenario: Despiece genera trazabilidad de partes
<!-- Obligatorio cuando el cambio crea o modifica un despiece. -->
- **DADO** que existe una unidad origen `{{identificador}}` con cantidad = {{N}} y peso = {{P}}
- **CUANDO** se registra un despiece {{total|parcial}}
- **ENTONCES** el Kardex MUST registrar la salida (parcial o total) de la unidad origen
- **Y** MUST registrar la entrada de las partes obtenidas vinculadas al identificador de origen
- **Y** la diferencia de peso (origen − suma de partes) MUST registrarse como merma dentro del rango parametrizado

#### Scenario: Documento rechazado por período cerrado
<!-- Obligatorio para toda creación/modificación de documentos con fecha. -->
- **DADO** que el período {{mes/año}} está CERRADO
- **CUANDO** el usuario intenta crear o modificar un documento con fecha dentro de ese período
- **ENTONCES** el Backend MUST rechazar la operación con HTTP `409 Conflict`
- **Y** el Frontend MUST mostrar el mensaje indicando que el período está cerrado

#### Scenario: Cuadre al cierre de ruta
<!-- Obligatorio cuando el cambio toca el cierre de ruta o la merma. -->
- **DADO** una ruta EN CURSO con peso_ingresado = {{PI}}, peso_entregado = {{PE}} y peso_sobrante = {{PS}}
- **CUANDO** se ejecuta el cierre de la ruta
- **ENTONCES** el sistema MUST validar que peso_ingresado = peso_entregado + merma + peso_sobrante
- **Y** si la diferencia (merma) está dentro del rango parametrizado, MUST generar el movimiento de merma automáticamente
- **Y** si la diferencia supera el máximo, MUST bloquear el cierre y exigir observación justificada + aprobación de Supervisor/Jefe

#### Scenario: Snapshot inmutable de la entrega
<!-- Obligatorio cuando el cambio toca entregas o listas de precios. -->
- **DADO** una entrega en estado BORRADOR con precios de la lista asignada al cliente
- **CUANDO** la entrega pasa a estado GENERADO
- **ENTONCES** el sistema MUST congelar un snapshot inmutable de los precios y los datos del destinatario
- **Y** cambios posteriores en el catálogo o en la ficha del cliente MUST NOT afectar la entrega generada

#### Scenario: Nota de crédito de proveedor vinculada a ingreso
<!-- Obligatorio cuando el cambio toca pagos a proveedores (CxP). -->
- **DADO** un Ingreso de mercadería en estado GENERADO con saldo CxP = {{S}}
- **CUANDO** el Supervisor/Jefe registra una nota de crédito por monto = {{NC}} vinculada a ese Ingreso
- **ENTONCES** el saldo CxP del Ingreso MUST reducirse a {{S − NC}}
- **Y** la nota de crédito MUST estar vinculada a ese Ingreso específico (nunca crédito genérico)
- **Y** se MUST notificar al Jefe y al Supervisor

#### Scenario: Reversión de efectos (devolución / anulación)
<!-- Obligatorio para devoluciones, anulación de cobros/pagos y reversión de cierre. -->
- **DADO** que el documento `{{entrega|cobro|pago|cierre}}` con id={{ID}} está {{GENERADO|APROBADO|CERRADO}}
- **Y** {{condición de bloqueo o no bloqueo, ej: la entrega no tiene cobros aplicados}}
- **CUANDO** el usuario ejecuta {{devolución | anulación | reversión}}
- **ENTONCES** el estado MUST cambiar al estado de reversión correspondiente
- **Y** se MUST revertir los efectos: {{Kardex reintegrado / saldo CxC|CxP restaurado / período desbloqueado}}
- **Y** se MUST registrar la acción y el `audit_log` correspondiente

#### Scenario: Baja de catálogo bloqueada por dependencias
<!-- Obligatorio cuando la baja (soft delete) de un dato maestro tiene precondiciones. -->
- **DADO** que el {{catálogo, ej: lista de precios}} está referenciado por {{fichas/entregas activas}}
- **CUANDO** el usuario intenta darlo de baja (soft delete)
- **ENTONCES** el Backend MUST retornar HTTP `409 Conflict`
- **Y** el mensaje MUST indicar las dependencias que lo bloquean
- **Y** el Frontend MUST mostrar la lista de dependencias

---

## MODIFIED Requirements
<!-- DRY: Solo listar el delta. No reproducir el requisito completo si solo cambia una parte. -->
<!-- Indicar explícitamente el valor anterior y el nuevo valor para facilitar la revisión. -->

### Requirement: {{nombre exacto del requisito existente a modificar}}
{{Descripción del nuevo comportamiento usando RFC 2119 (keywords en inglés).}}
*(Anteriormente: {{descripción breve del comportamiento previo que se reemplaza}})*

#### Scenario: {{nombre del escenario modificado}}
<!-- Solo documentar los escenarios que cambian. Los escenarios sin cambios no se repiten (DRY). -->
- **DADO** ...
- **CUANDO** ...
- **ENTONCES** ...

---

## REMOVED Requirements
<!-- Documentar brevemente qué se elimina y POR QUÉ. Sin dejar eliminaciones sin justificación. -->

### Requirement: {{nombre exacto del requisito a eliminar}}
*(Eliminado porque: {{razón concisa, ej: "reemplazado por el Requisito X", "fuera del alcance definido"}})*
