# Diseño Técnico: align-shadcn-tailwind4-tokens

> Cambio **exclusivo de frontend** (tooling + design tokens). Las capas de Datos y API no
> aplican y se documentan como tal para respetar la separación por capas (DIP/SRP); el grueso
> del diseño vive en la Capa de Presentación y en Configuración.

## 1. Capa de Datos (PostgreSQL + Django ORM)

**No aplica.** Este cambio NO toca el backend: sin tablas, sin modelos Django, sin migraciones,
sin índices ni constraints.

### Impacto en Invariantes del Sistema

- **Período cerrado:** No aplica. No se crean documentos.
- **Kardex FIFO / append-only:** No aplica.
- **Doble costeo:** No aplica.
- **Cuadre de ruta:** No aplica.
- **Snapshot inmutable de entrega:** No aplica.
- **Nota de crédito vinculada:** No aplica.
- **Soft delete (3 clases):** No aplica.
- **Trazabilidad:** No se altera la cadena de trazabilidad.

---

## 2. Capa de API y Contratos (Fuente de Verdad)

**No aplica.** No se añaden ni modifican serializers DRF, tipos Zod/TS generados, endpoints ni
servicios. El contrato OpenAPI no cambia.

---

## 3. Capa de Presentación (UI — Design System)

El corazón del cambio: definir **una sola vez** el sistema visual sobre el contrato canónico de
shadcn v4, mapeando la paleta de `config.yaml` a los slots de shadcn, antes de maquetar pantallas.

### 3.1 Mapeo paleta → slots de shadcn

Dos categorías de token:

- **Declarado** = valor fijado en `config.yaml`; el mapeo MUST reproducirlo **idéntico** (criterio
  de aborto de la propuesta).
- **Derivado** = slot que shadcn exige pero `config.yaml` no fija; se elige un neutro cálido o se
  reutiliza un valor declarado, sin introducir un color nuevo de identidad.

| Slot shadcn | Origen | Claro | Oscuro | Categoría |
| :--- | :--- | :--- | :--- | :--- |
| `--background` | fondo | `#FAF9F7` | `#191816` | Declarado |
| `--foreground` | texto | `#20201E` | `#ECEAE5` | Declarado |
| `--card` / `--popover` | superficie (= `--surface`) | `#FFFFFF` | `#232220` | Declarado |
| `--card-foreground` / `--popover-foreground` | texto | `#20201E` | `#ECEAE5` | Declarado |
| `--primary` | índigo frío | `#4F52C9` | `#8488E6` | Declarado |
| `--primary-foreground` | texto sobre primary | `#FFFFFF` | `#191816` | Derivado (contraste AA) |
| `--secondary` | neutro cálido bajo énfasis | `#F1EFEA` | `#2A2825` | Derivado |
| `--secondary-foreground` | texto | `#20201E` | `#ECEAE5` | Declarado |
| `--muted` | = secondary | `#F1EFEA` | `#2A2825` | Derivado |
| `--muted-foreground` | texto-2 | `#6F6E69` | `#A29F99` | Declarado |
| `--accent` | = muted (hover de ítems) | `#F1EFEA` | `#2A2825` | Derivado |
| `--accent-foreground` | texto | `#20201E` | `#ECEAE5` | Declarado |
| `--destructive` | danger (estado) | `#BE4940` | `#DE7269` | Declarado |
| `--destructive-foreground` | texto sobre danger | `#FFFFFF` | `#191816` | Derivado (contraste AA) |
| `--border` | borde | `#E9E7E1` | `#312E2A` | Declarado |
| `--input` | = border | `#E9E7E1` | `#312E2A` | Declarado |
| `--ring` | = primary (foco) | `#4F52C9` | `#8488E6` | Declarado |

**Decisión sobre `--destructive`:** es el único slot de shadcn que adopta un color de estado
(`danger`). NO contradice la regla "semánticos exclusivos de estados": `destructive` ES un estado
(acción peligrosa/borrado), no un acento decorativo.

**Tokens propios conservados POR ENCIMA del set shadcn** (shadcn no los cubre; siguen disponibles
para uso explícito de estado, nunca decorativo):

| Token propio | Claro | Oscuro |
| :--- | :--- | :--- |
| `--surface` | `#FFFFFF` | `#232220` |
| `--success` | `#3E875A` | `#67B083` |
| `--warning` | `#B07D1C` | `#D9A53F` |
| `--danger` | `#BE4940` | `#DE7269` |
| `--info` | `#3C6FA2` | `#6B97C4` |

**Radios** — se conservan los explícitos declarados y se añade un `--radius` base para los
componentes shadcn que lo lean directamente:

| Token | Valor | Notas |
| :--- | :--- | :--- |
| `--radius` | `8px` | Base (= md) para componentes que usan `var(--radius)` directo |
| `--radius-sm` | `4px` | Declarado |
| `--radius-md` | `8px` | Declarado |
| `--radius-lg` | `12px` | Declarado |
| `--radius-pill` | `999px` | Declarado |

### 3.2 Estructura del theme (CSS-first Tailwind v4)

`src/index.css` queda como **única** fuente del sistema visual (se retira `tailwind.config.js`):

```css
@import 'tailwindcss';
@import 'tw-animate-css';        /* animaciones de overlays shadcn (dialog/dropdown/...) */

@custom-variant dark (&:is(.dark *));  /* modo oscuro por clase .dark en <html> */

:root {
  /* slots shadcn + tokens propios — valores hex de la tabla 3.1 (modo claro) */
}
.dark {
  /* mismos slots — valores de modo oscuro */
}

@theme inline {
  /* mapeo token CSS -> utilidad Tailwind (reemplaza theme.extend del config.js) */
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-card: var(--card);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  /* ... resto de slots shadcn ... */
  --color-surface: var(--surface);
  --color-success: var(--success);
  --color-warning: var(--warning);
  --color-danger: var(--danger);
  --color-info: var(--info);
  --radius-sm: var(--radius-sm);
  --radius-md: var(--radius-md);
  --radius-lg: var(--radius-lg);
  --radius-pill: var(--radius-pill);
}
```

El `ThemeProvider` existente (clase `.dark` en `<html>`, arranque por `prefers-color-scheme`,
persistencia) NO cambia: sigue siendo el que gobierna el modo.

### 3.3 `components.json` y directorios

- `components.json`: campo `tailwind.config` → `""` (setup canónico v4; shadcn deja de buscar un
  JS config). El resto de alias se conserva (`ui: @/components/ui`, `utils: @/shared/lib/utils`).
- Crear `src/components/ui/` (alias `aliases.ui`). Aquí van **solo** las primitivas generadas por la
  CLI de shadcn (ISP). Los componentes visuales compuestos del proyecto siguen en
  `@/components/custom/` (regla de `config.yaml`).
- Verificación del flujo: `npx shadcn add button` → genera `src/components/ui/button.tsx`, que
  MUST compilar y resolver `bg-primary`, `ring-ring`, `border-input`, `rounded-md`.

No se crean features, páginas, hooks ni resources de dominio en este cambio (YAGNI).

---

## 4. Configuración y DevSecOps

### Gestión de Secretos

No se añaden variables de entorno (ni backend ni `VITE_*`). El cambio no maneja secretos.

### Seguridad Proactiva

- **Análisis Estático Frontend:** `eslint` + `tsc` limpios sobre `src/index.css` (vía build),
  `components.json` y el `button.tsx` de prueba.
- **SCA (Dependencias):** las 3 dependencias nuevas pasan por `npm audit` / Dependabot del pipeline
  frontend antes del merge.

---

## 5. Cambios Estructurales

### Nuevas Dependencias

| Paquete | Versión | Entorno | Justificación |
| :--- | :--- | :--- | :--- |
| `lucide-react` | pineada en lockfile | Frontend | Icon library declarada en `config.yaml` y en `components.json` (`iconLibrary: lucide`); las primitivas shadcn importan de aquí. Sin ella, todo componente con icono falla. |
| `class-variance-authority` | pineada en lockfile | Frontend | Lo usan button/badge/input/etc. de shadcn para componer variantes; `cn()` solo no basta. |
| `tw-animate-css` | pineada en lockfile | Frontend | Provee las utilidades de animación (`animate-in`, `fade-in`, etc.) que dialog/dropdown/accordion de shadcn requieren en Tailwind v4 (sustituye a `tailwindcss-animate` de v3). |

### Eliminaciones estructurales

- `tailwind.config.js` y la directiva `@config '../tailwind.config.js'` de `src/index.css`: se
  retiran al migrar el mapeo a `@theme inline`. Reversible vía control de versiones.

### Migraciones de Base de Datos

No aplica (cambio sin backend).
