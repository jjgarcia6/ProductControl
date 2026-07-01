import { CategoryList } from '@/features/products'

/*
  Dumb page: layout + la consola de categorías (que encapsula sus hooks). Sin estado ni fetch.
*/
export function CategoriesPage() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 py-10">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold text-foreground">Categorías</h1>
        <p className="text-sm text-muted-foreground">
          Caducidad, tipo de ingreso y estructura del rango de merma por categoría.
        </p>
      </header>
      <CategoryList />
    </main>
  )
}
