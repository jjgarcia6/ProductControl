# Delta para audit

<!-- Scenarios de dominio del mecanismo (comportamiento de `record_field_changes` y del registro de -->
<!-- reglas), NO endpoints HTTP: F10 no tiene superficie de red. Por eso los escenarios negativos -->
<!-- expresan el comportamiento rechazado del mecanismo (sin fila) en lugar de un código HTTP. -->
<!-- RFC 2119 en inglés (MUST/MUST NOT/SHALL); Gherkin en español (DADO/CUANDO/ENTONCES). -->

## ADDED Requirements

### Requirement: Vocabulario de acciones de auditoría

El sistema MUST exponer un conjunto canónico de acciones de auditoría (`CREATE`, `UPDATE`,
`CORRECTION`, `SOFT_DELETE`, `STATE_CHANGE`). Los valores persistidos MUST coincidir con los literales
ya usados por los services existentes para las acciones equivalentes, de modo que el retrofit de
constantes NO cambie ningún dato persistido.

#### Scenario: La acción de corrección se distingue de la actualización

- **DADO** una corrección post-generación sobre un documento
- **CUANDO** se registra el evento de auditoría
- **ENTONCES** la acción registrada es `CORRECTION` y NO `UPDATE`

#### Scenario: El retrofit de constantes preserva el valor persistido

- **DADO** un service de F1–F7 que antes registraba el literal `"UPDATE"`
- **CUANDO** se sustituye el literal por `AuditAction.UPDATE`
- **ENTONCES** el valor persistido en `AuditLog.action` sigue siendo `"UPDATE"`

### Requirement: Registro de correcciones a nivel de campo

Toda corrección sobre un campo registrado como auditable MUST generar un registro de auditoría **por
campo modificado**, con usuario, fecha/hora, campo, valor anterior y valor nuevo. Un campo NO registrado
como auditable MUST NOT generar registro. Un campo sin cambio real MUST NOT generar registro.

#### Scenario: Corrección de un campo auditado

- **DADO** una entidad con el campo `weight` registrado como auditable
- **CUANDO** se corrige `weight` de un valor anterior a uno nuevo
- **ENTONCES** el sistema crea un registro de auditoría con acción `CORRECTION`, el campo `weight`, el
  valor anterior, el valor nuevo y el usuario

#### Scenario: Corrección de múltiples campos

- **DADO** una entidad con `weight` y `cost` registrados como auditables
- **CUANDO** se corrigen ambos en una operación
- **ENTONCES** el sistema crea **dos** registros de auditoría, uno por campo

#### Scenario: Campo no auditable no genera registro

- **DADO** una entidad con un campo NO registrado como auditable
- **CUANDO** ese campo cambia
- **ENTONCES** el sistema NO crea registro para ese campo

#### Scenario: Sin cambio real no genera registro

- **DADO** un campo auditable cuyo valor nuevo es igual al anterior
- **CUANDO** se procesa la operación
- **ENTONCES** el sistema NO crea registro para ese campo

### Requirement: Normalización de valores del rastro

Los valores anterior y nuevo MUST persistirse mediante una normalización consistente: los decimales
como cadena en notación simple (sin notación científica), las fechas en formato ISO, las claves foráneas
como su identificador, y los valores nulos como cadena vacía. La comparación anterior≠nuevo MUST hacerse
sobre la forma normalizada.

#### Scenario: Normalización de un decimal

- **DADO** una corrección de un campo de peso con valor `Decimal("12.50")`
- **CUANDO** se registra
- **ENTONCES** el valor nuevo se persiste como `"12.50"` (sin notación científica ni ceros ambiguos)

#### Scenario: Normalización de un valor nulo

- **DADO** una corrección donde el valor anterior es `None` y el nuevo es un valor no nulo
- **CUANDO** se registra
- **ENTONCES** el valor anterior se persiste como cadena vacía (`""`) y el registro se crea por haber cambio real

### Requirement: Compatibilidad del evento grueso

El decorador `@audit(action, entity)` MUST seguir registrando el evento de acción (usuario, acción,
entidad, identificador de objeto) sin diff campo-nivel. El comportamiento observable de los services
existentes MUST NOT cambiar.

#### Scenario: Evento grueso preservado

- **DADO** un service existente decorado con `@audit`
- **CUANDO** se ejecuta con éxito
- **ENTONCES** se crea un registro con la acción y la entidad, sin campos de diff (`field`, `old_value`,
  `new_value` vacíos)
