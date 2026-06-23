import { ThemeToggle } from '@/components/custom/ThemeToggle'

/*
  Dumb page: sin estado de servidor ni llamadas directas a la API. Lo asíncrono se
  encapsula en custom hooks dentro de features/ (no hay ninguna en el bootstrap).
  Es el cascarón del andamiaje; las pantallas reales llegan en sus changes.
*/
export function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 px-6 py-16">
      <header className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold text-foreground">
          Sistema de gestión operativa
        </h1>
        <ThemeToggle />
      </header>

      <p className="text-muted-foreground">
        Andamiaje listo. Backend (Django + DRF) como fuente de verdad del contrato OpenAPI;
        frontend (React 19 + Vite + Refine) con tipos y Zod generados desde ese contrato.
      </p>

      <div className="rounded-lg border bg-surface p-4">
        <p className="text-sm text-muted-foreground">
          Acento índigo y semánticos de estado verificables:
        </p>
        <div className="mt-3 flex flex-wrap gap-2 text-sm">
          <span className="rounded-pill bg-primary px-3 py-1 text-primary-foreground">
            Acento
          </span>
          <span className="rounded-md border border-success px-3 py-1 text-success">
            Éxito
          </span>
          <span className="rounded-md border border-warning px-3 py-1 text-warning">
            Advertencia
          </span>
          <span className="rounded-md border border-danger px-3 py-1 text-danger">
            Peligro
          </span>
          <span className="rounded-md border border-info px-3 py-1 text-info">Info</span>
        </div>
      </div>
    </main>
  )
}
