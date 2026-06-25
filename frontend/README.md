# Frontend — Sistema de gestión operativa

React 19 + Vite + TypeScript (strict) + **Refine v5**. Ver `README.md` raíz para el arranque local.

> El backend es la **fuente de verdad** del contrato. Los tipos TS y los esquemas **Zod se generan**
> del OpenAPI con `npm run codegen` (`../backend/schema.yml` → `src/shared/api/{schema,zod}.ts`).
> NUNCA se escriben a mano. Tras cambiar el contrato del backend, regenera y vuelve a correr `codegen`.

## Stack y reglas

- **Refine v5** gobierna el estado de servidor: React Query vive **dentro** de Refine; no se monta un
  TanStack Query paralelo. **Zustand** solo para estado de UI/sesión (nunca estado de servidor).
- **Formularios:** React Hook Form + `zodResolver` con el Zod **generado**.
- **Tema CSS-first:** `src/index.css` es la **única fuente de color** (variables shadcn vía
  `@theme inline`, Tailwind v4; sin `tailwind.config.js`). **Cero hex literales** en componentes;
  modo claro y oscuro por clase `.dark`. shadcn/ui estilo `new-york`, iconos Lucide.
- **Linter:** ESLint (flat config) — no Oxlint.
- Alias de import: `@/*` → `src/*`.

## Arquitectura

Feature-driven alrededor de los resources de Refine:

```
src/features/<feature>/   components/ · hooks/ · types/ · (api/ providers/ store/)
src/shared/               lógica/contratos compartidos (api/, lib/, providers/, theme/)
src/components/custom/     componentes visuales reutilizables · src/components/ui/ primitivos shadcn
src/pages/                dumb pages: sin estado ni fetch directos; lo asíncrono va en hooks de features/
```

Features actuales: `auth` (F1: login, cambio de contraseña, sesión, gating por perfil + guard de
cambio forzado), `users` y `profiles` (F3: consolas de administración), y `directory` (F4: consola
del Directorio — listado con filtros rol/estado, formulario de ficha con roles múltiples e
identificación validada, acciones de estado y sub-formulario de términos de crédito por faceta).

> **Nota sobre `directory`:** las páginas dumb se montan en rutas protegidas con `<Authenticated>` +
> `ForcePasswordChangeGuard` (esta app no usa `resources`/`accessControlProvider` de Refine; el gating
> es por `usePermissions().canDo(module, action)`). Los hooks usan `dataProviderName: 'auth'` para que
> el `authHttpClient` adjunte el Bearer; el `default` no lo hace. El sub-formulario de crédito usa
> `z.number()` + `valueAsNumber` (no `z.coerce`, que rompe el genérico del resolver en Zod v4).

## Comandos

```bash
npm install
npm run codegen      # genera tipos TS + Zod desde ../backend/schema.yml — correr antes de dev
npm run dev
```

Gates de calidad (todos deben pasar antes de declarar una tarea completa):

```bash
npm run lint         # eslint
npm run typecheck    # tsc -b
npm test             # vitest (un archivo: npx vitest run ruta/al/archivo.test.ts)
npm audit --audit-level=moderate
npx playwright test  # E2E + WebKit (Safari iOS)
```
