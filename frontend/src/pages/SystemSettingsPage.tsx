import { SystemSettingsContainer } from '@/features/system-settings'

/*
  Dumb page: layout + la consola de configuración global (que encapsula sus hooks). Sin
  estado ni fetch directos.
*/
export function SystemSettingsPage() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-6 py-10">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold text-foreground">Configuración del sistema</h1>
        <p className="text-sm text-muted-foreground">
          Parámetros globales: qué base de costeo (nominal o efectiva) muestran los reportes y
          dashboards. Ambas se calculan siempre; el toggle solo decide qué se presenta.
        </p>
      </header>
      <SystemSettingsContainer />
    </main>
  )
}
