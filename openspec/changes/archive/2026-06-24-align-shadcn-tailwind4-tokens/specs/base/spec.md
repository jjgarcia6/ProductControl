# Delta para base

<!-- Cambio de infraestructura de frontend (design system / shadcn). Dominio: base. -->
<!-- No hay endpoints DRF ni actores de dominio; los escenarios verifican el sistema visual y el build. -->

## ADDED Requirements

### Requirement: El theme MUST exponer el contrato canónico de variables CSS de shadcn

El sistema de tokens del frontend MUST definir, en `src/index.css`, el conjunto completo de
variables CSS que shadcn/ui v4 espera (`--background`, `--foreground`, `--card`,
`--card-foreground`, `--popover`, `--popover-foreground`, `--primary`, `--primary-foreground`,
`--secondary`, `--secondary-foreground`, `--muted`, `--muted-foreground`, `--accent`,
`--accent-foreground`, `--destructive`, `--border`, `--input`, `--ring`, `--radius`), tanto en
`:root` (modo claro) como en `.dark` (modo oscuro). Cada variable de color MUST resolverse a un
valor derivado de la paleta cálida declarada en `config.yaml`; los componentes MUST NOT contener
hex literales.

#### Scenario: Desarrollador genera un componente shadcn que resuelve todas sus clases

- **DADO** que `src/index.css` define el contrato canónico de variables shadcn en `:root` y `.dark`
- **Y** que `components.json` apunta al setup canónico de Tailwind v4
- **CUANDO** el desarrollador ejecuta `npx shadcn add button`
- **ENTONCES** el componente generado en `src/components/ui/button.tsx` MUST compilar con `tsc`
- **Y** todas sus utilidades de theme (`bg-primary`, `text-primary-foreground`, `ring-ring`,
  `border-input`, `rounded-md`) MUST resolver contra una variable CSS existente
- **Y** el build de producción (`vite build`) MUST completarse sin error

#### Scenario: El build falla si una variable del contrato queda sin definir

- **DADO** que un componente de `src/components/ui/` usa una utilidad de theme (p. ej. `ring-ring`)
- **CUANDO** la variable CSS correspondiente (`--ring`) NO está definida en el theme
- **ENTONCES** la utilidad MUST quedar sin valor resuelto y el resultado visual MUST ser detectable
  como regresión en la verificación
- **Y** el contrato MUST considerarse incompleto hasta que la variable exista en `:root` y `.dark`

### Requirement: El mapeo de paleta a slots shadcn MUST preservar la identidad visual de config.yaml

El mapeo de la paleta del proyecto a los slots de shadcn MUST conservar exactamente los valores de
color declarados en `config.yaml`: neutros cálidos (fondo `#FAF9F7` claro / `#191816` oscuro, etc.),
`primary` índigo frío (`#4F52C9` / `#8488E6`) y `--radius` derivado de la escala sm 4 / md 8 / lg 12.
Los tokens propios del proyecto que shadcn no cubre (`--surface` y los semánticos de estado
`--success`, `--warning`, `--danger`, `--info`) MUST conservarse por encima del set de shadcn. Los
semánticos de estado MUST NOT usarse como acento decorativo.

#### Scenario: Los colores resueltos coinciden con config.yaml tras el mapeo

- **DADO** el theme migrado al contrato shadcn en `:root` y `.dark`
- **CUANDO** se inspeccionan los valores resueltos de `--background`, `--foreground`, `--primary`,
  `--border` y los radios
- **ENTONCES** cada valor MUST ser idéntico al hex declarado en `config.yaml` para su modo
- **Y** los tokens `--surface`, `--success`, `--warning`, `--danger`, `--info` MUST seguir presentes
  y con sus valores originales

#### Scenario: Un cambio de mapeo que altera un color declarado se rechaza

- **DADO** la comparación entre los valores resueltos del theme y la tabla de color de `config.yaml`
- **CUANDO** cualquier valor resuelto difiere del hex declarado
- **ENTONCES** el cambio MUST considerarse fallido (deriva de identidad visual)
- **Y** MUST corregirse el mapeo antes de continuar, conforme al criterio de aborto de la propuesta

### Requirement: El theme MUST usar el enfoque CSS-first de Tailwind v4

El mapeo de tokens a utilidades de Tailwind MUST hacerse vía `@theme inline` en `src/index.css`
(CSS-first de Tailwind v4). El proyecto MUST NOT depender de `tailwind.config.js`
(`theme.extend`) ni de la directiva `@config` para exponer los tokens del design system. El modo
oscuro MUST seguir gobernándose por la clase `.dark` en `<html>` aplicada por el ThemeProvider.

#### Scenario: Las utilidades de theme funcionan sin tailwind.config.js

- **DADO** que `src/index.css` declara los tokens vía `@theme inline`
- **Y** que `tailwind.config.js` y la directiva `@config` han sido retirados
- **CUANDO** se ejecuta `vite build`
- **ENTONCES** las utilidades existentes (`bg-background`, `text-foreground`, `border-border`,
  `rounded-md`, `rounded-pill`) MUST seguir resolviendo correctamente
- **Y** el alternar la clase `.dark` en `<html>` MUST cambiar los valores resueltos a los del modo
  oscuro

### Requirement: El frontend MUST declarar las dependencias que exige el stack de UI

El `package.json` del frontend MUST incluir, pineadas en el lockfile, las dependencias que el stack
de UI de `config.yaml` requiere y que la CLI de shadcn necesita: `lucide-react` (icon library),
`class-variance-authority` y `tw-animate-css`.

#### Scenario: Las dependencias del stack de UI están instaladas y pineadas

- **DADO** el `package.json` y el lockfile del frontend
- **CUANDO** se inspeccionan las dependencias
- **ENTONCES** `lucide-react`, `class-variance-authority` y `tw-animate-css` MUST estar presentes
  con versión pineada en el lockfile
- **Y** un componente shadcn que importe de `lucide-react` o use `cva` MUST compilar con `tsc`
