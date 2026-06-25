import { DirectoryList } from '@/features/directory'

/*
  Dumb page: layout + la consola del Directorio (que encapsula sus hooks). Sin estado ni
  fetch directos.
*/
export function DirectoryPage() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 py-10">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold text-foreground">Directorio</h1>
        <p className="text-sm text-muted-foreground">
          Fichas de terceros: identificación, roles, estados y términos de crédito por faceta.
        </p>
      </header>
      <DirectoryList />
    </main>
  )
}
