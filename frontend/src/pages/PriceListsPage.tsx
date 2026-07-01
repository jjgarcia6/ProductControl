import { PriceListsContainer } from '@/features/pricing'

/*
  Dumb page: layout + la consola de listas de precios (que encapsula sus hooks). Sin estado ni
  fetch directos.
*/
export function PriceListsPage() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 py-10">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold text-foreground">Listas de precios</h1>
        <p className="text-sm text-muted-foreground">
          Maestro de precios: listas (normal o descarte) y el precio de venta por producto.
        </p>
      </header>
      <PriceListsContainer />
    </main>
  )
}
