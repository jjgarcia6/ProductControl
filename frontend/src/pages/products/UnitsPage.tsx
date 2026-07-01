import { UnitList } from '@/features/products'

/*
  Dumb page: layout + la consola de unidades (que encapsula sus hooks). Sin estado ni fetch.
*/
export function UnitsPage() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 py-10">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold text-foreground">Unidades de medida</h1>
        <p className="text-sm text-muted-foreground">
          Unidades con su factor de conversión a la base (libras). No se aplica aún.
        </p>
      </header>
      <UnitList />
    </main>
  )
}
