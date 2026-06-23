# Tareas: {{change-name}}
<!-- Orden de fases REQUIRED: Contrato → Migraciones → Backend → Frontend → Seguridad → Pruebas. -->
<!-- SRP: No avanzar a la siguiente fase si hay ítems sin completar en la anterior. -->
<!-- Clean Code: Cada tarea nombra el archivo o módulo exacto a crear o modificar. -->

## Fase 0: Contrato y Sincronización Inicial
<!-- DRY: Esta fase es la fuente de verdad compartida. Backend y Frontend dependen de ella. -->
<!-- DIP: Definir abstracciones (contrato) antes de implementar. -->

- [ ] **0.1** Backend — Crear/actualizar serializers DRF en `backend/{{app}}/serializers/{{modulo}}.py`:
  definir `{{Entity}}WriteSerializer` y `{{Entity}}ReadSerializer` con `help_text=...` en cada campo.
  Usar `DecimalField` para valores monetarios y pesos. Nunca `FloatField`.
- [ ] **0.2** Backend — Verificar que el OpenAPI expone el contrato (drf-spectacular u equivalente)
  con los nuevos serializers y sus `help_text`.
- [ ] **0.3** Frontend — Regenerar los tipos/Zod desde el OpenAPI en `frontend/src/features/{{feature}}/types/`:
  ejecutar la generación (orval/kubb). MUST NOT escribirse tipos ni schemas a mano; derivar con `z.infer<>`.
- [ ] **0.4** Global — Actualizar `backend/.env.example` y `frontend/.env.example`
  con las nuevas variables requeridas (si las hay). Variables de cliente solo con prefijo `VITE_`.

## Fase 1: Modelo de Datos y Migraciones
<!-- SRP: Primero el modelo, luego la migración. No combinar con lógica de negocio. -->
<!-- Soft delete por política de 3 clases: catálogos heredan SoftDeleteMixin; documentos y Kardex no. -->

- [ ] **1.1** Crear/actualizar modelo Django en `backend/{{app}}/models/{{modulo}}.py`:
  heredar de `TimeStampedMixin` (siempre) y de `SoftDeleteMixin` solo si es catálogo/dato maestro;
  definir columnas, tipos, foreign keys (`on_delete` explícito) y relaciones.
  Usar `DecimalField(max_digits, decimal_places)` para valores monetarios y pesos. Nunca `FloatField`.
  Para catálogos: definir `UniqueConstraint` PARCIAL (`condition=Q(deleted_at__isnull=True)`).
- [ ] **1.2** Generar migración: `python manage.py makemigrations {{app}}`.
  Revisar el archivo generado; para `RunPython` incluir `reverse_code` (nunca noop si hay datos).
- [ ] **1.3** Aplicar migración en entorno de desarrollo: `python manage.py migrate`.
  Verificar que las tablas/columnas/constraints se crearon correctamente.
- [ ] **1.4** Probar el reverse: `python manage.py migrate {{app}} {{migracion_anterior}}`.
  Verificar que la reversión funciona sin errores. Luego re-aplicar: `python manage.py migrate`.

## Fase 2: Lógica de Negocio y API (Backend)
<!-- OCP: Implementar como extensión; no modificar servicios existentes salvo que sea estrictamente necesario. -->
<!-- SRP: Un servicio = una responsabilidad de negocio. El ViewSet delega, no contiene lógica. -->

- [ ] **2.1** (Si aplica cálculo financiero) Implementar/actualizar la función PURA en
  `backend/{{app}}/utils/{{nombre}}.py` (FIFO, costo nominal/efectivo, merma, saldos):
  sin dependencia del ORM, testeable de forma aislada.
- [ ] **2.2** Crear/modificar el servicio en `backend/{{app}}/services/{{nombre}}_service.py`:
  implementar la lógica con manejo de excepciones tipado (sin capturar `Exception` genérico).
  Usar `transaction.atomic()` para operaciones multi-tabla.
  Aplicar el decorator `@audit(action, entity)` para registrar en `audit_log`.
  Validar período cerrado antes de crear/modificar documentos.
- [ ] **2.3** Crear/modificar el ViewSet/endpoints en `backend/{{app}}/views/{{nombre}}.py`:
  integrar el servicio de 2.2; cada endpoint usa los serializers de Fase 0; ViewSet delgado.
  Las transiciones de estado son acciones explícitas (`@action`), no PUT genéricos.
  Aplicar permisos por rol (`{{Jefe|Supervisor|Responsable de ruta|Usuario}}`).
- [ ] **2.4** Registrar las rutas en `backend/{{app}}/urls.py` con el prefijo `/{{api-prefix}}`.

## Fase 3: Integración de Datos (Frontend — Hooks)
<!-- DIP: Los hooks dependen del contrato de API (Refine), no de detalles del Backend. -->
<!-- SRP: Un hook = un caso de uso. Prohibido hooks que mezclen fetch, estado global y UI. -->

- [ ] **3.1** Crear el hook `use{{NombreHook}}` en `frontend/src/features/{{feature}}/hooks/use{{NombreHook}}.ts`:
  envolver los data hooks de Refine (`useList`/`useOne`/`useCreate`/`useUpdate`/`useCustomMutation`
  para transiciones de estado). NO montar TanStack Query en paralelo (vive dentro de Refine).
  Definir `resource`/query key descriptivos.
- [ ] **3.2** Validar en el hook que la respuesta del Backend cumple el schema Zod generado en Fase 0
  antes de exponer los datos. Lanzar error descriptivo si no coincide.

## Fase 4: Componentes y Páginas (Frontend — UI)
<!-- ISP: Componentes de dominio en `features/`; componentes visuales reutilizables en `@/components/custom/`. -->
<!-- Clean Code: Cada componente hace UNA cosa. -->

- [ ] **4.1** Crear el componente contenedor `{{NombreContenedor}}.tsx` en `features/{{feature}}/components/`:
  consume el hook de Fase 3; orquesta los sub-componentes; sin lógica de presentación directa.
  Cubrir los estados vacío, carga, error y éxito.
- [ ] **4.2** Crear el/los componente(s) presentacional(es) `{{NombrePresentacional}}.tsx` en `features/{{feature}}/components/`:
  reciben solo `props`; sin `useState` propio ni llamadas a la API.
  Todo color desde tokens del theme (cero hex literales); áreas táctiles >=44px; inputs >=16px en iOS.
  Formularios con React Hook Form + `zodResolver`.
- [ ] **4.3** Actualizar el contrato público `frontend/src/features/{{feature}}/index.ts`
  con las exportaciones explícitas de los nuevos componentes, hooks y tipos.
- [ ] **4.4** Crear/actualizar la página `{{NombrePagina}}.tsx` en `frontend/src/pages/`:
  importar y renderizar `{{NombreContenedor}}`; sin lógica de estado ni fetch directos (Dumb Page).
- [ ] **4.5** Registrar el resource/ruta en la configuración de Refine (`<Refine resources={[...]}>`):
  - Definir si es protegido (roles vía `accessControlProvider`: `{{Jefe|Supervisor|Responsable de ruta|Usuario}}`).
  - Aplicar `lazy(() => import(...))` para code splitting.

## Fase 5: Seguridad y DevSecOps
<!-- No negociable. Esta fase no puede eliminarse ni reordenarse. -->

- [ ] **5.1** Backend — Análisis estático en los módulos modificados:
  `ruff check backend/{{app}}/{{modulo}}/` y `mypy --strict backend/{{app}}/{{modulo}}/`. Corregir todos los errores.
- [ ] **5.2** Backend — Escaneo de seguridad: `bandit -r backend/{{app}}/{{modulo}}/`.
  Corregir o documentar toda alerta de severidad MEDIUM o superior.
- [ ] **5.3** Frontend — `eslint frontend/src/features/{{feature}}/` y `tsc --noEmit`. Corregir todos los errores.
- [ ] **5.4** Global — Verificar que no hay secretos en el código (credenciales, tokens, connection strings).
- [ ] **5.5** Dependencias — Si se añadieron en Fase 0: `pip-audit` (Python), `npm audit` (Node) y `trivy fs .`.
  No mergear con CVEs conocidos.
- [ ] **5.6** UI — Validar contraste de color (WCAG AA mínimo) en los nuevos componentes en modo claro y oscuro.

## Fase 6: Pruebas y Validación Final
<!-- SRP: Cada prueba valida un único comportamiento. Nombrar como "should [hacer algo] when [condición]". -->
<!-- DRY: Extraer datos de prueba repetidos a fixtures o factories compartidas. -->
<!-- Gate de cobertura: >=80% global, >=90% en módulos de cálculo financiero. -->

- [ ] **6.1** Backend — Escribir/actualizar pruebas en `backend/{{app}}/tests/test_{{nombre}}.py`:
  - Prueba del contrato JSON para cada endpoint (éxito y error).
  - Prueba de validación de serializer para inputs inválidos (debe retornar `400`).
  - Prueba de rechazo por período cerrado (`409`).
  - Prueba de invariantes de negocio: saldo no negativo, FIFO correcto, cuadre de ruta,
    snapshot inmutable de entrega, nota de crédito vinculada, reversión de efectos.
  - Prueba unitaria de las funciones puras de cálculo financiero (cobertura >=90%).
  - Ejecutar con `pytest backend/{{app}}/tests/test_{{nombre}}.py -v --cov`.
- [ ] **6.2** Frontend — Escribir/actualizar pruebas en `frontend/src/features/{{feature}}/components/{{NombreContenedor}}.test.tsx`:
  - Prueba del flujo principal (éxito) y del feedback de error al usuario.
  - Prueba de los estados vacío/carga/error.
  - Prueba de accesibilidad básica (roles ARIA, navegación por teclado).
  - Ejecutar con `vitest run`.
- [ ] **6.3** E2E / cross-browser — Ejecutar Playwright incluyendo el motor WebKit (Safari/iOS):
  validar el flujo principal y los inputs numéricos decimales y de fecha.
- [ ] **6.4** Integración — Verificar manualmente:
  - No hay operaciones síncronas bloqueantes que choquen con el timeout de Cloud Run.
  - No hay errores en la consola del navegador ni warnings de React.
  - La migración Django es reversible (reverse + migrate sin pérdida de datos).
  - La cadena de trazabilidad se mantiene íntegra (Ingreso -> Kardex -> Entrega -> Cobro / Ingreso -> CxP -> Pago).
- [ ] **6.5** Definition of done — Todos los gates del pipeline (backend y frontend) en verde,
  ejecutados localmente, antes de declarar el cambio completo.
