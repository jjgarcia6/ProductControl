# Propuesta: {{change-name}}

## 1. El Problema o Necesidad de Negocio
<!-- SRP: Esta sección responde ÚNICAMENTE "¿por qué?". -->
<!-- Describe qué está fallando hoy o qué capacidad nueva se necesita, y por qué -->
<!-- es prioritario para el usuario final. Sé directo; evita justificaciones vagas. -->

## 2. Alcance Crítico
<!-- YAGNI: Solo incluir lo estrictamente necesario para resolver el problema descrito. -->
<!-- Las "mejoras de paso" ajenas al dominio de este cambio MUST NOT agregarse. -->

### In-Scope (Lo que se va a construir)
<!-- Describe los flujos de usuario en el Frontend y los dominios afectados en el Backend. -->
<!-- Menciona los nuevos contratos de datos (serializers DRF / tipos Zod generados) que se establecerán. -->

### Out-of-Scope (Prohibiciones Estrictas)
- **Backend:** Toda persistencia MUST ser PostgreSQL vía Django ORM. Sin SQL raw salvo justificación explícita.
- **Backend:** Las transacciones multi-tabla MUST usar `transaction.atomic()` con rollback total.
- **Backend:** Los modelos de catálogo/datos maestros MUST heredar del mixin de soft-delete (política de 3 clases). Los documentos con flujo de estado y el Kardex son append-only: MUST NOT usar soft delete.
- **Backend:** El cálculo financiero (FIFO, costo nominal/efectivo, merma, saldos CxC/CxP) MUST vivir en funciones puras sin dependencia del ORM.
- **Frontend:** Los colores hardcodeados MUST NOT usarse; todo estilo MUST usar tokens del theme (shadcn/Tailwind) con soporte de modo claro y oscuro.
- **Seguridad:** Las credenciales MUST NOT almacenarse en el código; MUST gestionarse vía `.env` / GCP Secret Manager.
- **Calidad:** Las refactorizaciones paralelas ajenas al dominio de este cambio MUST NOT introducirse (YAGNI).
<!-- Añade aquí cualquier restricción adicional específica de este cambio. -->

## 3. Evaluación de Impacto
<!-- DIP: Describir el impacto de capas de más bajo nivel a más alto nivel. -->
<!-- Primero datos, luego lógica de negocio, luego UI. Nunca al revés. -->

### Modelo de Datos (PostgreSQL)
<!-- ¿Qué tablas/modelos Django se crean, modifican o eliminan? -->
<!-- ¿Qué columnas nuevas se agregan? ¿Se necesita migración Django (makemigrations)? -->
<!-- ¿Se afectan índices, constraints, índices únicos parciales (soft delete) o foreign keys existentes? -->
<!-- ¿Se impactan los invariantes del Kardex FIFO, el snapshot inmutable de entrega o la trazabilidad? -->

### Lógica de Negocio y API
<!-- ¿Qué endpoints de DRF se añaden o modifican? (derivados de los flujos de estado, no CRUD por defecto) -->
<!-- ¿Qué servicios (`services.py`) se ven afectados? -->
<!-- ¿Se modifica la lógica FIFO, el costeo nominal/efectivo, la merma, el flujo de soft delete, -->
<!-- la aplicación de cobros (CxC) o pagos a proveedores (CxP)? -->

### Flujo del Usuario (UI)
<!-- ¿Qué cambia en la experiencia visual o interacción en el Frontend (Refine)? -->
<!-- ¿Hay recursos/rutas nuevos (públicos o protegidos)? -->
<!-- ¿Qué roles (Jefe, Supervisor, Responsable de ruta, Usuario) se ven afectados? -->
<!-- ¿Se respetan los estados de pantalla (vacío, carga, error, éxito) y las áreas táctiles >=44px? -->

### Cadena de Trazabilidad
<!-- ¿Este cambio afecta la trazabilidad Ingreso -> Kardex (despiece/merma) -> Entrega -> Cobro, -->
<!-- o Ingreso -> CxP -> Pago? -->
<!-- Si no aplica, indicar explícitamente: "No se altera la cadena de trazabilidad." -->

## 4. Riesgos y Rollback
<!-- KISS: Un riesgo principal, un criterio de aborto claro. Sin sobrecomplicar. -->

### Riesgo Principal
<!-- Describe el riesgo técnico más probable. -->
<!-- Considerar: integridad FIFO, consistencia de saldos CxC/CxP, cuadre de ruta -->
<!-- (peso_ingresado = peso_entregado + merma + peso_sobrante), reversión de devoluciones/anulaciones, -->
<!-- inmutabilidad del snapshot de entrega, compatibilidad de la migración Django (reverse). -->

### Criterio de Aborto
<!-- Define una condición técnica verificable y objetiva para revertir los cambios. -->
<!-- Ejemplo: "Si las pruebas de integración de los endpoints fallan tras 2 intentos de corrección, -->
<!-- o si la migración Django no es reversible (la migración inversa falla)." -->

### Plan de Rollback
<!-- ¿La migración Django tiene reverse funcional? -->
<!-- ¿Se necesita data migration de limpieza o re-cálculo de saldos? -->
