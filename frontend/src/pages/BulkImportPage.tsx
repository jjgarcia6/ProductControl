import { ImportWizard } from '@/features/bulk-import'

/*
  Dumb page: layout + el asistente de importación masiva (que encapsula sus hooks). Sin estado
  ni fetch. El gating por perfil lo resuelve el propio asistente.
*/
export function BulkImportPage() {
  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-6 py-10">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold text-foreground">Importación masiva</h1>
        <p className="text-sm text-muted-foreground">
          Carga masiva de maestros (productos y fichas) desde CSV o Excel, con previsualización
          antes de confirmar.
        </p>
      </header>
      <ImportWizard />
    </main>
  )
}
