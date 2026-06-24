# auth Specification

## Purpose

Define la autenticación de usuarios del sistema: inicio y cierre de sesión, renovación y rotación de tokens, identidad del usuario autenticado, cambio de contraseña propio, la estructura de roles y la limitación de intentos de login. La autorización fina por rol se define en la capability `access-control` (F2).

<!-- Keywords Gherkin en español (DADO/CUANDO/ENTONCES/Y); keywords normativos RFC 2119 en inglés. -->

## Requirements

### Requirement: Autenticación por credenciales
El sistema MUST autenticar a un usuario con credenciales válidas y emitir un access token (vida 15 min) en el cuerpo de la respuesta y un refresh token (vida 7 días) en una cookie `httpOnly`. El sistema MUST NOT emitir tokens para credenciales inválidas ni para usuarios inactivos. Los errores MUST seguir el contrato de errores uniforme.

#### Scenario: Usuario activo inicia sesión con credenciales válidas
- **DADO** un usuario con `is_active = true` y credenciales correctas
- **CUANDO** el Frontend envía la solicitud al endpoint `POST /auth/login`
- **ENTONCES** el Backend MUST responder `200 OK` con el access token en el cuerpo
- **Y** MUST establecer el refresh token en una cookie `httpOnly`, `Secure`, con `SameSite` configurado
- **Y** la respuesta MUST incluir el identificador, el nombre y el rol del usuario

#### Scenario: Usuario intenta iniciar sesión con credenciales inválidas
- **DADO** un identificador con contraseña incorrecta
- **CUANDO** el Frontend envía la solicitud al endpoint `POST /auth/login`
- **ENTONCES** el Backend MUST responder `401 Unauthorized` con `{detail}` en español
- **Y** MUST NOT establecer ninguna cookie

#### Scenario: Usuario inactivo intenta iniciar sesión
- **DADO** un usuario con `is_active = false`
- **CUANDO** el Frontend envía credenciales correctas al endpoint `POST /auth/login`
- **ENTONCES** el Backend MUST responder `401 Unauthorized` con `{detail}`
- **Y** MUST NOT emitir tokens

### Requirement: Renovación de access token
El sistema MUST emitir un nuevo access token a partir de un refresh token válido presente en la cookie `httpOnly`, y MUST rotar el refresh token (emitir uno nuevo e invalidar el anterior por blacklist). El sistema MUST rechazar refresh tokens expirados, ausentes o revocados.

#### Scenario: Usuario renueva el access con un refresh válido
- **DADO** un refresh token válido en la cookie `httpOnly`
- **CUANDO** el Frontend solicita renovación en `POST /auth/refresh`
- **ENTONCES** el Backend MUST responder `200 OK` con un nuevo access token en el cuerpo
- **Y** MUST rotar el refresh token estableciendo una nueva cookie `httpOnly`
- **Y** MUST agregar el refresh anterior a la blacklist

#### Scenario: Usuario renueva con un refresh token revocado
- **DADO** un refresh token previamente invalidado por logout o por cambio de contraseña
- **CUANDO** el Frontend solicita renovación en `POST /auth/refresh`
- **ENTONCES** el Backend MUST responder `401 Unauthorized` con `{detail}`

#### Scenario: Usuario renueva sin cookie de refresh
- **DADO** una solicitud de renovación sin cookie de refresh
- **CUANDO** llega al endpoint `POST /auth/refresh`
- **ENTONCES** el Backend MUST responder `401 Unauthorized` con `{detail}`

### Requirement: Cierre de sesión
El sistema MUST invalidar el refresh token (blacklist) y limpiar la cookie `httpOnly` al cerrar sesión, de modo que el refresh no pueda reutilizarse.

#### Scenario: Usuario cierra una sesión activa
- **DADO** un usuario autenticado con un refresh válido
- **CUANDO** el Frontend solicita cierre de sesión en `POST /auth/logout`
- **ENTONCES** el Backend MUST agregar el refresh a la blacklist
- **Y** MUST limpiar la cookie de refresh
- **Y** MUST responder `200 OK`

#### Scenario: Usuario intenta renovar tras cerrar sesión
- **DADO** un usuario que cerró sesión
- **CUANDO** el Frontend intenta renovar con el refresh anterior en `POST /auth/refresh`
- **ENTONCES** el Backend MUST responder `401 Unauthorized`

### Requirement: Identidad del usuario autenticado
El sistema MUST exponer un endpoint que devuelva la identidad del usuario autenticado (identificador, nombre, rol, estado) a partir de un access token válido, y MUST rechazar solicitudes sin access token válido.

#### Scenario: Usuario consulta su identidad con access válido
- **DADO** un access token válido en la cabecera `Authorization: Bearer`
- **CUANDO** el Frontend consulta el endpoint `GET /auth/me`
- **ENTONCES** el Backend MUST responder `200 OK` con identificador, nombre y rol

#### Scenario: Usuario consulta su identidad sin autenticación
- **DADO** una solicitud sin access token
- **CUANDO** el Frontend consulta el endpoint `GET /auth/me`
- **ENTONCES** el Backend MUST responder `401 Unauthorized` con `{detail}`

### Requirement: Cambio de contraseña propio
El sistema MUST permitir que un usuario autenticado cambie su propia contraseña proporcionando la contraseña actual y una nueva que cumpla la política de contraseñas. MUST rechazar si la contraseña actual es incorrecta o la nueva no cumple la política. Tras un cambio exitoso, el sistema MUST invalidar los refresh tokens vigentes del usuario.

#### Scenario: Usuario cambia su contraseña con la actual correcta
- **DADO** un usuario autenticado
- **CUANDO** envía su contraseña actual correcta y una nueva válida a `POST /auth/change-password`
- **ENTONCES** el Backend MUST actualizar la contraseña
- **Y** MUST invalidar los refresh tokens previos del usuario
- **Y** MUST responder `200 OK`

#### Scenario: Usuario cambia su contraseña con la actual incorrecta
- **DADO** un usuario autenticado
- **CUANDO** envía una contraseña actual incorrecta a `POST /auth/change-password`
- **ENTONCES** el Backend MUST responder `400 Bad Request` con `{campo: [mensajes]}` señalando el campo de la contraseña actual
- **Y** el Frontend MUST mostrar el mensaje en el campo correspondiente sin exponer detalles internos

#### Scenario: Usuario envía una nueva contraseña que no cumple la política
- **DADO** un usuario autenticado
- **CUANDO** envía una nueva contraseña que no cumple los validadores de Django a `POST /auth/change-password`
- **ENTONCES** el Backend MUST responder `400 Bad Request` con `{campo: [mensajes]}` señalando el campo de la nueva contraseña

### Requirement: Roles del sistema
El modelo de usuario MUST incluir un rol entre cuatro valores: Jefe, Supervisor, Responsable de ruta, Usuario. El rol MUST formar parte de la identidad expuesta del usuario. La autorización fina por rol se define en la capability `access-control` (F2); aquí el rol es solo estructura.

#### Scenario: Usuario con rol asignado expone su rol en la identidad
- **DADO** un usuario con rol Supervisor
- **CUANDO** consulta su identidad en `GET /auth/me`
- **ENTONCES** la respuesta MUST incluir el rol Supervisor

### Requirement: Limitación de intentos de login
El sistema MUST limitar la tasa de intentos de login para mitigar ataques de fuerza bruta, y MUST responder con un error claro siguiendo el contrato uniforme cuando se supere el umbral.

#### Scenario: Usuario supera el umbral de intentos de login
- **DADO** múltiples intentos de login fallidos desde el mismo origen por encima del umbral configurado
- **CUANDO** se realiza otro intento en `POST /auth/login`
- **ENTONCES** el Backend MUST responder con un error de límite excedido en formato `{detail}`
