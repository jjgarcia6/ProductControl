# Delta para pricing

<!-- Keywords Gherkin en español (DADO/CUANDO/ENTONCES/Y); keywords RFC 2119 en inglés. -->
<!-- Identificadores técnicos en inglés; valores de dominio (NORMAL/DESCARTE) en español MAYÚSCULAS. -->

## ADDED Requirements

### Requirement: Lista de precios

La lista MUST registrar un `name` único entre listas vivas y un `type` (`NORMAL` o `DESCARTE`). Usa
soft delete clase 2 (`deleted_at` + manager filtrado, unicidad de nombre por índice parcial). La
unicidad de nombre MUST gobernarse en el service (`Conflict` 409), no por `UniqueValidator`. En F6 el
`type` es solo un atributo (su efecto en la venta de descarte se implementa en F16). Los errores MUST
seguir el contrato uniforme.

#### Scenario: Supervisor crea una lista normal y una de descarte

- **DADO** un usuario cuyo perfil permite `PRICING.create`
- **Y** un `name` único para cada lista
- **CUANDO** crea una lista de tipo `NORMAL` y otra de tipo `DESCARTE`
- **ENTONCES** el Backend MUST persistirlas dentro de `transaction.atomic()` con su `type`
- **Y** MUST registrar la operación en `audit_log` con acción `CREATE`
- **Y** el Frontend MUST mostrar una notificación de éxito usando tokens del theme

#### Scenario: Supervisor crea una lista con nombre duplicado

- **DADO** que ya existe una lista viva con `name = "Mayorista"`
- **CUANDO** intenta crear otra lista con el mismo `name`
- **ENTONCES** el Backend MUST retornar HTTP `409 Conflict` con `{detail}` del contrato uniforme
- **Y** el Frontend MUST mostrar el mensaje indicando el duplicado

#### Scenario: Usuario sin autorización gestiona listas

- **DADO** un usuario sin el módulo `PRICING` en su perfil, o sin sesión activa (token SimpleJWT)
- **CUANDO** intenta crear o editar una lista
- **ENTONCES** el Backend MUST retornar HTTP `401 Unauthorized` (sin sesión) o `403 Forbidden`
  (`{detail}` genérico) según corresponda
- **Y** el Frontend MUST redirigir al login (401) u ocultar/deshabilitar la acción (403)

### Requirement: Precio de producto en lista

Cada par (lista, producto) MUST tener a lo sumo un precio (`UniqueConstraint(price_list, product)`). El
`price` MUST ser un `DecimalField(max_digits=12, decimal_places=2)` no negativo, en USD. La unicidad
(lista, producto) MUST gobernarse en el service (`Conflict` 409), no por `UniqueTogetherValidator`. El
FK a `products.Product` MUST usar `on_delete=PROTECT`.

#### Scenario: Supervisor agrega un producto con su precio

- **DADO** un usuario cuyo perfil permite `PRICING.update`
- **Y** una lista y un producto existentes, sin precio previo para ese par
- **CUANDO** agrega el producto a la lista con un `price` válido (≥ 0)
- **ENTONCES** el Backend MUST persistir el precio para ese par dentro de `transaction.atomic()`
- **Y** MUST registrar la operación en `audit_log` con acción `CREATE`
- **Y** el Frontend MUST mostrar una notificación de éxito usando tokens del theme

#### Scenario: Supervisor agrega un producto ya presente en la lista

- **DADO** que el producto ya tiene un precio en esa lista
- **CUANDO** intenta agregarlo de nuevo a la misma lista
- **ENTONCES** el Backend MUST retornar HTTP `409 Conflict` con `{detail}` del contrato uniforme
- **Y** el Frontend MUST mostrar el mensaje indicando el duplicado

#### Scenario: Supervisor fija un precio negativo

- **DADO** que el payload trae `price < 0`
- **CUANDO** el Frontend intenta enviar la solicitud al endpoint de ítems de precio
- **ENTONCES** el Backend MUST retornar HTTP `400 Bad Request` con `{campo: [mensajes]}` en `price`
- **Y** el Frontend MUST mapear el mensaje al campo del precio en el formulario

### Requirement: Baja de lista en uso

Una lista asignada a una o más fichas MUST NOT poder darse de baja (soft delete) sin reasignar antes a
esas fichas. La regla MUST gobernarse en el service (`Conflict` 409); el `on_delete=PROTECT` del FK en
la ficha es la segunda defensa a nivel de base de datos.

#### Scenario: Supervisor da de baja una lista sin clientes

- **DADO** un usuario cuyo perfil permite `PRICING.update`
- **Y** una lista sin fichas asignadas
- **CUANDO** la da de baja
- **ENTONCES** el Backend MUST marcarla con `deleted_at` (soft delete clase 2) y dejar de listarla
- **Y** MUST registrar la operación en `audit_log` con acción `SOFT_DELETE`
- **Y** el Frontend MUST mostrar una notificación de éxito usando tokens del theme

#### Scenario: Supervisor da de baja una lista asignada a un cliente

- **DADO** una lista asignada a al menos una ficha
- **CUANDO** intenta darla de baja
- **ENTONCES** el Backend MUST retornar HTTP `409 Conflict` con `{detail}` indicando que está en uso
- **Y** el mensaje MUST indicar que hay fichas que dependen de la lista
- **Y** el Frontend MUST mostrar el mensaje al usuario
