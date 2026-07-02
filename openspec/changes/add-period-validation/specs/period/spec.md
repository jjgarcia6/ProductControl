# Delta para period

> Los Scenarios describen la **regla de dominio** (comportamiento del validador
> `assert_date_operable`), no endpoints HTTP. En F9 los períodos `CLOSED` se establecen creando la
> fila directamente (no hay proceso de cierre hasta F25). El código HTTP de rechazo es **400** con la
> forma `non_field_errors` del contrato de errores uniforme (reutiliza el `ValidationError` ya
> mapeado por `apps.common`).

## ADDED Requirements

### Requirement: Período contable mensual con estado
El sistema MUST representar cada mes contable como un período único por `(año, mes)` con estado `OPEN`
o `CLOSED`. El sistema MUST NOT permitir dos períodos con el mismo `(año, mes)`. Los períodos MUST NOT
eliminarse; su ciclo de vida se gobierna por transición de estado.

#### Scenario: Unicidad del período
- **DADO** un período existente para un `(año, mes)`
- **CUANDO** se intenta crear otro período con el mismo `(año, mes)`
- **ENTONCES** el sistema rechaza la creación por violación de unicidad

### Requirement: Validación de período cerrado antes de escribir
Antes de crear o modificar un documento, el sistema MUST validar que ninguna fecha involucrada en la
escritura pertenezca a un período cerrado. Si la fecha pertenece a un período cerrado, el sistema MUST
rechazar la operación con HTTP `400` y el contrato de errores uniforme (`non_field_errors`).

#### Scenario: Fecha en mes sin período registrado (implícita-abierta)
- **DADO** que no existe un período para el `(año, mes)` de la fecha del documento
- **CUANDO** se valida esa fecha
- **ENTONCES** el sistema la considera operable y permite continuar

#### Scenario: Fecha en período abierto
- **DADO** un período `OPEN` para el `(año, mes)` de la fecha del documento
- **CUANDO** se valida esa fecha
- **ENTONCES** el sistema la considera operable y permite continuar

#### Scenario: Crear documento con fecha en período cerrado
- **DADO** un período `CLOSED` para el `(año, mes)` de la fecha del documento
- **CUANDO** se valida esa fecha al crear
- **ENTONCES** el sistema responde HTTP `400` con `{"non_field_errors": ["La fecha pertenece a un período cerrado."]}`

#### Scenario: Modificar un documento cuya fecha está en período cerrado
- **DADO** un documento cuya fecha actual pertenece a un período `CLOSED`
- **CUANDO** se intenta modificarlo
- **ENTONCES** el sistema rechaza la modificación con el mismo error `400` de período cerrado

#### Scenario: Mover la fecha de un documento hacia un período cerrado
- **DADO** un documento cuya fecha actual pertenece a un período `OPEN`
- **Y** un período `CLOSED` en otro `(año, mes)`
- **CUANDO** se intenta cambiar la fecha del documento hacia ese período cerrado
- **ENTONCES** el sistema rechaza la modificación con el error `400` de período cerrado
