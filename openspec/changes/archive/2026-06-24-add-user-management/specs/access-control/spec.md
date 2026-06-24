# Delta para la capability `access-control`

## ADDED Requirements

### Requirement: Administración de perfiles
Un usuario autorizado (Jefe) MUST poder editar y dar de baja perfiles (soft delete clase 2) y configurar sus permisos por (módulo, acción) desde el catálogo conocido y sus flags de capacidad. Un perfil con usuarios asignados MUST NOT poder darse de baja sin reasignar antes a esos usuarios.

#### Scenario: Jefe edita los permisos de un perfil
- DADO un perfil existente y un administrador con perfil Jefe
- CUANDO el Frontend envía la solicitud a `PATCH /authz/profiles/{id}` con permisos por (módulo, acción) del catálogo
- ENTONCES el Backend MUST procesarla dentro de `transaction.atomic()` y persistir los permisos actualizados
- Y el Backend MUST registrar la operación en `audit_log` con acción `UPDATE`
- Y los usuarios con ese perfil MUST resolver su autorización con los permisos nuevos
- Y el Frontend MUST mostrar una notificación de éxito usando tokens del theme

#### Scenario: Jefe da de baja un perfil sin usuarios
- DADO un perfil sin usuarios asignados
- CUANDO el Frontend envía la solicitud a `DELETE /authz/profiles/{id}`
- ENTONCES el Backend MUST marcarlo como eliminado (soft delete clase 2, `deleted_at`) y registrar la operación en `audit_log` con acción `SOFT_DELETE`
- Y el perfil MUST dejar de ofrecerse para asignación

#### Scenario: Jefe intenta dar de baja un perfil en uso
- DADO un perfil con al menos un usuario asignado
- CUANDO el Frontend intenta `DELETE /authz/profiles/{id}`
- ENTONCES el Backend MUST NOT darlo de baja
- Y el Backend MUST retornar HTTP `409 Conflict` con `{detail}` indicando que hay usuarios asignados (baja bloqueada por dependencias)
- Y el Frontend MUST mostrar el mensaje indicando que primero debe reasignar a esos usuarios

#### Scenario: Usuario sin autorización intenta administrar perfiles
- DADO un usuario cuyo perfil no permite administrar perfiles
- CUANDO intenta acceder a `PATCH /authz/profiles/{id}` o `DELETE /authz/profiles/{id}`
- ENTONCES el Backend MUST retornar HTTP `403 Forbidden` con `{detail}` genérico
- Y el Backend MUST NOT modificar el perfil

## MODIFIED Requirements

### Requirement: Asignación de perfil a usuario
Cada usuario MUST estar asociado a exactamente un perfil. La autorización del sistema MUST resolverse por el perfil del usuario, no por su `role` nominal. Solo el `Jefe` MUST poder asignar perfiles. Al asignar o cambiar el perfil de un usuario, el sistema MUST sincronizar su `role` nominal con el perfil e **invalidar (blacklist) los refresh vigentes** del usuario, de modo que los permisos nuevos surtan efecto sin esperar a la expiración del token.
*(Anteriormente: la asignación cambiaba el perfil y registraba `audit_log`, pero NO sincronizaba el `role` ni invalidaba las sesiones activas — el usuario conservaba sus permisos previos hasta que expirara el refresh.)*

#### Scenario: Cambiar el perfil sincroniza el rol e invalida la sesión
- DADO un usuario con un perfil asignado y un refresh válido
- CUANDO el `Jefe` envía la solicitud a `POST /authz/users/{id}/assign-profile` con un perfil distinto
- ENTONCES el Backend MUST procesarla dentro de `transaction.atomic()`, actualizar el perfil y sincronizar el `role` nominal
- Y el Backend MUST invalidar (blacklist) los refresh vigentes del usuario
- Y el Backend MUST registrar la operación en `audit_log` con acción `UPDATE`
- Y el usuario MUST renovar su sesión para operar con los permisos actualizados
