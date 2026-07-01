# Delta para access-control

<!-- Keywords Gherkin en español (DADO/CUANDO/ENTONCES/Y); keywords RFC 2119 en inglés. -->
<!-- Este delta AÑADE el módulo `system-settings` al catálogo de permisos y lo siembra en los -->
<!-- perfiles JEFE/SUPERVISOR. La autorización efectiva (403/401) se especifica en el delta de -->
<!-- `system-settings` y NO se duplica aquí (DRY). -->

## ADDED Requirements

### Requirement: Módulo `system-settings` en el catálogo de permisos

El catálogo de permisos de `access-control` MUST incluir el módulo `system-settings` con las acciones
`read` y `update`. Los perfiles semilla MUST otorgar `system-settings` en `read`+`update` al perfil
`JEFE` y en `read` al perfil `SUPERVISOR`, tanto en instalaciones nuevas (seed) como en entornos ya
sembrados (data migration idempotente). La autorización efectiva (403/401) se especifica en el delta
de `system-settings` y MUST NOT duplicarse aquí (DRY).

#### Scenario: El catálogo registra el módulo en instalaciones nuevas

- **DADO** un entorno sin sembrar
- **CUANDO** se ejecuta la siembra de perfiles del sistema
- **ENTONCES** el perfil `JEFE` MUST obtener `system-settings` en `read` y `update`
- **Y** el perfil `SUPERVISOR` MUST obtener `system-settings` en `read`

#### Scenario: El parche no pisa permisos en entornos ya sembrados

- **DADO** un entorno con `JEFE` y `SUPERVISOR` ya sembrados sin `system-settings`
- **CUANDO** se aplica la data migration de parche
- **ENTONCES** `JEFE` MUST ganar `system-settings` en `read` y `update` conservando sus permisos
  previos
- **Y** `SUPERVISOR` MUST ganar `system-settings` en `read` conservando sus permisos previos

#### Scenario: La reversión retira solo la clave añadida

- **DADO** los perfiles semilla parcheados con `system-settings`
- **CUANDO** se revierte la data migration de parche
- **ENTONCES** el sistema MUST retirar la clave `system-settings` de `JEFE` y `SUPERVISOR`
- **Y** MUST conservar intactos los demás permisos de cada perfil
