# Delta para directory

<!-- Keywords Gherkin en español (DADO/CUANDO/ENTONCES/Y); keywords RFC 2119 en inglés. -->
<!-- Este delta AÑADE la asignación de lista de precios a la ficha; completa el FK diferido en F4. -->

## ADDED Requirements

### Requirement: Asignación de lista de precios a un cliente

El sistema MUST permitir que una ficha con rol **cliente** tenga a lo sumo una lista de precios asignada
(FK simple `price_list` a `pricing.PriceList`, `on_delete=PROTECT`), y MUST NOT permitir asignar una
lista a una ficha sin rol cliente. La integridad asignación↔rol MUST validarse en el service
(`apps/directory/services.py`), retornando el contrato uniforme. La asignación la realiza un perfil
autorizado (el módulo `directory` en `update`, resuelto por perfil, nunca por el `role` nominal).

#### Scenario: Supervisor asigna una lista a un cliente

- **DADO** un usuario cuyo perfil permite `directory.update`
- **Y** una ficha con rol cliente y una lista de precios existente
- **CUANDO** le asigna la lista
- **ENTONCES** el Backend MUST persistir `price_list` en la ficha dentro de `transaction.atomic()`
- **Y** MUST registrar la operación en `audit_log` con acción `UPDATE`
- **Y** el Frontend MUST mostrar una notificación de éxito usando tokens del theme

#### Scenario: Supervisor asigna una lista a una ficha sin rol cliente

- **DADO** una ficha que NO tiene rol cliente
- **CUANDO** intenta asignarle una lista de precios
- **ENTONCES** el Backend MUST retornar HTTP `400 Bad Request` con `{campo: [mensajes]}` indicando que
  la ficha no es cliente
- **Y** el Frontend MUST mapear el mensaje al campo de la lista en el formulario

#### Scenario: Usuario sin autorización asigna una lista

- **DADO** un usuario sin el módulo `directory` en `update`, o sin sesión activa (token SimpleJWT)
- **CUANDO** intenta asignar una lista a una ficha
- **ENTONCES** el Backend MUST retornar HTTP `401 Unauthorized` (sin sesión) o `403 Forbidden`
  (`{detail}` genérico) según corresponda
- **Y** el Frontend MUST redirigir al login (401) u ocultar/deshabilitar el selector (403)
