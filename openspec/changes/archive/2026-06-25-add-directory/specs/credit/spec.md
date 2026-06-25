# Delta para la capability `credit`

> En F4 los términos de crédito son **solo datos**. El comportamiento de vencimiento, alerta y bloqueo
> automático se define en `credit-control` (F21).

## ADDED Requirements

### Requirement: Términos de crédito por faceta
El sistema MUST permitir definir términos de crédito por faceta (CLIENTE o PROVEEDOR) para una ficha,
con límite de crédito (default 0), plazo en días (default 0) y días de aviso de vencimiento (default 2).
MUST existir a lo sumo un juego de términos por (ficha, faceta).

#### Scenario: Supervisor define los términos de crédito de cliente
- DADO una ficha con rol cliente y un usuario con perfil autorizado
- CUANDO el Frontend envía `POST /credit/terms` con faceta CLIENTE, límite, plazo y días de aviso
- ENTONCES el Backend MUST procesarla dentro de `transaction.atomic()` y persistir los términos asociados a la ficha
- Y el Backend MUST registrar la operación en `audit_log` con acción `CREATE`
- Y el Frontend MUST mostrar una notificación de éxito usando tokens del theme

#### Scenario: Supervisor intenta crear términos duplicados para la misma faceta
- DADO una ficha con términos de faceta PROVEEDOR ya definidos
- CUANDO el Frontend intenta `POST /credit/terms` con otra faceta PROVEEDOR para la misma ficha
- ENTONCES el Backend MUST NOT crear el segundo juego de términos
- Y el Backend MUST retornar HTTP `409 Conflict` con `{detail}` indicando el duplicado
- Y el Frontend MUST mostrar el mensaje al usuario

#### Scenario: Usuario sin autorización intenta definir términos de crédito
- DADO un usuario cuyo perfil no permite gestionar condiciones comerciales (o sin sesión activa)
- CUANDO intenta `POST /credit/terms` o `PATCH /credit/terms/{id}`
- ENTONCES el Backend MUST retornar HTTP `401 Unauthorized` o `403 Forbidden` con `{detail}` genérico
- Y el Backend MUST NOT crear ni modificar los términos

### Requirement: Integridad entre faceta y rol
El sistema MUST NOT permitir términos de crédito de faceta CLIENTE si la ficha no tiene rol cliente, ni
de faceta PROVEEDOR si no tiene rol proveedor.

#### Scenario: Supervisor define términos de cliente sobre una ficha sin rol cliente
- DADO una ficha que solo tiene rol proveedor
- CUANDO el Frontend intenta `POST /credit/terms` con faceta CLIENTE
- ENTONCES el Backend MUST NOT crear los términos
- Y el Backend MUST retornar HTTP `400 Bad Request` con `{campo: [mensajes]}` indicando la incompatibilidad faceta↔rol
- Y el Frontend MUST mostrar el mensaje en el campo de faceta

#### Scenario: Supervisor define términos de proveedor sobre una ficha con rol proveedor
- DADO una ficha con rol proveedor
- CUANDO el Frontend envía `POST /credit/terms` con faceta PROVEEDOR
- ENTONCES el Backend MUST persistir los términos asociados a la ficha
- Y el Frontend MUST mostrar una notificación de éxito usando tokens del theme
