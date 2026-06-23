# Diseño Técnico: {{change-name}}
<!-- DIP: Las capas se diseñan de abajo hacia arriba: Datos → API → UI. -->
<!-- Completar cada sección en orden. No pasar a la siguiente sin terminar la anterior. -->

## 1. Capa de Datos (PostgreSQL + Django ORM)
<!-- Esta sección MUST completarse primero. Las capas superiores dependen de ella (DIP). -->

### Tablas e Índices
<!-- Nombrar tablas/modelos en inglés, snake_case en plural (ej: `kardex_movements`). -->
<!-- Definir índices para todos los campos usados en filtros, joins o constraints de unicidad. -->
<!-- Para catálogos con soft delete, usar índice único PARCIAL (WHERE deleted_at IS NULL). -->
<!-- Incluir foreign keys con on_delete explícito. -->

| Tabla | Índice / Constraint | Tipo | Justificación |
| :--- | :--- | :--- | :--- |
| `{{table_name}}` | `{{column(s)}}` | `{{unique / partial-unique / btree / compound / fk}}` | {{Por qué este índice es necesario}} |

### Modelo Django
<!-- KISS: Solo incluir los campos necesarios para este cambio. Sin campos "por si acaso" (YAGNI). -->
<!-- Política de soft delete de 3 clases: -->
<!--   - Catálogos / datos maestros  -> heredan de SoftDeleteMixin (deleted_at + manager filtrado). -->
<!--   - Documentos con flujo de estado y Kardex -> append-only: NO heredan SoftDeleteMixin. -->
<!--   - Todos los modelos -> heredan de TimeStampedMixin (created_at/by, updated_at/by). -->
<!-- Usar DecimalField(max_digits, decimal_places) para valores monetarios y pesos. Nunca FloatField. -->
```python
# Modelo Django — Tabla: {{table_name}}
# Mixins: TimeStampedMixin (siempre) + SoftDeleteMixin (solo catálogos/datos maestros)

class {{ModelName}}(TimeStampedMixin, models.Model):  # + SoftDeleteMixin si es catálogo
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # {{field_name}} = models.{{FieldType}}(...)   # Decimal -> DecimalField(max_digits=.., decimal_places=..)

    class Meta:
        db_table = "{{table_name}}"
        constraints = [
            # models.UniqueConstraint(fields=[...], condition=Q(deleted_at__isnull=True), name="...")
        ]
```

### Migración Django
<!-- Toda migración MUST ser reversible (Django genera el reverse para operaciones estándar). -->
<!-- Para data migrations (RunPython), incluir SIEMPRE reverse_code; nunca dejar noop si hay datos. -->
```
# Archivo: {{app}}/migrations/{{NNNN}}_{{descripcion_breve}}.py
# operations: CreateModel / AddField / AddConstraint / RunPython(forwards, backwards) ...
# Generar con: python manage.py makemigrations {{app}}
# Aplicar con:  python manage.py migrate
# Reverse de prueba: python manage.py migrate {{app}} {{migracion_anterior}}
```

### Impacto en Invariantes del Sistema
<!-- Verificar explícitamente que el cambio no viola ningún invariante. -->
<!-- Si no aplica, indicar "No se alteran invariantes." -->
- **Período cerrado:** {{¿El documento valida que su fecha no caiga en período cerrado?}}
- **Kardex FIFO / append-only:** {{¿Se afecta el saldo, los lotes, el orden FIFO o la inmutabilidad de movimientos?}}
- **Doble costeo:** {{¿Se afecta el costo nominal o el costo efectivo (peso real tras merma)?}}
- **Cuadre de ruta:** {{¿Se afecta peso_ingresado = peso_entregado + merma + peso_sobrante?}}
- **Snapshot inmutable de entrega:** {{¿Se congelan precios y datos del destinatario al pasar a GENERADO?}}
- **Nota de crédito vinculada:** {{¿Toda NC queda vinculada a un Ingreso específico?}}
- **Soft delete (3 clases):** {{¿El modelo es catálogo (soft delete) o documento/Kardex (append-only)? ¿Reversión de efectos?}}
- **Trazabilidad:** {{¿Se altera Ingreso -> Kardex -> Entrega -> Cobro / Ingreso -> CxP -> Pago?}}

---

## 2. Capa de API y Contratos (Fuente de Verdad)
<!-- SRP: Esta sección define ÚNICAMENTE el contrato de datos. Sin lógica de UI aquí. -->

### Diccionario de Datos Vivo
<!-- Este cuadro es el contrato único que sincroniza Backend y Frontend. -->
<!-- DRY: Todo campo definido aquí NO se redefine en ningún otro lugar del proyecto. -->
<!-- Cada campo MUST tener 'help_text' (serializer DRF) y 'description' (en el OpenAPI). -->

| Entidad | Campo | Tipo (Py / TS) | Descripción (Uso y Propósito) | Restricciones |
| :--- | :--- | :--- | :--- | :--- |
| `{{Entity}}` | `{{field}}` | `Decimal / number` | {{Explicación clara para el diccionario}} | {{Min/Max, Unique, Nullable, etc.}} |

### Backend: Serializers DRF
<!-- OCP: Los serializers MUST diseñarse para extenderse sin modificar el serializer base. -->
<!-- Separar serializers de entrada (write) y salida (read). Nunca el mismo para ambos. -->
<!-- Usar DecimalField para valores monetarios y pesos. Nunca float. -->
<!-- El ViewSet/serializer NO contiene lógica de negocio: delega en services/. -->
```python
# {{Entity}}WriteSerializer — entrada (validación de escritura)
# {{Entity}}ReadSerializer  — salida (contrato de lectura)
# Nota: cada campo MUST incluir help_text para el OpenAPI / Diccionario Vivo.

from rest_framework import serializers

class {{Entity}}WriteSerializer(serializers.ModelSerializer):
    # {{field}} = serializers.DecimalField(max_digits=.., decimal_places=.., help_text="{{desc}}")
    class Meta:
        model = {{ModelName}}
        fields = ["{{...}}"]

class {{Entity}}ReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = {{ModelName}}
        fields = ["{{...}}"]
```

### Frontend: Tipos generados (Zod + TypeScript)
<!-- DRY/Contrato: los esquemas Zod y los tipos TS se GENERAN del OpenAPI de DRF (orval/kubb). -->
<!-- Los tipos/Zod MUST NOT escribirse a mano (sería una segunda fuente de verdad). -->
<!-- Derivar tipos con z.infer<>. -->
```typescript
// Generado desde el OpenAPI de DRF — NO editar a mano.
// {{entity}}Schema (Zod) y {{Entity}}Type = z.infer<typeof {{entity}}Schema>
// Los formularios usan React Hook Form + zodResolver({{entity}}Schema).
```

### Endpoints de DRF
<!-- Clean Code: Rutas en inglés, kebab-case, sustantivos en plural. -->
<!-- Los endpoints se DERIVAN de los flujos de estado. Las transiciones de estado son acciones -->
<!-- explícitas (ej: POST /ingresos/{id}/verificar), NO PUT genéricos. NO CRUD completo por defecto. -->

| Verbo | Ruta | Write Serializer | Read Serializer | Códigos HTTP | Roles |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `{{GET/POST/PATCH/DELETE}}` | `/{{recurso}}` o `/{{recurso}}/{id}/{{accion}}` | `{{...Write}}` | `{{...Read}}` | `{{200/201/400/401/403/404/409}}` | `{{Jefe,Supervisor,Responsable de ruta,Usuario}}` |

### Servicio de Negocio
<!-- SRP: Un servicio = una responsabilidad de negocio. La lógica vive aquí, no en el ViewSet. -->
<!-- Los servicios MUST usar `transaction.atomic()` para operaciones multi-tabla. -->
<!-- Los servicios MUST usar el decorator `@audit(action, entity)` para el audit_log. -->
<!-- El cálculo financiero (FIFO, costeo, merma) se delega a funciones puras en `utils/` (sin ORM). -->

| Servicio | Método | Responsabilidad única | Transaccional |
| :--- | :--- | :--- | :--- |
| `{{name}}_service.py` | `{{method}}()` | {{Descripción de una sola línea}} | {{Sí/No}} |

---

## 3. Capa de Presentación (UI — React + Refine)
<!-- SRP: Esta sección solo define estructura de UI. Sin lógica de datos aquí. -->
<!-- DIP: Los componentes dependen de los hooks; los hooks dependen del contrato de API (Refine). -->

### Árbol de Directorios de la Feature
<!-- ISP: Cada módulo expone solo lo que otros necesitan. Todo lo demás es privado. -->
<!-- Las features se organizan alrededor de los resources de Refine. -->
<!-- Mostrar únicamente los archivos que este cambio crea o modifica. -->
```
src/features/{{feature-name}}/
├── components/
│   ├── {{NombreContenedor}}.tsx     # Contenedor: orquesta hooks y sub-componentes
│   └── {{NombrePresentacional}}.tsx # Presentacional: solo recibe props, sin lógica
├── hooks/
│   └── use{{NombreHook}}.ts         # Lógica asíncrona vía data hooks de Refine
├── types/
│   └── {{nombre}}.types.ts          # Re-exporta tipos generados del OpenAPI
└── index.ts                         # Contrato público: exports explícitos de la feature
```
<!-- Regla DRY: Si dos features comparten lógica, extraerla a src/shared/ en lugar de duplicarla. -->
<!-- Regla de tokens: definir el sistema visual (color/tipografía/radios) en tailwind.config + theme -->
<!-- shadcn ANTES de maquetar. Todo color sale de un token; cero hex literales. Estados (vacío/carga/ -->
<!-- error/éxito) obligatorios. Áreas táctiles >=44px en móvil/tablet; inputs >=16px en iOS. -->

### Contrato Público (`index.ts`)
<!-- ISP: Solo exportar lo que otras partes de la app necesitan consumir. -->
```typescript
// Exportaciones explícitas de la feature (no exportar todo con *)
export { {{NombreContenedor}} } from './components/{{NombreContenedor}}';
export { use{{NombreHook}} } from './hooks/use{{NombreHook}}';
export type { {{Entity}}Type } from './types/{{nombre}}.types';
```

### Custom Hooks (`hooks/`)
<!-- SRP: Un hook = una responsabilidad. Prohibido hooks "God Hook" que hagan todo. -->
<!-- Clean Code: Nombrar hooks como use + verbo + sustantivo (ej: useCreateEntrega, useFetchKardex). -->
<!-- Los hooks MUST usar los data hooks de Refine (useList/useOne/useCreate/useUpdate, -->
<!-- useCustomMutation para transiciones de estado). React Query vive DENTRO de Refine: -->
<!-- NO montar TanStack Query en paralelo. -->

| Hook | Responsabilidad única | Endpoint / resource | Refine hook |
| :--- | :--- | :--- | :--- |
| `use{{NombreHook}}` | {{Descripción de una sola línea}} | `{{VERBO /ruta}}` / `{{resource}}` | `{{useList/useCreate/useCustomMutation}}` |

### Resources y Páginas (`src/pages/`)
<!-- SRP: Las páginas son Dumb Pages. Solo importan el componente contenedor y lo renderizan. -->
<!-- Prohibido: useState, useEffect, fetch directamente en una página. -->
<!-- Las rutas/recursos se registran en la configuración de Refine (<Refine resources={...}>); -->
<!-- la protección por rol vive en el authProvider/accessControlProvider. -->

| Ruta / Resource | Tipo | Página (`src/pages/`) | Componente Contenedor | Roles permitidos |
| :--- | :--- | :--- | :--- | :--- |
| `/{{ruta}}` | `{{Protegida}}` | `{{NombrePagina}}.tsx` | `{{NombreContenedor}}` | `{{Jefe,Supervisor,Responsable de ruta,Usuario}}` |

---

## 4. Configuración y DevSecOps

### Gestión de Secretos
<!-- DRY: Centralizar la validación de variables de entorno. Sin variables dispersas. -->
- **Backend:** Listar las variables nuevas que MUST agregarse a `.env.example` del Backend.
  Validadas al inicio en `settings`. Producción: gestionadas en GCP Secret Manager.
- **Frontend:** Listar las variables `VITE_*` nuevas que MUST agregarse a `.env.example` del Frontend
  (solo valores no sensibles; nunca secretos en el bundle).

### Seguridad Proactiva
- **Análisis Estático Backend:** Resultado esperado limpio de `ruff`, `mypy --strict` y `bandit` en los módulos afectados.
- **Análisis Estático Frontend:** Resultado esperado limpio de `eslint` y `tsc` en los componentes afectados.
- **SCA (Dependencias):** Revisión con `pip-audit` (Python), `npm audit`/Dependabot (Node) y `trivy` (imagen) de las nuevas dependencias (si las hay).

---

## 5. Cambios Estructurales
<!-- YAGNI: Solo completar esta sección si el cambio altera dependencias, estructura de carpetas -->
<!-- o requiere migraciones no triviales. Si no aplica, eliminar esta sección. -->

### Nuevas Dependencias
<!-- Justificar cada dependencia nueva. Si se resuelve con código propio en <20 líneas, -->
<!-- evaluar si realmente es necesaria (KISS + YAGNI). Versiones pineadas en lockfile. -->

| Paquete | Versión | Entorno | Justificación |
| :--- | :--- | :--- | :--- |
| `{{nombre-paquete}}` | `{{x.y.z}}` | `{{Backend / Frontend / Ambos}}` | {{Por qué no puede resolverse sin esta dependencia}} |

### Migraciones de Base de Datos
<!-- Documentar si se añaden, renombran o eliminan columnas en tablas existentes. -->
<!-- Describir la estrategia de migración para datos existentes (data migration) si aplica. -->
<!-- Toda migración MUST tener reverse funcional. -->
