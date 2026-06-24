# user-management Specification

## Purpose

Administración del ciclo de vida de las cuentas de usuario por parte de un administrador (Jefe):
creación, edición, desactivación y reactivación de usuarios; reset administrativo de contraseña con
contraseña temporal y cambio forzado; e invalidación de sesiones activas (blacklist) cuando cambian
las credenciales o el estado. La autorización fina se resuelve por el perfil del usuario
(capability `access-control`); la autenticación y el cambio de contraseña propio viven en `auth`.

<!-- Keywords Gherkin en español (DADO/CUANDO/ENTONCES/Y); keywords normativos RFC 2119 en inglés. -->

## Requirements

### Requirement: Gestión de usuarios
Un usuario cuyo perfil lo autorice (Jefe) MUST poder crear, editar, desactivar y reactivar usuarios. La creación MUST asignar un perfil y dejar el `role` nominal sincronizado. Quien no esté autorizado MUST recibir 403. Los errores de validación MUST seguir el contrato uniforme `{campo: [mensajes]}`.

#### Scenario: Jefe crea un usuario con datos válidos
- DADO un usuario con perfil Jefe en la consola de administración
- Y que los datos (identificador único, perfil, datos básicos) cumplen el Diccionario de Datos
- CUANDO el Frontend envía la solicitud a `POST /auth/users`
- ENTONCES el Backend MUST procesarla dentro de `transaction.atomic()` y persistir el usuario con su perfil y su `role` sincronizado
- Y el Backend MUST registrar la operación en `audit_log` con acción `CREATE`
- Y el usuario MUST quedar disponible para autenticarse
- Y el Frontend MUST mostrar una notificación de éxito usando tokens del theme

#### Scenario: Usuario sin autorización intenta crear un usuario
- DADO un usuario cuyo perfil no permite administrar usuarios
- CUANDO intenta acceder a `POST /auth/users`
- ENTONCES el Backend MUST retornar HTTP `403 Forbidden` con `{detail}` genérico en español
- Y el Backend MUST NOT crear el usuario
- Y el Frontend MUST mostrar el mensaje de acceso denegado sin exponer detalles internos

#### Scenario: Jefe crea un usuario con identificador duplicado
- DADO que ya existe un usuario activo con ese identificador
- CUANDO el Frontend intenta crear otro con el mismo identificador en `POST /auth/users`
- ENTONCES el Backend MUST NOT crear el usuario
- Y el Backend MUST retornar HTTP `400 Bad Request` con `{campo: [mensajes]}` en el campo del identificador
- Y el Frontend MUST mostrar el error en el campo correspondiente del formulario

> **Nota de alcance:** el *cambio de perfil de un usuario* no se especifica en esta capability. Vive
> en `access-control` como la requirement *"Asignación de perfil a usuario"*, extendida con
> sincronización de `role` + blacklist. Se evita duplicar la misma regla en dos capabilities (DRY/KISS).

### Requirement: Reset administrativo de contraseña
El administrador (Jefe) MUST poder restablecer la contraseña de un usuario sin conocer la anterior. El reset MUST fijar una contraseña temporal (definida por el administrador o generada por el sistema), activar el flag `must_change_password` e invalidar (blacklist) los refresh vigentes del usuario.

#### Scenario: Jefe resetea la contraseña de un usuario
- DADO un usuario existente y un administrador con perfil Jefe
- CUANDO el Frontend envía la solicitud a `POST /auth/users/{id}/reset-password`
- ENTONCES el Backend MUST procesarla dentro de `transaction.atomic()`, fijar la contraseña temporal y activar `must_change_password`
- Y el Backend MUST invalidar (blacklist) los refresh vigentes del usuario
- Y el Backend MUST registrar la operación en `audit_log` con acción `UPDATE`
- Y el Backend MUST NOT loggear la contraseña temporal en claro
- Y el Frontend MUST mostrar la contraseña temporal una sola vez usando tokens del theme

#### Scenario: Reset con contraseña temporal que no cumple la política
- DADO que el administrador define una contraseña temporal que no cumple las reglas de complejidad
- CUANDO el Frontend envía la solicitud a `POST /auth/users/{id}/reset-password`
- ENTONCES el Backend MUST NOT cambiar la contraseña
- Y el Backend MUST retornar HTTP `400 Bad Request` con `{campo: [mensajes]}` en el campo de la contraseña
- Y el Frontend MUST mostrar el error en el campo correspondiente

#### Scenario: Usuario sin autorización intenta resetear una contraseña
- DADO un usuario cuyo perfil no permite administrar identidad
- CUANDO intenta acceder a `POST /auth/users/{id}/reset-password`
- ENTONCES el Backend MUST retornar HTTP `403 Forbidden` con `{detail}` genérico
- Y el Backend MUST NOT modificar la contraseña del usuario

### Requirement: Desactivación y reactivación
El administrador (Jefe) MUST poder desactivar y reactivar usuarios. La desactivación MUST invalidar (blacklist) todos los refresh del usuario; un usuario desactivado MUST NOT poder autenticarse ni renovar sesión.

#### Scenario: Jefe desactiva un usuario e invalida su sesión
- DADO un usuario activo con un refresh válido
- CUANDO el Frontend envía la solicitud a `POST /auth/users/{id}/deactivate`
- ENTONCES el Backend MUST procesarla dentro de `transaction.atomic()`, marcar `is_active=False` e invalidar sus refresh
- Y el Backend MUST registrar la operación en `audit_log` con acción `UPDATE`
- Y el usuario MUST NOT poder renovar ni iniciar sesión
- Y el Frontend MUST mostrar una notificación de éxito usando tokens del theme

#### Scenario: Jefe reactiva un usuario desactivado
- DADO un usuario desactivado
- CUANDO el Frontend envía la solicitud a `POST /auth/users/{id}/reactivate`
- ENTONCES el Backend MUST marcar `is_active=True` y registrar la operación en `audit_log`
- Y el usuario MUST poder volver a autenticarse

#### Scenario: Usuario sin autorización intenta desactivar a otro
- DADO un usuario cuyo perfil no permite administrar identidad
- CUANDO intenta acceder a `POST /auth/users/{id}/deactivate`
- ENTONCES el Backend MUST retornar HTTP `403 Forbidden` con `{detail}` genérico
- Y el Backend MUST NOT modificar el estado del usuario

### Requirement: Auditoría de eventos de seguridad
El sistema MUST registrar en el `audit_log` (vía el decorador `@audit`) los eventos de reset de contraseña, desactivación, reactivación y cambio de perfil, con el usuario que ejecuta la acción, el usuario afectado, el tipo de evento, la fecha/hora y —cuando aplique— el valor anterior y el nuevo del campo modificado. El registro de auditoría MUST ser atómico con la operación: si el registro falla, la operación completa MUST revertirse.

#### Scenario: El reset queda auditado
- DADO un administrador que resetea la contraseña de un usuario
- CUANDO el reset se ejecuta con éxito
- ENTONCES el Backend MUST registrar en `audit_log` el ejecutor, el afectado, el tipo de evento y la fecha/hora

#### Scenario: Fallo al auditar revierte la operación de seguridad
- DADO un administrador que ejecuta una desactivación
- CUANDO el registro en `audit_log` falla dentro de la transacción
- ENTONCES el Backend MUST revertir la desactivación (rollback total) y MUST NOT dejar el usuario en estado inconsistente
- Y el Backend MUST retornar un error del contrato uniforme
