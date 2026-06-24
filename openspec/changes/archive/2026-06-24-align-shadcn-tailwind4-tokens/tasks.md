# Tareas: align-shadcn-tailwind4-tokens

<!-- Cambio frontend-only (tooling + design tokens). Las fases de Contrato OpenAPI, Migraciones y -->
<!-- Backend del template estándar NO aplican y se omiten. Se conservan Seguridad y Pruebas. -->
<!-- SRP: cada tarea nombra el archivo exacto. No avanzar de fase con ítems pendientes. -->

## Fase 0: Dependencias (fuente compartida)

- [x] **0.1** Instalar y pinear en `frontend/package.json` + lockfile: `lucide-react`,
  `class-variance-authority`, `tw-animate-css`. Verificar que quedan en `dependencies` con versión
  exacta en `package-lock.json`.

## Fase 1: Contrato de tokens (`src/index.css`)

- [x] **1.1** En `frontend/src/index.css`, definir en `:root` (modo claro) el set completo de slots
  shadcn con los valores de la tabla 3.1 del design: `--background`, `--foreground`, `--card`,
  `--card-foreground`, `--popover`, `--popover-foreground`, `--primary`, `--primary-foreground`,
  `--secondary`, `--secondary-foreground`, `--muted`, `--muted-foreground`, `--accent`,
  `--accent-foreground`, `--destructive`, `--destructive-foreground`, `--border`, `--input`,
  `--ring`, `--radius`.
- [x] **1.2** Replicar el set completo en `.dark` con los valores de modo oscuro de la tabla 3.1.
- [x] **1.3** Conservar los tokens propios `--surface`, `--success`, `--warning`, `--danger`,
  `--info` en `:root` y `.dark` con sus valores originales (no eliminarlos al reescribir).
- [x] **1.4** Conservar `--radius-sm/md/lg/pill` (4/8/12/999) y añadir `--radius: 8px` base.
- [x] **1.5** Verificación de identidad visual: comparar cada valor resuelto contra la tabla de
  color de `config.yaml`; todo slot "Declarado" MUST ser idéntico al hex declarado (criterio de
  aborto). Corregir cualquier deriva antes de continuar.

## Fase 2: Migración a CSS-first (Tailwind v4)

- [x] **2.1** En `frontend/src/index.css`, añadir bloque `@theme inline` que mapee cada token CSS a
  su utilidad Tailwind (`--color-background: var(--background)`, ... incl. tokens propios `--color-surface`,
  `--color-success`, etc., y `--radius-sm/md/lg/pill`). Importar `tw-animate-css`.
- [x] **2.2** Eliminar la directiva `@config '../tailwind.config.js'` de `frontend/src/index.css` y
  borrar `frontend/tailwind.config.js`. Asegurar que `darkMode: 'class'` se preserva vía
  `@custom-variant dark (&:is(.dark *))` en el CSS.
- [x] **2.3** En `frontend/components.json`, fijar `tailwind.config: ""` (setup canónico v4).
  Mantener el resto de alias (`ui`, `utils`, `lib`, `hooks`) sin cambios.

## Fase 3: Operatividad de shadcn

- [x] **3.1** Crear el directorio `frontend/src/components/ui/` (alias `aliases.ui`).
- [x] **3.2** Ejecutar `npx shadcn add button` y verificar que genera
  `frontend/src/components/ui/button.tsx` sin reescritura manual de tokens.
- [x] **3.3** Verificar que el componente compila (`tsc --noEmit`) y que sus utilidades de theme
  (`bg-primary`, `text-primary-foreground`, `ring-ring`, `border-input`, `rounded-md`) resuelven
  contra una variable existente.

## Fase 4: Seguridad y DevSecOps

- [x] **4.1** `eslint frontend/src/` y `tsc --noEmit` limpios sobre `components.json`,
  `src/index.css` (vía build) y `src/components/ui/button.tsx`. Corregir todo error.
- [x] **4.2** Verificar que `src/index.css` es el único lugar con hex literales; ningún componente
  de `src/components/` contiene colores hardcodeados.
- [x] **4.3** SCA de las dependencias nuevas: `npm audit`. No mergear con CVEs conocidos.
- [x] **4.4** Validar contraste WCAG AA de los pares foreground/background (incl. los slots
  "Derivado": `--primary-foreground` sobre `--primary`, `--destructive-foreground` sobre
  `--destructive`) en modo claro y oscuro.

## Fase 5: Pruebas y Validación Final

- [x] **5.1** Build de producción: `vite build` completa sin error y sin warnings de utilidades
  Tailwind no resueltas.
- [x] **5.2** Verificación de modo oscuro: alternar la clase `.dark` en `<html>` cambia los valores
  resueltos de `--background`/`--foreground` a los de la tabla oscura (smoke manual o test de
  componente con `button`).
- [x] **5.3** Confirmar que las utilidades preexistentes (`bg-background`, `text-foreground`,
  `border-border`, `rounded-md`, `rounded-pill`) siguen resolviendo tras retirar
  `tailwind.config.js`.
- [x] **5.4** Definition of done: gates del pipeline frontend (`eslint` → `tsc` → `npm audit` →
  `vitest` → `vite build`) en verde localmente antes de declarar el cambio completo.
