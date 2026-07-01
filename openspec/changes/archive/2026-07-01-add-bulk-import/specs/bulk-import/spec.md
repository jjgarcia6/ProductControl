# Delta para bulk-import

<!-- Keywords Gherkin en español (DADO/CUANDO/ENTONCES/Y); keywords RFC 2119 en inglés. -->
<!-- Identificadores técnicos en inglés; estados de fila (valid/skipped/error) en inglés por ser claves de contrato. -->

## ADDED Requirements

### Requirement: Previsualización sin persistir (dry-run)
El sistema MUST permitir cargar un archivo CSV o Excel y validarlo fila por fila SIN persistir, devolviendo
HTTP `200 OK` con un reporte por fila: su número, su estado (válida, a omitir por duplicado, o con error) y,
si tiene error, el campo y el mensaje según el contrato uniforme.

#### Scenario: Supervisor previsualiza un archivo válido
- DADO un usuario con el módulo `bulk-import` y un archivo con filas válidas
- CUANDO ejecuta el dry-run en `POST /bulk-import/products?dry_run=true`
- ENTONCES el Backend MUST responder `200 OK` con el reporte marcando las filas como válidas
- Y no persiste ningún registro

#### Scenario: Supervisor previsualiza un archivo con filas inválidas
- DADO un archivo con algunas filas inválidas
- CUANDO ejecuta el dry-run
- ENTONCES el Backend MUST responder `200 OK` con el reporte que señala cada fila inválida con su número, campo y mensaje
- Y no persiste ningún registro
- Y el Frontend MUST mostrar la tabla de reporte con los errores por campo usando tokens del theme

### Requirement: Commit atómico all-or-nothing
El commit MUST persistir el lote en una única transacción y solo si ninguna fila tiene error de validación.
Si al menos una fila tiene error, el sistema MUST NOT persistir ninguna fila y MUST responder `400 Bad Request`
con el reporte de errores por fila.

#### Scenario: Supervisor confirma un lote sin errores
- DADO un archivo cuyas filas son todas válidas o a omitir
- CUANDO confirma la importación en `POST /bulk-import/products` (sin `dry_run`)
- ENTONCES el Backend MUST procesar dentro de `transaction.atomic()` y persistir las filas nuevas
- Y MUST registrar la operación en `audit_log` con acción `CREATE` (entidad y conteos)
- Y MUST responder `201 Created` con el conteo de insertadas y omitidas
- Y el Frontend MUST mostrar una notificación de éxito con los conteos

#### Scenario: Supervisor confirma un lote con una fila inválida
- DADO un archivo con al menos una fila con error de validación
- CUANDO intenta confirmar la importación
- ENTONCES el Backend MUST NOT persistir ninguna fila
- Y MUST responder `400 Bad Request` con el reporte de errores por fila
- Y el Frontend MUST mostrar los errores sin exponer detalles internos

### Requirement: Deduplicación idempotente
El importador MUST omitir las filas cuya clave natural ya existe (producto por nombre; ficha por número de
identificación), sin duplicarlas ni sobrescribirlas. Re-ejecutar el mismo archivo MUST NOT alterar los
registros existentes. Una omisión por duplicado NO es un error y no impide el commit.

#### Scenario: Supervisor re-ejecuta el mismo archivo
- DADO un archivo ya importado con éxito
- CUANDO importa el mismo archivo de nuevo
- ENTONCES el Backend MUST responder `201 Created` con todas las filas marcadas como omitidas
- Y no altera ningún registro existente

#### Scenario: Supervisor confirma un lote con filas nuevas y duplicadas
- DADO un archivo con filas nuevas y filas cuya clave ya existe
- CUANDO confirma la importación
- ENTONCES el Backend MUST insertar las nuevas y omitir las existentes
- Y MUST responder `201 Created` reportando ambos conteos

### Requirement: Validación delegada a las reglas de dominio
Cada fila MUST validarse con las mismas reglas de su entidad (identificación ecuatoriana, roles ≥1, unicidad,
referencias existentes), sin reimplementarlas en el importador. El mensaje de error de fila MUST ser el mismo
que produce el alta individual, siguiendo el contrato de errores uniforme.

#### Scenario: Fila de ficha con identificación inválida
- DADO una fila de ficha con una cédula que no pasa el dígito verificador
- CUANDO se valida (dry-run o commit)
- ENTONCES la fila se marca con error y el mismo mensaje que produce el alta individual de F4

#### Scenario: Producto con categoría inexistente
- DADO una fila de producto que referencia una categoría que no existe
- CUANDO se valida
- ENTONCES la fila se marca con error indicando la categoría inexistente

### Requirement: Importadores de productos y de fichas
El sistema MUST proveer un importador de productos y uno de fichas. La ficha importa campos base (identificación,
nombre, roles, contacto) y NO importa términos de crédito ni lista de precios. El sistema MUST ofrecer una
plantilla descargable por entidad con las columnas esperadas.

#### Scenario: Supervisor importa fichas con roles múltiples
- DADO un archivo de fichas con una fila que declara roles cliente y proveedor
- CUANDO confirma la importación
- ENTONCES la ficha se crea con ambos roles

#### Scenario: Supervisor descarga la plantilla de una entidad
- DADO un usuario con el módulo `bulk-import`
- CUANDO solicita `GET /bulk-import/products/template`
- ENTONCES el Backend MUST responder `200 OK` con un CSV de ejemplo con las columnas esperadas

### Requirement: Validación del archivo (tipo, tamaño y límite de filas)
El sistema MUST rechazar archivos con formato no soportado, que excedan el tamaño máximo o el límite de filas
por archivo (constante centralizada), respondiendo `400 Bad Request` sin procesar el contenido.

#### Scenario: Usuario sube un archivo que excede el límite de filas
- DADO un archivo cuyo número de filas supera el límite configurado
- CUANDO se envía al endpoint de importación
- ENTONCES el Backend MUST responder `400 Bad Request` indicando que debe dividir el archivo
- Y el Frontend MUST mostrar el mensaje al usuario

#### Scenario: Usuario sube un archivo con formato no soportado
- DADO un archivo que no es CSV ni Excel
- CUANDO se envía al endpoint de importación
- ENTONCES el Backend MUST responder `400 Bad Request` indicando el formato inválido
- Y no persiste ningún registro

### Requirement: Restricción de acceso por perfil
La importación MUST estar restringida a perfiles con el módulo `bulk-import` (Jefe/Supervisor). Un usuario sin
ese permiso MUST recibir `403 Forbidden`.

#### Scenario: Usuario sin permiso intenta importar
- DADO un usuario cuyo perfil NO incluye el módulo `bulk-import`
- CUANDO accede a `POST /bulk-import/products`
- ENTONCES el Backend MUST responder `403 Forbidden` con `{detail}` genérico
- Y el Frontend MUST NOT mostrar el asistente de importación a ese perfil

#### Scenario: Usuario sin sesión intenta importar
- DADO un usuario sin sesión activa (sin token SimpleJWT válido)
- CUANDO accede a `POST /bulk-import/products`
- ENTONCES el Backend MUST responder `401 Unauthorized`
- Y el Frontend MUST redirigir al login (authProvider de Refine)
