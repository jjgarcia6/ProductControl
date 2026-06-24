# Delta para la capability `auth`

## ADDED Requirements

### Requirement: Cambio de contraseña forzado en el primer acceso
Cuando un usuario tiene activo el flag `must_change_password`, el sistema MUST exigir el cambio de contraseña antes de permitir cualquier otra operación. Mientras el flag esté activo, solo el cambio de contraseña propio, `GET /auth/me` y el cierre de sesión MUST estar disponibles; cualquier otra operación MUST rechazarse con HTTP `403 Forbidden` y `{detail}` indicando la obligación de cambio. Tras un cambio exitoso, el flag MUST desactivarse.

#### Scenario: Login con cambio forzado pendiente
- DADO un usuario con el flag `must_change_password` activo
- CUANDO inicia sesión con su contraseña temporal en `POST /auth/login`
- ENTONCES el Backend MUST autenticarlo y emitir tokens
- Y la respuesta de `GET /auth/me` MUST indicar que debe cambiar su contraseña
- Y el Frontend MUST redirigir a la pantalla de cambio de contraseña

#### Scenario: Operación bloqueada mientras el cambio está pendiente
- DADO un usuario autenticado con el flag activo
- CUANDO intenta una operación distinta de cambiar su contraseña, `GET /auth/me` o logout
- ENTONCES el Backend MUST retornar HTTP `403 Forbidden` con `{detail}` que exige el cambio de contraseña
- Y el Backend MUST NOT ejecutar la operación solicitada
- Y el Frontend MUST mantener al usuario en la pantalla de cambio de contraseña

#### Scenario: El cambio de contraseña desactiva el flag
- DADO un usuario con el flag activo
- CUANDO cambia su contraseña con éxito en `POST /auth/change-password`
- ENTONCES el Backend MUST desactivar `must_change_password` dentro de `transaction.atomic()`
- Y el usuario MUST poder operar normalmente según su perfil
