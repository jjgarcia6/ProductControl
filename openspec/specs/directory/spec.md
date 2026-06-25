# directory Specification

## Purpose

Gestión del Directorio de terceros: fichas con nombre o razón social, identificación validada (cédula,
RUC o pasaporte con dígito verificador), uno o varios roles (cliente, proveedor, responsable de ruta,
chofer), datos de contacto, máquina de estados (ACTIVO/BLOQUEADO/INACTIVO con baja lógica reversible —
soft delete clase 3) y vínculo opcional 1:1 con un usuario del sistema. La autorización fina se resuelve
por el perfil del usuario (capability `access-control`).

<!-- Keywords Gherkin en español (DADO/CUANDO/ENTONCES/Y); keywords normativos RFC 2119 en inglés. -->

## Requirements

### Requirement: Ficha de tercero
La ficha MUST registrar nombre o razón social, tipo de identificación (cédula, RUC o pasaporte) y un
número de identificación válido para ese tipo. El número MUST ser único entre las fichas no inactivas.
La validación de cédula y RUC MUST usar el dígito verificador; el pasaporte se acepta sin checksum. Los
errores MUST seguir el contrato uniforme.

#### Scenario: Supervisor crea una ficha con identificación válida
- DADO un usuario con perfil autorizado en la vista de Directorio
- Y un tipo de identificación y un número válido para ese tipo, con al menos un rol
- CUANDO el Frontend envía la solicitud a `POST /directory/fichas`
- ENTONCES el Backend MUST procesarla dentro de `transaction.atomic()` y persistir la ficha en estado ACTIVO
- Y el Backend MUST registrar la operación en `audit_log` con acción `CREATE`
- Y el Frontend MUST mostrar una notificación de éxito usando tokens del theme

#### Scenario: Supervisor crea una ficha con dígito verificador inválido
- DADO un número de cédula o RUC que no pasa el dígito verificador
- CUANDO el Frontend envía la solicitud a `POST /directory/fichas`
- ENTONCES el Backend MUST NOT persistir la ficha
- Y el Backend MUST retornar HTTP `400 Bad Request` con `{campo: [mensajes]}` en el campo del número
- Y el Frontend MUST mostrar el mensaje en el campo de identificación

#### Scenario: Supervisor crea una ficha con número de identificación duplicado
- DADO una ficha no inactiva con un número de identificación
- CUANDO el Frontend intenta `POST /directory/fichas` con el mismo número
- ENTONCES el Backend MUST NOT crear la segunda ficha
- Y el Backend MUST retornar HTTP `409 Conflict` con `{detail}` indicando el duplicado
- Y el Frontend MUST mostrar el mensaje al usuario

#### Scenario: Usuario sin autorización intenta gestionar fichas
- DADO un usuario cuyo perfil no permite gestionar el Directorio (o sin sesión activa)
- CUANDO intenta acceder a `POST /directory/fichas` o `PATCH /directory/fichas/{id}`
- ENTONCES el Backend MUST retornar HTTP `401 Unauthorized` o `403 Forbidden` con `{detail}` genérico
- Y el Backend MUST NOT crear ni modificar la ficha

### Requirement: Roles de la ficha
La ficha MUST tener al menos un rol entre cliente, proveedor, responsable de ruta y chofer, y MAY tener
varios. El sistema MUST rechazar una ficha sin rol.

#### Scenario: Supervisor crea una ficha con múltiples roles
- DADO una entidad que es cliente y proveedor
- CUANDO el Frontend envía `POST /directory/fichas` con ambos roles
- ENTONCES el Backend MUST persistir la ficha con los dos roles
- Y el Frontend MUST mostrar una notificación de éxito usando tokens del theme

#### Scenario: Supervisor intenta crear una ficha sin rol
- DADO un payload de ficha sin ningún rol
- CUANDO el Frontend intenta `POST /directory/fichas`
- ENTONCES el Backend MUST NOT crear la ficha
- Y el Backend MUST retornar HTTP `400 Bad Request` con `{campo: [mensajes]}` en el campo de roles
- Y el Frontend MUST mostrar el mensaje en el campo de roles

### Requirement: Contacto de la ficha
La ficha MUST poder almacenar email y teléfono/WhatsApp. Si se provee email, MUST tener formato válido.

#### Scenario: Supervisor guarda una ficha con email y teléfono válidos
- DADO un email con formato válido y un teléfono
- CUANDO el Frontend envía `POST /directory/fichas` con esos datos de contacto
- ENTONCES el Backend MUST persistir el contacto en la ficha
- Y el Frontend MUST mostrar una notificación de éxito usando tokens del theme

#### Scenario: Supervisor guarda una ficha con email mal formado
- DADO un email con formato inválido
- CUANDO el Frontend intenta guardar la ficha
- ENTONCES el Backend MUST retornar HTTP `400 Bad Request` con `{campo: [mensajes]}` en el campo del email
- Y el Frontend MUST mostrar el mensaje en el campo del email

### Requirement: Estados de la ficha
La ficha MUST transitar entre ACTIVO, BLOQUEADO e INACTIVO. ACTIVO y BLOQUEADO son intercambiables por
un perfil autorizado; INACTIVO es la baja lógica (soft delete clase 3) y MUST ser reversible a ACTIVO.
Las fichas INACTIVO MUST quedar excluidas de los listados operativos por defecto.

#### Scenario: Supervisor bloquea y reactiva una ficha
- DADO una ficha en estado ACTIVO
- CUANDO el Frontend envía `POST /directory/fichas/{id}/block`
- ENTONCES el Backend MUST dejar la ficha en BLOQUEADO dentro de `transaction.atomic()`
- Y el Backend MUST registrar la operación en `audit_log` con acción `STATE_CHANGE`
- Y un `POST /directory/fichas/{id}/unblock` posterior MUST devolverla a ACTIVO

#### Scenario: Supervisor da de baja una ficha y la reactiva
- DADO una ficha en estado ACTIVO
- CUANDO el Frontend envía `POST /directory/fichas/{id}/deactivate`
- ENTONCES el Backend MUST dejar la ficha en INACTIVO y registrar `audit_log` con acción `STATE_CHANGE`
- Y la ficha MUST dejar de aparecer en los listados operativos por defecto
- Y un `POST /directory/fichas/{id}/reactivate` posterior MUST devolverla a ACTIVO

#### Scenario: Usuario sin autorización intenta cambiar el estado de una ficha
- DADO un usuario cuyo perfil no permite gestionar el Directorio (o sin sesión activa)
- CUANDO intenta `POST /directory/fichas/{id}/block` (o cualquier transición)
- ENTONCES el Backend MUST retornar HTTP `401 Unauthorized` o `403 Forbidden` con `{detail}` genérico
- Y el Backend MUST NOT cambiar el estado de la ficha

### Requirement: Vínculo opcional con un usuario
Una ficha MAY estar vinculada a un usuario del sistema en relación uno a uno. La baja del usuario MUST
NOT borrar la ficha.

#### Scenario: Jefe vincula una ficha a un usuario sin ficha previa
- DADO una ficha y un usuario sin ficha previa
- CUANDO el Frontend envía `POST /directory/fichas/{id}/link-user` con ese usuario
- ENTONCES el Backend MUST establecer el vínculo 1:1 dentro de `transaction.atomic()` y registrar `audit_log` con acción `UPDATE`
- Y el usuario MUST acceder a su ficha y la ficha a su usuario

#### Scenario: Jefe intenta vincular un usuario que ya tiene ficha
- DADO un usuario ya vinculado a otra ficha
- CUANDO el Frontend intenta `POST /directory/fichas/{id}/link-user` con ese usuario
- ENTONCES el Backend MUST NOT crear el segundo vínculo
- Y el Backend MUST retornar HTTP `409 Conflict` con `{detail}` indicando que el usuario ya tiene ficha
- Y el Frontend MUST mostrar el mensaje al usuario
