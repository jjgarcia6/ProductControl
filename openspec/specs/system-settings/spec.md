# system-settings Specification

## Purpose

Configuración global del sistema modelada como singleton: una única fila de parámetros globales que
gobierna los toggles de costeo (`costing_nominal_enabled`, `costing_effective_enabled`). Solo el Jefe
edita la configuración; el Supervisor la consulta en solo lectura. Todo cambio queda auditado.

## Requirements

### Requirement: Configuración global como singleton

El sistema MUST exponer una única fila de configuración global, recuperable sin identificador. El
sistema MUST NOT permitir crear ni eliminar filas de configuración. Los errores MUST seguir el
contrato uniforme.

#### Scenario: El Jefe recupera la configuración global

- **DADO** un usuario cuyo perfil permite `system-settings.read`
- **CUANDO** solicita la configuración global en `GET /system-settings`
- **ENTONCES** el Backend MUST responder `200` con los toggles de costeo actuales

#### Scenario: La siembra conserva una sola fila de configuración

- **DADO** que la configuración ya existe (sembrada)
- **CUANDO** se ejecuta la siembra de nuevo
- **ENTONCES** el sistema MUST conservar exactamente una fila de configuración

### Requirement: Toggles de costeo independientes

Cada base de costeo (`costing_nominal_enabled`, `costing_effective_enabled`) MUST poder activarse o
desactivarse de forma independiente mediante `PATCH` parcial en `/system-settings`.

#### Scenario: El Jefe desactiva solo la base efectiva

- **DADO** ambas bases de costeo activas
- **CUANDO** el Jefe desactiva únicamente la base efectiva
- **ENTONCES** el Backend MUST persistir `costing_effective_enabled=false` y conservar
  `costing_nominal_enabled=true` dentro de `transaction.atomic()`

#### Scenario: El Jefe reactiva la base nominal

- **DADO** la base nominal desactivada y la efectiva activa
- **CUANDO** el Jefe reactiva la base nominal
- **ENTONCES** el Backend MUST persistir ambas bases activas

### Requirement: Al menos una base de costeo activa

El sistema MUST rechazar toda operación que dejaría ambas bases de costeo desactivadas
simultáneamente.

#### Scenario: El Jefe intenta desactivar ambas bases

- **DADO** solo una base de costeo activa
- **CUANDO** el Jefe intenta desactivar también la base restante
- **ENTONCES** el Backend MUST retornar HTTP `400 Bad Request` con `{campo: [mensajes]}` en
  `non_field_errors` (validación cruzada, no atada a un campo)
- **Y** el Frontend MUST mostrar el mensaje como aviso general (no atado a un campo)

### Requirement: Solo el Jefe edita; el Supervisor consulta

La edición de la configuración MUST estar restringida a perfiles con `system-settings` en `update`. La
lectura MUST estar disponible para perfiles con `system-settings` en `read`.

#### Scenario: El Jefe edita la configuración

- **DADO** un Jefe con `system-settings` en `update`
- **CUANDO** modifica un toggle de costeo válido
- **ENTONCES** el Backend MUST aplicar el cambio y responder `200`

#### Scenario: El Supervisor consulta la configuración

- **DADO** un Supervisor con `system-settings` en `read` (sin `update`)
- **CUANDO** recupera la configuración
- **ENTONCES** el Backend MUST responder `200` con los toggles
- **Y** el Frontend MUST mostrar los controles en solo lectura (deshabilitados)

#### Scenario: El Supervisor no puede editar la configuración

- **DADO** un Supervisor con `system-settings` en `read` (sin `update`)
- **CUANDO** intenta modificar un toggle
- **ENTONCES** el Backend MUST retornar HTTP `403 Forbidden` con `{detail}` genérico

#### Scenario: Un usuario sin sesión accede a la configuración

- **DADO** un usuario sin sesión activa (token SimpleJWT)
- **CUANDO** intenta recuperar o modificar la configuración
- **ENTONCES** el Backend MUST retornar HTTP `401 Unauthorized`
- **Y** el Frontend MUST redirigir al login (authProvider de Refine)

### Requirement: Auditoría del cambio de configuración

Toda modificación de la configuración MUST registrar un evento de auditoría con usuario, fecha/hora,
campo, valor anterior y valor nuevo.

#### Scenario: Cambiar un toggle deja rastro de auditoría

- **DADO** un Jefe autorizado
- **CUANDO** desactiva una base de costeo
- **ENTONCES** el Backend MUST registrar un evento de auditoría con el campo, el valor anterior y el
  valor nuevo
- **Y** el usuario que realizó el cambio
