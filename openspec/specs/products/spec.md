# products

<!-- Keywords Gherkin en español (DADO/CUANDO/ENTONCES/Y); keywords RFC 2119 en inglés. -->
<!-- Identificadores técnicos en inglés; valores de dominio (GAVETA/PESO) en español MAYÚSCULAS. -->

## Purpose

Maestro de catálogo de productos e inventario (F5): categorías, productos y unidades de medida, con
baja lógica clase 2 y autorización por perfil (módulo `products`). Los pesos se expresan en libras
como base; los factores de conversión se almacenan para uso futuro.

## Requirements

### Requirement: Categoría de producto

La categoría MUST registrar un nombre único entre categorías vivas, los días de caducidad desde el
ingreso (default 7), el tipo de ingreso (`GAVETA` o `PESO`) y la estructura del rango de merma
proporcional: `merma_min`, `merma_max` y `reference_qty` (default 100). Los valores `merma_min`/
`merma_max` MAY quedar sin definir hasta que el cliente los provea. Los pesos MUST expresarse como
decimales en libras. La unicidad de nombre MUST gobernarse en el service (`Conflict` 409), no por
`UniqueValidator`. Los errores MUST seguir el contrato uniforme.

#### Scenario: Crear una categoría

- **DADO** un usuario cuyo perfil permite `products.create`
- **Y** un nombre único, días de caducidad y un tipo de ingreso válido (`GAVETA`/`PESO`)
- **CUANDO** se crea la categoría
- **ENTONCES** el Backend MUST persistirla dentro de `transaction.atomic()` con la estructura del rango de merma disponible para configurarse
- **Y** MUST registrar la operación en `audit_log` con acción `CREATE`
- **Y** el Frontend MUST mostrar una notificación de éxito usando tokens del theme

#### Scenario: Categoría sin valores de merma definidos

- **DADO** una categoría cuyos valores de rango de merma (`merma_min`/`merma_max`) aún no se conocen
- **CUANDO** se crea la categoría sin esos valores
- **ENTONCES** el Backend MUST persistirla con el rango de merma sin definir (nullable) y `reference_qty` por defecto

#### Scenario: Tipo de ingreso inválido

- **DADO** un payload con un tipo de ingreso distinto de `GAVETA` o `PESO`
- **CUANDO** el Frontend intenta crear la categoría
- **ENTONCES** el Backend MUST retornar HTTP `400` con `{intake_type: [mensajes]}` (validación de serializer)
- **Y** el Frontend MUST mostrar el error mapeado al campo del tipo de ingreso

#### Scenario: Nombre de categoría duplicado

- **DADO** una categoría viva con un nombre
- **CUANDO** se intenta crear otra categoría con el mismo nombre
- **ENTONCES** el Backend MUST retornar HTTP `409` con `{detail}` indicando que ya existe una categoría con ese nombre (la unicidad la gobierna el service)
- **Y** el Frontend MUST mostrar el mensaje como aviso

#### Scenario: Crear categoría sin autorización del perfil

- **DADO** un usuario cuyo perfil NO permite `products.create`
- **CUANDO** intenta crear una categoría en `POST /products/categories`
- **ENTONCES** el Backend MUST retornar HTTP `403` con `{detail}` genérico
- **Y** el Backend MUST NOT persistir la categoría

### Requirement: Producto

El producto MUST registrar un nombre único entre productos vivos, una categoría existente y una unidad
de medida existente. La unicidad de nombre MUST gobernarse en el service (`Conflict` 409).

#### Scenario: Crear un producto

- **DADO** un usuario con perfil que permite `products.create`
- **Y** una categoría y una unidad de medida existentes
- **CUANDO** se crea el producto con un nombre único
- **ENTONCES** el Backend MUST persistirlo asociado a su categoría y unidad
- **Y** MUST registrar la operación en `audit_log` con acción `CREATE`

#### Scenario: Producto con categoría inexistente

- **DADO** un payload cuya categoría referenciada no existe
- **CUANDO** el Frontend intenta crear el producto
- **ENTONCES** el Backend MUST retornar HTTP `400` con `{category: [mensajes]}` (validación de FK en el serializer)

#### Scenario: Nombre de producto duplicado

- **DADO** un producto vivo con un nombre
- **CUANDO** se intenta crear otro producto con el mismo nombre
- **ENTONCES** el Backend MUST retornar HTTP `409` con `{detail}` indicando el duplicado

### Requirement: Unidad de medida

La unidad de medida MUST registrar nombre único entre vivas, símbolo y un factor de conversión a la
unidad base (libras = 1). Tras la inicialización MUST existir la unidad base (libras, factor 1) y
kilogramos. Los factores de conversión se almacenan para uso futuro y MUST NOT aplicarse en esta fase.

#### Scenario: Unidades base disponibles tras la inicialización

- **DADO** un sistema recién inicializado
- **CUANDO** se ejecuta la data migration que siembra las unidades de medida
- **ENTONCES** MUST existir libras (factor 1) y kilogramos con su factor de conversión
- **Y** la siembra MUST ser idempotente (re-ejecutarla no duplica filas)

### Requirement: Baja lógica de catálogos

Categorías, productos y unidades MUST usar soft delete clase 2 (baja con `deleted_at`, exclusión de los
listados por defecto vía manager, unicidad parcial entre vivos). Una categoría o unidad con productos
vivos asociados MUST NOT poder darse de baja: el service MUST rechazar con `Conflict` (409).

#### Scenario: Baja de una categoría sin productos

- **DADO** un usuario con perfil que permite `products.update`
- **Y** una categoría sin productos vivos asociados
- **CUANDO** se da de baja
- **ENTONCES** el Backend MUST marcarla como eliminada (`deleted_at`) y dejar de listarla por defecto
- **Y** MUST registrar la operación en `audit_log` con acción `SOFT_DELETE`

#### Scenario: Baja de una categoría con productos

- **DADO** una categoría con al menos un producto vivo asociado
- **CUANDO** se intenta darla de baja
- **ENTONCES** el Backend MUST retornar HTTP `409` con `{detail}` indicando que tiene productos asociados
- **Y** el Frontend MUST mostrar el mensaje de la dependencia que la bloquea

#### Scenario: Reutilización del nombre de un registro dado de baja

- **DADO** una categoría dada de baja (`deleted_at` no nulo) con nombre `N`
- **CUANDO** se crea una nueva categoría con el mismo nombre `N`
- **ENTONCES** el Backend MUST persistirla (la unicidad parcial solo aplica entre vivas)
