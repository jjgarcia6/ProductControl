# Diseño Técnico: add-directory

> Identificadores técnicos en inglés; documentación en español. Valores de dominio (estados, roles,
> facetas) se persisten con códigos en inglés y se muestran en español en la UI.

## 1. Capa de Datos (PostgreSQL + Django ORM)

### Tablas e Índices

| Tabla | Índice / Constraint | Tipo | Justificación |
| :--- | :--- | :--- | :--- |
| `directory_fichas` | `identification_number` WHERE `status != 'INACTIVO'` | `partial-unique` | Unicidad del número solo entre fichas no inactivas (soft delete clase 3: la baja es el estado). |
| `directory_fichas` | `roles` | `GIN` | Consultar/filtrar fichas por rol (ArrayField). |
| `directory_fichas` | `status` | `btree` | Listados filtran por estado y excluyen INACTIVO por defecto. |
| `directory_fichas` | `user_id` | `unique (O2O) / fk` | Vínculo 1:1 con `accounts.User`, `on_delete=SET_NULL`. |
| `credit_terms` | `(ficha_id, facet)` | `unique compound` | A lo sumo un juego de términos por (ficha, faceta). |
| `credit_terms` | `ficha_id` | `fk` | Navegar términos desde la ficha. |

### Modelo Django

<!-- Política soft delete 3 clases: Ficha = clase 3 (estado INACTIVO), NO hereda SoftDeleteModel.
     CreditTerms = dato dependiente sin máquina de estado propia. Ambos heredan TimeStampedModel. -->

```python
# Modelo Django — Tabla: directory_fichas   (app `directory`)
# Mixins: TimeStampedModel (siempre). NO SoftDeleteModel: la baja es el estado INACTIVO (clase 3).
# Códigos de enum en español MAYÚSCULAS, consistentes con accounts.Role (JEFE/SUPERVISOR/RUTA).

class IdentificationType(models.TextChoices):
    CEDULA = "CEDULA", "Cédula"
    RUC = "RUC", "RUC"
    PASAPORTE = "PASAPORTE", "Pasaporte"

class FichaRole(models.TextChoices):
    CLIENTE = "CLIENTE", "Cliente"
    PROVEEDOR = "PROVEEDOR", "Proveedor"
    RESPONSABLE_RUTA = "RESPONSABLE_RUTA", "Responsable de ruta"
    CHOFER = "CHOFER", "Chofer"

class FichaStatus(models.TextChoices):
    ACTIVO = "ACTIVO", "Activo"
    BLOQUEADO = "BLOQUEADO", "Bloqueado"
    INACTIVO = "INACTIVO", "Inactivo"

class Ficha(TimeStampedModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)                    # nombre o razón social
    identification_type = models.CharField(max_length=10, choices=IdentificationType.choices)
    identification_number = models.CharField(max_length=20)    # validado por dígito verificador
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    roles = ArrayField(models.CharField(max_length=20, choices=FichaRole.choices))  # ≥1, validado
    status = models.CharField(max_length=10, choices=FichaStatus.choices, default=FichaStatus.ACTIVO)
    user = models.OneToOneField("accounts.User", null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="ficha")

    class Meta:
        db_table = "directory_fichas"
        constraints = [
            models.UniqueConstraint(
                fields=["identification_number"],
                condition=~models.Q(status="INACTIVO"),
                name="uq_ficha_identification_number_not_inactive",
            ),
        ]
        indexes = [GinIndex(fields=["roles"], name="ix_ficha_roles_gin")]


# Modelo Django — Tabla: credit_terms   (app `credit`)
# Mixins: TimeStampedModel. Dato dependiente de Ficha; sin estado propio. Términos = SOLO datos en F4.

class CreditFacet(models.TextChoices):
    CLIENTE = "CLIENTE", "Cliente"
    PROVEEDOR = "PROVEEDOR", "Proveedor"

class CreditTerms(TimeStampedModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ficha = models.ForeignKey("directory.Ficha", on_delete=models.CASCADE, related_name="credit_terms")
    facet = models.CharField(max_length=10, choices=CreditFacet.choices)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    term_days = models.PositiveIntegerField(default=0)
    notice_days = models.PositiveIntegerField(default=2)

    class Meta:
        db_table = "credit_terms"
        constraints = [
            models.UniqueConstraint(fields=["ficha", "facet"], name="uq_credit_terms_ficha_facet"),
        ]
```

### Migración Django

```
# Archivo: directory/migrations/0001_initial.py
#   operations: CreateModel(Ficha) + AddConstraint(uq parcial) + AddIndex(GIN roles)
# Archivo: credit/migrations/0001_initial.py
#   operations: CreateModel(CreditTerms) + AddConstraint(uq ficha,facet)
# Generar: python manage.py makemigrations directory credit
# Aplicar:  python manage.py migrate
# Reverse de prueba: python manage.py migrate directory zero  /  python manage.py migrate credit zero
# Ambas son CreateModel: reverse estándar (drop de tablas). Sin data migration.
```

### Impacto en Invariantes del Sistema

- **Período cerrado:** N/A. La ficha y los términos son datos maestros, no documentos con fecha.
- **Kardex FIFO / append-only:** N/A. No se generan movimientos de Kardex.
- **Doble costeo:** N/A. No interviene costo nominal ni efectivo.
- **Cuadre de ruta:** N/A. No toca peso ingresado/entregado/merma.
- **Snapshot inmutable de entrega:** N/A. No hay entregas en esta fase.
- **Nota de crédito vinculada:** N/A. No hay CxP en esta fase.
- **Soft delete (3 clases):** Ficha = **clase 3** (estado INACTIVO, reversible; nunca `deleted_at`).
  `CreditTerms` es dato dependiente sin baja lógica propia (se elimina/edita con su ficha).
- **Trazabilidad:** No se altera. F4 provee la entidad maestra que las cadenas referenciarán después.

---

## 2. Capa de API y Contratos (Fuente de Verdad)

### Diccionario de Datos Vivo

| Entidad | Campo | Tipo (Py / TS) | Descripción (Uso y Propósito) | Restricciones |
| :--- | :--- | :--- | :--- | :--- |
| `Ficha` | `name` | `str / string` | Nombre o razón social del tercero. | Requerido, ≤255. |
| `Ficha` | `identification_type` | `enum / enum` | Tipo de identificación. | CEDULA \| RUC \| PASAPORTE. |
| `Ficha` | `identification_number` | `str / string` | Número de identificación validado por dígito verificador (pasaporte sin checksum). | Requerido; único entre fichas no inactivas. |
| `Ficha` | `email` | `str / string` | Correo de contacto. | Opcional, formato email. |
| `Ficha` | `phone` | `str / string` | Teléfono/WhatsApp. | Opcional, ≤20. |
| `Ficha` | `roles` | `list[str] / string[]` | Roles del tercero. | ≥1 de CLIENTE/PROVEEDOR/RESPONSABLE_RUTA/CHOFER. |
| `Ficha` | `status` | `enum / enum` | Estado de la ficha (read-only en write; cambia por acciones). | ACTIVO \| BLOQUEADO \| INACTIVO. |
| `Ficha` | `user` | `UUID? / string?` | Usuario del sistema vinculado (1:1). | Opcional, nullable. |
| `CreditTerms` | `ficha` | `UUID / string` | Ficha a la que aplican los términos. | Requerido, FK. |
| `CreditTerms` | `facet` | `enum / enum` | Faceta a la que aplican. | CLIENTE \| PROVEEDOR; única por ficha. |
| `CreditTerms` | `credit_limit` | `Decimal / number` | Límite de crédito. | ≥0, default 0. |
| `CreditTerms` | `term_days` | `int / number` | Plazo de crédito en días. | ≥0, default 0. |
| `CreditTerms` | `notice_days` | `int / number` | Días de aviso previo al vencimiento. | ≥0, default 2. |

### Backend: Serializers DRF

```python
# FichaWriteSerializer  — entrada: name, identification_type, identification_number, email, phone, roles
#   · valida identificación según el tipo (apps.common.validations) y devuelve error por campo
#   · valida roles ≥1 ; NO acepta `status` ni `user` directos (cambian por acciones explícitas)
# FichaReadSerializer   — salida: id, name, identificación, contacto, roles, status, user, timestamps
# LinkUserWriteSerializer — entrada: user (UUID) para la acción link-user
# CreditTermsWriteSerializer — entrada: ficha, facet, credit_limit, term_days, notice_days
#   · valida integridad faceta↔rol (la ficha debe tener el rol correspondiente)
# CreditTermsReadSerializer  — salida: id, ficha, facet, credit_limit, term_days, notice_days
# Cada campo con help_text para el OpenAPI / Diccionario Vivo. El ViewSet NO contiene lógica: delega.
```

### Frontend: Tipos generados (Zod + TypeScript)

```typescript
// Generado desde el OpenAPI de DRF (npm run codegen) — NO editar a mano.
// fichaSchema (Zod) y FichaType = z.infer<typeof fichaSchema>
// creditTermsSchema (Zod) y CreditTermsType = z.infer<typeof creditTermsSchema>
// Formato/longitud de identificación por tipo se valida en cliente con Zod (céd 10, RUC 13, numérico);
// el dígito verificador lo valida SOLO el backend (DRY: no se duplica el algoritmo). El error del
// backend se mapea al campo. Los formularios usan React Hook Form + zodResolver(...).
```

### Endpoints de DRF

<!-- Endpoints derivados de los flujos de estado. Transiciones como acciones explícitas, no PUT. -->

| Verbo | Ruta | Write Serializer | Read Serializer | Códigos HTTP | Roles |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/directory/fichas` (filtros `?role=`, `?status=`, `?include_inactive=`) | — | `FichaRead` | `200/401/403` | Jefe, Supervisor |
| `POST` | `/directory/fichas` | `FichaWrite` | `FichaRead` | `201/400/401/403` | Jefe, Supervisor |
| `GET` | `/directory/fichas/{id}` | — | `FichaRead` | `200/401/403/404` | Jefe, Supervisor |
| `PATCH` | `/directory/fichas/{id}` | `FichaWrite` | `FichaRead` | `200/400/401/403/404` | Jefe, Supervisor |
| `POST` | `/directory/fichas/{id}/block` | — | `FichaRead` | `200/401/403/404` | Jefe, Supervisor |
| `POST` | `/directory/fichas/{id}/unblock` | — | `FichaRead` | `200/401/403/404` | Jefe, Supervisor |
| `POST` | `/directory/fichas/{id}/deactivate` | — | `FichaRead` | `200/401/403/404` | Jefe, Supervisor |
| `POST` | `/directory/fichas/{id}/reactivate` | — | `FichaRead` | `200/401/403/404` | Jefe, Supervisor |
| `POST` | `/directory/fichas/{id}/link-user` | `LinkUserWrite` | `FichaRead` | `200/400/401/403/404/409` | Jefe |
| `POST` | `/credit/terms` | `CreditTermsWrite` | `CreditTermsRead` | `201/400/401/403/409` | Jefe, Supervisor |
| `PATCH` | `/credit/terms/{id}` | `CreditTermsWrite` | `CreditTermsRead` | `200/400/401/403/404` | Jefe, Supervisor |

> `status` no se edita por `PATCH /fichas/{id}`: cambia solo por las acciones explícitas. La unicidad de
> número (400/409) y de (ficha, faceta) (409) las resuelve el service y se mapean al contrato uniforme.

### Servicio de Negocio

| Servicio | Método | Responsabilidad única | Transaccional |
| :--- | :--- | :--- | :--- |
| `directory/services.py` | `create_ficha()` | Validar identificación + roles, persistir en ACTIVO. | Sí |
| `directory/services.py` | `update_ficha()` | Editar datos no-estado de la ficha. | Sí |
| `directory/services.py` | `change_status()` | Transiciones ACTIVO↔BLOQUEADO, →INACTIVO reversible. | Sí |
| `directory/services.py` | `link_user()` | Vincular/validar O2O ficha↔usuario. | Sí |
| `credit/services.py` | `upsert_terms()` | Crear/editar términos con integridad faceta↔rol y unicidad. | Sí |

Todos los métodos aplican `@audit(action, entity)` (CREATE/UPDATE/STATE_CHANGE) y usan
`transaction.atomic()`. La validación del dígito verificador se delega a
`apps/common/validations.py` (funciones puras, sin ORM).

---

## 3. Capa de Presentación (UI — React + Refine)

### Árbol de Directorios de la Feature

```
src/features/directory/
├── components/
│   ├── DirectoryList.tsx          # Contenedor: orquesta el listado y filtros (rol/estado)
│   ├── FichaForm.tsx              # Contenedor: alta/edición de ficha + acciones de estado
│   ├── FichaFormFields.tsx       # Presentacional: campos de identificación/contacto/roles
│   └── CreditTermsSubform.tsx    # Presentacional: términos por faceta (solo facetas del rol)
├── hooks/
│   ├── useFichas.ts              # Listado con filtros (useList de Refine)
│   ├── useFichaMutation.ts       # Crear/editar ficha (useCreate/useUpdate)
│   └── useFichaStatus.ts         # Transiciones de estado (useCustomMutation)
├── types/
│   └── directory.types.ts        # Re-exporta tipos generados del OpenAPI (Ficha, CreditTerms)
└── index.ts                       # Contrato público
```

### Contrato Público (`index.ts`)

```typescript
export { DirectoryList } from './components/DirectoryList';
export { FichaForm } from './components/FichaForm';
export { useFichas } from './hooks/useFichas';
export { useFichaMutation } from './hooks/useFichaMutation';
export { useFichaStatus } from './hooks/useFichaStatus';
export type { FichaType, CreditTermsType } from './types/directory.types';
```

### Custom Hooks (`hooks/`)

| Hook | Responsabilidad única | Endpoint / resource | Refine hook |
| :--- | :--- | :--- | :--- |
| `useFichas` | Listar fichas con filtros rol/estado (excluye INACTIVO por defecto). | `GET /directory/fichas` / `fichas` | `useList` |
| `useFichaMutation` | Crear/editar una ficha. | `POST/PATCH /directory/fichas` / `fichas` | `useCreate` / `useUpdate` |
| `useFichaStatus` | Bloquear/reactivar/dar de baja. | `POST /directory/fichas/{id}/{action}` | `useCustomMutation` |
| `useCreditTerms` | Crear/editar términos por faceta. | `POST/PATCH /credit/terms` / `credit-terms` | `useCreate` / `useUpdate` |

### Resources y Páginas (`src/pages/`)

| Ruta / Resource | Tipo | Página (`src/pages/`) | Componente Contenedor | Roles permitidos |
| :--- | :--- | :--- | :--- | :--- |
| `/directory` | Protegida | `DirectoryPage.tsx` | `DirectoryList` | Jefe, Supervisor |
| `/directory/new` · `/directory/:id/edit` | Protegida | `FichaFormPage.tsx` | `FichaForm` | Jefe, Supervisor |

Páginas dumb: importan y renderizan el contenedor; sin `useState`/`useEffect`/fetch directos. La
protección por perfil vive en el `accessControlProvider` de Refine (resuelve por perfil — F2).

---

## 4. Configuración y DevSecOps

### Gestión de Secretos

- **Backend:** sin nuevas variables de entorno. No se agregan claves a `.env.example`.
- **Frontend:** sin nuevas variables `VITE_*`.

### Seguridad Proactiva

- **Análisis Estático Backend:** `ruff`, `mypy --strict` y `bandit` limpios en `apps/directory/`,
  `apps/credit/` y `apps/common/validations.py`.
- **Análisis Estático Frontend:** `eslint` y `tsc` limpios en `src/features/directory/`.
- **SCA:** sin dependencias nuevas previstas; si se añadiera alguna, `pip-audit` / `npm audit` / `trivy`.
- **Server-side:** la validación de identificación es efectiva en el backend; la del cliente es
  conveniencia. Acceso por perfil; listados y acciones respetan los permisos de F2.

---

## 5. Cambios Estructurales

### Nuevas Dependencias

Ninguna nueva. `ArrayField` y `GinIndex` provienen de `django.contrib.postgres` (ya disponible con
PostgreSQL). El algoritmo de dígito verificador se implementa en código propio
(`apps/common/validations.py`), sin librería externa (KISS/YAGNI).

### Migraciones de Base de Datos

Dos migraciones `CreateModel` nuevas (`directory.0001_initial`, `credit.0001_initial`), ambas con
reverse estándar funcional. Sin columnas añadidas a tablas existentes y sin data migration.

### Decisiones resueltas

- **Ubicación de los validadores:** `apps/common/validations.py`. `config.yaml` los nombra como
  `utils/validations.py`; se interpreta como "un módulo utilitario transversal" y se ubica en el hogar
  transversal ya establecido (`apps/common/` aloja `audit.py`, `exceptions.py`, `models.py`), con el
  mismo estilo de `apps/authz/catalog.py` (solo funciones puras, sin imports de Django). Evita crear un
  segundo paquete `utils/` en paralelo (DRY/KISS).
- **Códigos de enum en español MAYÚSCULAS** (`ACTIVO/BLOQUEADO/INACTIVO`,
  `CLIENTE/PROVEEDOR/RESPONSABLE_RUTA/CHOFER`, `CEDULA/RUC/PASAPORTE`, faceta `CLIENTE/PROVEEDOR`),
  consistentes con `accounts.Role` (`JEFE/SUPERVISOR/RUTA/USUARIO`) de F1, con el PLAN y con el F4 doc.
  Los nombres de módulo/acción de autorización siguen siendo kebab inglés (`directory`, `read`/`create`/
  `update`), como `access-control` en F2.
