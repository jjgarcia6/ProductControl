# access-control Specification

## Purpose

Control de acceso basado en perfiles de permisos: define perfiles que agrupan permisos por
`(módulo, acción)` y flags de capacidad, los asigna a usuarios (uno por usuario), y resuelve la
autorización del sistema por el perfil del usuario en lugar de su `role` nominal. Incluye campos
invisibles por perfil, la capacidad estructural de auto-aprobación y los perfiles semilla del sistema.

## Requirements

### Requirement: Perfil de permisos
El sistema MUST permitir definir perfiles que agrupan permisos. Cada perfil MUST tener un nombre
único y un conjunto de permisos por `(módulo, acción)` tomados de un catálogo conocido, además de
flags de capacidad. Los perfiles son catálogo configurable (soft delete clase 2). Los errores de
validación MUST seguir el contrato de errores uniforme.

#### Scenario: Jefe crea un perfil con permisos válidos
- **DADO** que el usuario con rol `Jefe` dispone de un catálogo de módulos y acciones conocido
- **Y** que los datos ingresados cumplen con el esquema del Diccionario de Datos
- **CUANDO** el Frontend envía la solicitud al endpoint `POST /authz/profiles`
- **ENTONCES** el Backend MUST procesar la solicitud dentro de `transaction.atomic()` y persistir el perfil con sus permisos en PostgreSQL
- **Y** el Backend MUST registrar la operación en `audit_log` con acción `CREATE`
- **Y** el perfil MUST quedar disponible para asignación
- **Y** el Frontend MUST mostrar una notificación de éxito usando tokens del theme

#### Scenario: Jefe crea un perfil con nombre duplicado
- **DADO** que ya existe un perfil activo con `name = "Supervisor"`
- **CUANDO** el Frontend intenta crear otro perfil con el mismo `name` en `POST /authz/profiles`
- **ENTONCES** el Backend MUST NOT crear el perfil
- **Y** el Backend MUST retornar HTTP `400 Bad Request` con `{campo: [mensajes]}` en el campo `name`
- **Y** el Frontend MUST mostrar el mensaje de error en el campo correspondiente del formulario

#### Scenario: Jefe crea un perfil con un permiso fuera del catálogo
- **DADO** que el payload incluye un `(módulo, acción)` que no existe en el catálogo conocido
- **CUANDO** el Frontend intenta enviar la solicitud al endpoint `POST /authz/profiles`
- **ENTONCES** el Backend MUST NOT procesar la solicitud
- **Y** el Backend MUST retornar HTTP `400 Bad Request` con el detalle del campo inválido (serializer DRF)

### Requirement: Asignación de perfil a usuario
Cada usuario MUST estar asociado a exactamente un perfil. La autorización del sistema MUST resolverse
por el perfil del usuario, no por su `role` nominal. Solo el `Jefe` MUST poder asignar perfiles. Al
asignar o cambiar el perfil de un usuario, el sistema MUST sincronizar su `role` nominal con el perfil
e **invalidar (blacklist) los refresh vigentes** del usuario, de modo que los permisos nuevos surtan
efecto sin esperar a la expiración del token.

#### Scenario: Cambiar el perfil sincroniza el rol e invalida la sesión
- **DADO** un usuario con un perfil asignado y un refresh válido
- **CUANDO** el `Jefe` envía la solicitud a `POST /authz/users/{id}/assign-profile` con un perfil distinto
- **ENTONCES** el Backend MUST procesarla dentro de `transaction.atomic()`, actualizar el perfil y sincronizar el `role` nominal
- **Y** el Backend MUST invalidar (blacklist) los refresh vigentes del usuario
- **Y** el Backend MUST registrar la operación en `audit_log` con acción `UPDATE`
- **Y** el usuario MUST renovar su sesión para operar con los permisos actualizados

### Requirement: Autorización por módulo y acción
El sistema MUST permitir o denegar cada acción sobre un módulo según el perfil del usuario. Cuando se
deniega, el sistema MUST responder `403 Forbidden` con `{detail}` en español, sin filtrar la
estructura interna de permisos.

#### Scenario: Usuario ejecuta una acción permitida por su perfil
- **DADO** un usuario cuyo perfil permite la acción sobre un módulo
- **CUANDO** ejecuta esa acción en el endpoint correspondiente
- **ENTONCES** el Backend MUST autorizar la operación y procesarla normalmente

#### Scenario: Usuario intenta una acción no permitida por su perfil
- **DADO** un usuario cuyo perfil no permite la acción sobre un módulo
- **CUANDO** intenta ejecutar esa acción en el endpoint correspondiente
- **ENTONCES** el Backend MUST retornar HTTP `403 Forbidden` con `{detail}` en español
- **Y** el mensaje MUST NOT revelar qué permiso específico faltó si eso expone estructura interna sensible

### Requirement: Campos invisibles por perfil
El sistema MUST omitir de la respuesta serializada los campos registrados como sensibles cuando el
perfil del usuario no tiene permiso de verlos. Un campo invisible MUST NOT aparecer en la respuesta
(no basta con marcarlo de solo lectura ni enmascararlo).

#### Scenario: Campo sensible omitido para un perfil sin acceso
- **DADO** un recurso con un campo registrado como sensible en el registro central
- **Y** un usuario cuyo perfil no puede ver ese campo
- **CUANDO** consulta el recurso
- **ENTONCES** la respuesta serializada MUST NOT incluir ese campo (ni su clave ni su valor)

#### Scenario: Campo sensible visible para un perfil con acceso
- **DADO** un recurso con un campo registrado como sensible en el registro central
- **Y** un usuario cuyo perfil puede ver ese campo
- **CUANDO** consulta el recurso
- **ENTONCES** la respuesta serializada MUST incluir ese campo con su valor

### Requirement: Capacidad de auto-aprobación
El perfil MUST exponer un flag de auto-aprobación consultable. La capacidad aquí es solo estructural;
su aplicación efectiva (llevar un ingreso de BORRADOR a VERIFICADO sin supervisor) se define en
`intake`.

#### Scenario: Perfil con auto-aprobación habilitada
- **DADO** un perfil con el flag de auto-aprobación habilitado
- **CUANDO** se consulta la capacidad del perfil
- **ENTONCES** el sistema MUST indicar que la auto-aprobación está habilitada

#### Scenario: Perfil con auto-aprobación deshabilitada
- **DADO** un perfil con el flag de auto-aprobación deshabilitado
- **CUANDO** se consulta la capacidad del perfil
- **ENTONCES** el sistema MUST indicar que la auto-aprobación NO está habilitada

### Requirement: Perfiles semilla del sistema
El sistema MUST proveer cuatro perfiles semilla correspondientes a los roles Jefe, Supervisor,
Responsable de ruta y Usuario, con permisos por defecto coherentes con cada rol. El seed MUST ser
idempotente y reversible.

#### Scenario: Perfiles semilla disponibles tras la inicialización
- **DADO** un sistema recién inicializado (migraciones aplicadas)
- **CUANDO** se ejecuta el seed de perfiles del sistema
- **ENTONCES** MUST existir los cuatro perfiles (Jefe, Supervisor, Responsable de ruta, Usuario)
- **Y** cada uno MUST quedar disponible para asignación

#### Scenario: El seed se aplica dos veces sin duplicar perfiles
- **DADO** que los cuatro perfiles semilla ya existen
- **CUANDO** se ejecuta el seed nuevamente
- **ENTONCES** el sistema MUST NOT crear perfiles duplicados
- **Y** el conjunto de perfiles semilla MUST permanecer en cuatro

### Requirement: Administración de perfiles
Un usuario autorizado (Jefe) MUST poder editar y dar de baja perfiles (soft delete clase 2) y configurar sus permisos por (módulo, acción) desde el catálogo conocido y sus flags de capacidad. Un perfil con usuarios asignados MUST NOT poder darse de baja sin reasignar antes a esos usuarios.

#### Scenario: Jefe edita los permisos de un perfil
- **DADO** un perfil existente y un administrador con perfil Jefe
- **CUANDO** el Frontend envía la solicitud a `PATCH /authz/profiles/{id}` con permisos por (módulo, acción) del catálogo
- **ENTONCES** el Backend MUST procesarla dentro de `transaction.atomic()` y persistir los permisos actualizados
- **Y** el Backend MUST registrar la operación en `audit_log` con acción `UPDATE`
- **Y** los usuarios con ese perfil MUST resolver su autorización con los permisos nuevos
- **Y** el Frontend MUST mostrar una notificación de éxito usando tokens del theme

#### Scenario: Jefe da de baja un perfil sin usuarios
- **DADO** un perfil sin usuarios asignados
- **CUANDO** el Frontend envía la solicitud a `DELETE /authz/profiles/{id}`
- **ENTONCES** el Backend MUST marcarlo como eliminado (soft delete clase 2, `deleted_at`) y registrar la operación en `audit_log` con acción `SOFT_DELETE`
- **Y** el perfil MUST dejar de ofrecerse para asignación

#### Scenario: Jefe intenta dar de baja un perfil en uso
- **DADO** un perfil con al menos un usuario asignado
- **CUANDO** el Frontend intenta `DELETE /authz/profiles/{id}`
- **ENTONCES** el Backend MUST NOT darlo de baja
- **Y** el Backend MUST retornar HTTP `409 Conflict` con `{detail}` indicando que hay usuarios asignados (baja bloqueada por dependencias)
- **Y** el Frontend MUST mostrar el mensaje indicando que primero debe reasignar a esos usuarios

#### Scenario: Usuario sin autorización intenta administrar perfiles
- **DADO** un usuario cuyo perfil no permite administrar perfiles
- **CUANDO** intenta acceder a `PATCH /authz/profiles/{id}` o `DELETE /authz/profiles/{id}`
- **ENTONCES** el Backend MUST retornar HTTP `403 Forbidden` con `{detail}` genérico
- **Y** el Backend MUST NOT modificar el perfil
