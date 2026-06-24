# Propuesta: align-shadcn-tailwind4-tokens

## 1. El Problema o Necesidad de Negocio

El `config.yaml` declara la UI como **Tailwind CSS + shadcn/ui + Lucide React** con tokens
expresados como variables CSS de shadcn (`--background`, `--foreground`, `--primary`, `--border`,
`--radius`). El scaffold actual del frontend tiene la *apariencia* de shadcn (existe
`components.json`, el helper `cn()`, alias y tokens en `src/index.css`), pero **no es operativo**:
un `npx shadcn add <componente>` no compila hoy. Esto bloquea la construcción de cualquier
pantalla, porque todas las pantallas dependen de las primitivas de shadcn.

Causas verificadas:

- **Dependencias faltantes que el `config.yaml` exige:** `lucide-react` (icon library declarada en
  `components.json` y en el stack), `class-variance-authority` (lo usan button/badge/input/etc.) y
  `tw-animate-css` (animaciones de dialog/dropdown/accordion en Tailwind v4). Ninguna está en
  `package.json`.
- **Contrato de tokens incompleto:** shadcn asume slots semánticos (`--card`, `--popover`,
  `--secondary`, `--muted`, `--accent`, `--destructive`, `--input`, `--ring`, `--radius` único) que
  hoy no existen. Un `Button` usa `ring-ring`, un `Input` usa `border-input` → revientan.
- **Mapeo de theme estilo Tailwind v3:** los tokens se exponen vía `tailwind.config.js`
  (`theme.extend.colors`) puenteado con `@config`, en lugar del enfoque CSS-first `@theme inline`
  canónico de Tailwind v4 que shadcn detecta y espera.
- **No existe `src/components/ui/`** (el alias `aliases.ui` de `components.json`).

Resolverlo ahora, antes de maquetar pantallas, evita parchear a mano cada componente que la CLI de
shadcn genere en el futuro.

## 2. Alcance Crítico

### In-Scope (Lo que se va a construir)

Cambio **exclusivo de frontend**, de tooling y design tokens. Sin lógica de negocio, sin flujos de
usuario nuevos, sin endpoints. Concretamente:

- Adoptar el **contrato canónico de variables CSS de shadcn v4** en `src/index.css`, mapeando la
  paleta cálida del proyecto (neutros Notion/Claude, índigo frío como `primary`, semánticos de
  estado) dentro de los slots de shadcn (`--background/--foreground`, `--card/--card-foreground`,
  `--popover/--popover-foreground`, `--primary/--primary-foreground`, `--secondary`, `--muted`,
  `--accent`, `--destructive`, `--border`, `--input`, `--ring`, `--radius`) en `:root` y `.dark`.
- Conservar los **tokens propios del proyecto por encima del set shadcn**: `--surface` y los
  semánticos exclusivos de estado (`--success/--warning/--danger/--info`), que shadcn no cubre.
- Migrar el mapeo de theme de `tailwind.config.js` a **`@theme inline` (CSS-first de Tailwind v4)**
  en `src/index.css`, y retirar el `tailwind.config.js` y la directiva `@config`.
- Ajustar `components.json` al setup canónico v4 (`tailwind.config` vacío).
- Instalar y pinear en lockfile las dependencias faltantes: `lucide-react`,
  `class-variance-authority`, `tw-animate-css`.
- Crear `src/components/ui/` y validar el flujo con un componente de prueba (`button`) generado por
  la CLI de shadcn.

### Out-of-Scope (Prohibiciones Estrictas)

- **Backend:** Este cambio NO toca el backend. Sin modelos, sin migraciones, sin endpoints, sin
  servicios.
- **Frontend:** Los colores hardcodeados MUST NOT usarse en componentes; todo estilo MUST salir de
  un token del theme con soporte de modo claro y oscuro. Los hex literales solo viven en el archivo
  de definición de tokens.
- **Frontend:** NO se construyen pantallas, features ni páginas de dominio en este cambio (YAGNI).
  El único componente que se añade es `button`, como verificación del flujo.
- **Frontend:** NO se altera la identidad visual definida en `config.yaml` (paleta cálida, índigo
  frío, semánticos exclusivos de estado, radios sm/md/lg/pill). El mapeo preserva los mismos valores
  de color.
- **Seguridad:** Las credenciales MUST NOT almacenarse en el código.
- **Calidad:** Las refactorizaciones paralelas ajenas a este cambio MUST NOT introducirse (YAGNI).

## 3. Evaluación de Impacto

### Modelo de Datos (PostgreSQL)

**Sin impacto.** No se crean, modifican ni eliminan modelos Django ni tablas. No se requiere
migración. No se afectan índices, constraints ni foreign keys. No se tocan los invariantes de
Kardex FIFO, snapshot inmutable de entrega ni la cadena de trazabilidad.

### Lógica de Negocio y API

**Sin impacto.** No se añaden ni modifican endpoints DRF ni servicios. No se altera FIFO, costeo,
merma, soft delete, CxC ni CxP.

### Flujo del Usuario (UI)

No hay cambio observable en pantallas (no existen pantallas de dominio todavía). El impacto es de
**infraestructura visual**: a partir de este cambio, `npx shadcn add <componente>` funciona
out-of-the-box, las primitivas resuelven sus clases (`bg-primary`, `ring-ring`, `border-input`,
`rounded-md`) contra el theme, y el modo claro/oscuro vía clase `.dark` sigue gobernado por el
ThemeProvider. Sin impacto por rol.

### Cadena de Trazabilidad

No se altera la cadena de trazabilidad.

## 4. Riesgos y Rollback

### Riesgo Principal

Que el mapeo de la paleta cálida a los slots de shadcn **altere visualmente** los colores
declarados en `config.yaml` (deriva de identidad visual), o que la migración de `tailwind.config.js`
a `@theme inline` **rompa utilidades de Tailwind ya en uso** (p. ej. `bg-background`,
`text-foreground`, `rounded-md`) si algún token queda sin mapear.

### Criterio de Aborto

Condición técnica verificable: se aborta y revierte si, tras dos intentos de corrección, (a) el
build del frontend (`tsc` + `vite build`) falla, o (b) `npx shadcn add button` no genera un
componente que compile, o (c) una comparación de los valores de color resueltos en `:root`/`.dark`
muestra cualquier hex distinto a los declarados en `config.yaml` (la paleta debe quedar idéntica).

### Plan de Rollback

El cambio es reversible por control de versiones: revertir el commit restaura `src/index.css`,
`tailwind.config.js`, `components.json` y `package.json`/lockfile al estado previo. No hay migración
de datos ni estado persistido que limpiar.
