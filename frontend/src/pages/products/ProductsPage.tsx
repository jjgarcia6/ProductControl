import { ProductList } from '@/features/products'

/*
  Dumb page: layout + la consola de productos (que encapsula sus hooks). Sin estado ni fetch.
*/
export function ProductsPage() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 py-10">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold text-foreground">Productos</h1>
        <p className="text-sm text-muted-foreground">
          Maestro de productos con su categoría y unidad de medida.
        </p>
      </header>
      <ProductList />
    </main>
  )
}
