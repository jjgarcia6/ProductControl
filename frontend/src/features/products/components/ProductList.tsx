import { type HttpError } from '@refinedev/core'
import { useState } from 'react'

import { usePermissions } from '@/features/auth'

import { useCategories } from '../hooks/useCategories'
import { useProducts } from '../hooks/useProducts'
import { useUnits } from '../hooks/useUnits'
import { type Product, type ProductWriteInput } from '../types/products.types'
import { ProductForm } from './ProductForm'

/*
  Consola de productos (F5). Contenedor: orquesta el listado y el alta/edición/baja. Provee al
  formulario las opciones de categoría y unidad. Gating por perfil (F2, módulo `products`).
  Estados vacío/carga/error/éxito. Tokens del theme.
*/

const cardClass = 'rounded-lg border bg-surface p-5'

type FieldErrors = Partial<Record<'name' | 'category' | 'unit_of_measure', string>>

function toFieldErrors(error: HttpError): { fields: FieldErrors; general?: string } {
  const fields: FieldErrors = {}
  for (const key of ['name', 'category', 'unit_of_measure'] as const) {
    const messages = error.errors?.[key]
    if (messages) fields[key] = Array.isArray(messages) ? messages[0] : String(messages)
  }
  // 409 (nombre duplicado) llega como mensaje general.
  const general = Object.keys(fields).length === 0 ? error.message : undefined
  return { fields, general }
}

export function ProductList() {
  const { canDo } = usePermissions()
  const canCreate = canDo('products', 'create')
  const canManage = canDo('products', 'update')

  const { products, isLoading, isError, refetch, create, update, remove, isPending } = useProducts()
  const { categories } = useCategories()
  const { units } = useUnits()

  const [selected, setSelected] = useState<Product | null>(null)
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [serverError, setServerError] = useState<string | undefined>(undefined)

  const onError = (error: HttpError) => {
    const { fields, general } = toFieldErrors(error)
    setFieldErrors(fields)
    setServerError(general)
  }

  const handleSubmit = (values: ProductWriteInput) => {
    setFieldErrors({})
    setServerError(undefined)
    const callbacks = { onSuccess: () => setSelected(null), onError }
    if (selected) update(selected.id, values, callbacks)
    else create(values, callbacks)
  }

  if (isLoading) {
    return (
      <p role="status" aria-live="polite" className="text-muted-foreground">
        Cargando productos…
      </p>
    )
  }

  if (isError) {
    return (
      <div role="alert" className="flex flex-col items-start gap-3 text-danger">
        <p>No se pudieron cargar los productos.</p>
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
      <section aria-label="Productos" className={cardClass}>
        {products.length === 0 ? (
          <p className="text-sm text-muted-foreground">Aún no hay productos registrados.</p>
        ) : (
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="py-2 pr-4 font-medium">Nombre</th>
                <th className="py-2 pr-4 font-medium">Categoría</th>
                <th className="py-2 pr-4 font-medium">Unidad</th>
                <th className="py-2 font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {products.map((product) => (
                <tr key={product.id} className="border-b align-middle">
                  <td className="py-3 pr-4 font-medium text-foreground">{product.name}</td>
                  <td className="py-3 pr-4 text-muted-foreground">{product.category_name}</td>
                  <td className="py-3 pr-4 text-muted-foreground">{product.unit_of_measure_name}</td>
                  <td className="py-3">
                    {canManage ? (
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => {
                            setFieldErrors({})
                            setServerError(undefined)
                            setSelected(product)
                          }}
                          className="h-11 rounded-md border px-3 text-sm font-medium text-foreground hover:bg-muted"
                        >
                          Editar
                        </button>
                        <button
                          type="button"
                          onClick={() => remove(product.id, { onError })}
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
          <section aria-label="Editar producto" className={cardClass}>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-foreground">Editar producto</h2>
              <button
                type="button"
                onClick={() => setSelected(null)}
                className="h-11 rounded-md border px-3 text-sm font-medium text-foreground hover:bg-muted"
              >
                Cerrar
              </button>
            </div>
            <ProductForm
              product={selected}
              categories={categories}
              units={units}
              isPending={isPending}
              serverError={serverError}
              fieldErrors={fieldErrors}
              onSubmit={handleSubmit}
            />
          </section>
        ) : canCreate ? (
          <section aria-label="Nuevo producto" className={cardClass}>
            <h2 className="mb-4 text-lg font-semibold text-foreground">Nuevo producto</h2>
            <ProductForm
              categories={categories}
              units={units}
              isPending={isPending}
              serverError={serverError}
              fieldErrors={fieldErrors}
              onSubmit={handleSubmit}
            />
          </section>
        ) : null}
      </aside>
    </div>
  )
}
