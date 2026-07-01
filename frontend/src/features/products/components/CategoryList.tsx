import { type HttpError } from '@refinedev/core'
import { useState } from 'react'

import { usePermissions } from '@/features/auth'

import { useCategories } from '../hooks/useCategories'
import { INTAKE_TYPE_LABELS, type Category, type CategoryWriteInput } from '../types/products.types'
import { CategoryForm } from './CategoryForm'

/*
  Consola de categorías (F5). Contenedor: orquesta el listado, el alta/edición y la baja lógica.
  Gating por perfil (F2, módulo `products`). Estados vacío/carga/error/éxito. Tokens del theme.
*/

const cardClass = 'rounded-lg border bg-surface p-5'

export function CategoryList() {
  const { canDo } = usePermissions()
  const canCreate = canDo('products', 'create')
  const canManage = canDo('products', 'update')

  const { categories, isLoading, isError, refetch, create, update, remove, isPending } =
    useCategories()
  const [selected, setSelected] = useState<Category | null>(null)
  const [serverError, setServerError] = useState<string | undefined>(undefined)

  const onError = (error: HttpError) => setServerError(error.message)

  const handleSubmit = (values: CategoryWriteInput) => {
    setServerError(undefined)
    const callbacks = { onSuccess: () => setSelected(null), onError }
    if (selected) update(selected.id, values, callbacks)
    else create(values, callbacks)
  }

  if (isLoading) {
    return (
      <p role="status" aria-live="polite" className="text-muted-foreground">
        Cargando categorías…
      </p>
    )
  }

  if (isError) {
    return (
      <div role="alert" className="flex flex-col items-start gap-3 text-danger">
        <p>No se pudieron cargar las categorías.</p>
        <button
          type="button"
          onClick={() => refetch()}
          className="h-11 rounded-md border px-4 text-sm font-medium text-foreground hover:bg-muted"
        >
          Reintentar
        </button>
      </div>
    )
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_24rem]">
      <section aria-label="Categorías" className={cardClass}>
        {categories.length === 0 ? (
          <p className="text-sm text-muted-foreground">Aún no hay categorías registradas.</p>
        ) : (
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="py-2 pr-4 font-medium">Nombre</th>
                <th className="py-2 pr-4 font-medium">Caducidad</th>
                <th className="py-2 pr-4 font-medium">Ingreso</th>
                <th className="py-2 font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {categories.map((category) => (
                <tr key={category.id} className="border-b align-middle">
                  <td className="py-3 pr-4 font-medium text-foreground">{category.name}</td>
                  <td className="py-3 pr-4 text-muted-foreground">{category.shelf_life_days} días</td>
                  <td className="py-3 pr-4 text-muted-foreground">
                    {INTAKE_TYPE_LABELS[category.intake_type]}
                  </td>
                  <td className="py-3">
                    {canManage ? (
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => {
                            setServerError(undefined)
                            setSelected(category)
                          }}
                          className="h-11 rounded-md border px-3 text-sm font-medium text-foreground hover:bg-muted"
                        >
                          Editar
                        </button>
                        <button
                          type="button"
                          onClick={() => remove(category.id, { onError })}
                          disabled={isPending}
                          className="h-11 rounded-md border border-danger px-3 text-sm font-medium text-danger hover:bg-danger/10 disabled:opacity-60"
                        >
                          Dar de baja
                        </button>
                      </div>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <aside className="flex flex-col gap-6">
        {selected ? (
          <section aria-label="Editar categoría" className={cardClass}>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-foreground">Editar categoría</h2>
              <button
                type="button"
                onClick={() => setSelected(null)}
                className="h-11 rounded-md border px-3 text-sm font-medium text-foreground hover:bg-muted"
              >
                Cerrar
              </button>
            </div>
            <CategoryForm
              category={selected}
              isPending={isPending}
              serverError={serverError}
              onSubmit={handleSubmit}
            />
          </section>
        ) : canCreate ? (
          <section aria-label="Nueva categoría" className={cardClass}>
            <h2 className="mb-4 text-lg font-semibold text-foreground">Nueva categoría</h2>
            <CategoryForm isPending={isPending} serverError={serverError} onSubmit={handleSubmit} />
          </section>
        ) : null}
      </aside>
    </div>
  )
}
