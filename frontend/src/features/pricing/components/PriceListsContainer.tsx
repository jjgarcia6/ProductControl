import { type HttpError } from '@refinedev/core'
import { useState } from 'react'

import { usePermissions } from '@/features/auth'
import { useProducts } from '@/features/products'

import { usePriceListItems } from '../hooks/usePriceListItems'
import { usePriceLists } from '../hooks/usePriceLists'
import {
  PRICE_LIST_TYPE_LABELS,
  type PriceList,
  type PriceListItemWriteInput,
  type PriceListWriteInput,
} from '../types/pricing.types'
import { PriceItemsGrid } from './PriceItemsGrid'
import { PriceListForm } from './PriceListForm'

/*
  Consola de listas de precios (F6). Contenedor: orquesta el listado de listas, el alta/edición/
  baja y la grilla de precios de la lista seleccionada. Gating por perfil (F2, módulo `pricing`).
  Estados vacío/carga/error/éxito. Tokens del theme; cero hex.
*/

const cardClass = 'rounded-lg border bg-surface p-5'

type ListFieldErrors = Partial<Record<'name' | 'type', string>>
type ItemFieldErrors = Partial<Record<'product' | 'price', string>>

function toListErrors(error: HttpError): { fields: ListFieldErrors; general?: string } {
  const fields: ListFieldErrors = {}
  for (const key of ['name', 'type'] as const) {
    const messages = error.errors?.[key]
    if (messages) fields[key] = Array.isArray(messages) ? messages[0] : String(messages)
  }
  const general = Object.keys(fields).length === 0 ? error.message : undefined
  return { fields, general }
}

function toItemErrors(error: HttpError): { fields: ItemFieldErrors; general?: string } {
  const fields: ItemFieldErrors = {}
  for (const key of ['product', 'price'] as const) {
    const messages = error.errors?.[key]
    if (messages) fields[key] = Array.isArray(messages) ? messages[0] : String(messages)
  }
  const general = Object.keys(fields).length === 0 ? error.message : undefined
  return { fields, general }
}

export function PriceListsContainer() {
  const { canDo } = usePermissions()
  const canCreate = canDo('pricing', 'create')
  const canManage = canDo('pricing', 'update')

  const { priceLists, isLoading, isError, refetch, create, update, remove, isPending } =
    usePriceLists()
  const { products } = useProducts()

  const [selected, setSelected] = useState<PriceList | null>(null)
  const [editing, setEditing] = useState<PriceList | null>(null)
  const [listErrors, setListErrors] = useState<ListFieldErrors>({})
  const [listServerError, setListServerError] = useState<string | undefined>(undefined)
  const [itemErrors, setItemErrors] = useState<ItemFieldErrors>({})
  const [itemServerError, setItemServerError] = useState<string | undefined>(undefined)

  const {
    items,
    addItem,
    removeItem,
    isPending: itemPending,
  } = usePriceListItems(selected?.id)

  const onListError = (error: HttpError) => {
    const { fields, general } = toListErrors(error)
    setListErrors(fields)
    setListServerError(general)
  }

  const handleListSubmit = (values: PriceListWriteInput) => {
    setListErrors({})
    setListServerError(undefined)
    const callbacks = { onSuccess: () => setEditing(null), onError: onListError }
    if (editing) update(editing.id, values, callbacks)
    else create(values, callbacks)
  }

  const handleAddItem = (values: PriceListItemWriteInput) => {
    setItemErrors({})
    setItemServerError(undefined)
    addItem(values, {
      onError: (error) => {
        const { fields, general } = toItemErrors(error)
        setItemErrors(fields)
        setItemServerError(general)
      },
    })
  }

  if (isLoading) {
    return (
      <p role="status" aria-live="polite" className="text-muted-foreground">
        Cargando listas de precios…
      </p>
    )
  }

  if (isError) {
    return (
      <div role="alert" className="flex flex-col items-start gap-3 text-danger">
        <p>No se pudieron cargar las listas de precios.</p>
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
      <section aria-label="Listas de precios" className={cardClass}>
        {priceLists.length === 0 ? (
          <p className="text-sm text-muted-foreground">Aún no hay listas de precios.</p>
        ) : (
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="py-2 pr-4 font-medium">Nombre</th>
                <th className="py-2 pr-4 font-medium">Tipo</th>
                <th className="py-2 font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {priceLists.map((priceList) => (
                <tr key={priceList.id} className="border-b align-middle">
                  <td className="py-3 pr-4 font-medium text-foreground">{priceList.name}</td>
                  <td className="py-3 pr-4 text-muted-foreground">
                    {PRICE_LIST_TYPE_LABELS[priceList.type]}
                  </td>
                  <td className="py-3">
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          setItemErrors({})
                          setItemServerError(undefined)
                          setSelected(priceList)
                        }}
                        className="h-11 rounded-md border px-3 text-sm font-medium text-foreground hover:bg-muted"
                      >
                        Ver precios
                      </button>
                      {canManage ? (
                        <>
                          <button
                            type="button"
                            onClick={() => {
                              setListErrors({})
                              setListServerError(undefined)
                              setEditing(priceList)
                            }}
                            className="h-11 rounded-md border px-3 text-sm font-medium text-foreground hover:bg-muted"
                          >
                            Editar
                          </button>
                          <button
                            type="button"
                            onClick={() => remove(priceList.id, { onError: onListError })}
                            disabled={isPending}
                            className="h-11 rounded-md border border-danger px-3 text-sm font-medium text-danger hover:bg-danger/10 disabled:opacity-60"
                          >
                            Dar de baja
                          </button>
                        </>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {listServerError ? (
          <p role="alert" className="mt-4 text-sm text-danger">
            {listServerError}
          </p>
        ) : null}
      </section>

      <aside className="flex flex-col gap-6">
        {editing ? (
          <section aria-label="Editar lista" className={cardClass}>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-foreground">Editar lista</h2>
              <button
                type="button"
                onClick={() => setEditing(null)}
                className="h-11 rounded-md border px-3 text-sm font-medium text-foreground hover:bg-muted"
              >
                Cerrar
              </button>
            </div>
            <PriceListForm
              priceList={editing}
              isPending={isPending}
              serverError={listServerError}
              fieldErrors={listErrors}
              onSubmit={handleListSubmit}
            />
          </section>
        ) : canCreate ? (
          <section aria-label="Nueva lista" className={cardClass}>
            <h2 className="mb-4 text-lg font-semibold text-foreground">Nueva lista</h2>
            <PriceListForm
              isPending={isPending}
              serverError={listServerError}
              fieldErrors={listErrors}
              onSubmit={handleListSubmit}
            />
          </section>
        ) : null}

        {selected ? (
          <section aria-label={`Precios de ${selected.name}`} className={cardClass}>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-foreground">Precios · {selected.name}</h2>
              <button
                type="button"
                onClick={() => setSelected(null)}
                className="h-11 rounded-md border px-3 text-sm font-medium text-foreground hover:bg-muted"
              >
                Cerrar
              </button>
            </div>
            {canManage ? (
              <PriceItemsGrid
                items={items}
                products={products}
                isPending={itemPending}
                serverError={itemServerError}
                fieldErrors={itemErrors}
                onAdd={handleAddItem}
                onRemove={(itemId) => removeItem(itemId)}
              />
            ) : items.length === 0 ? (
              <p className="text-sm text-muted-foreground">Esta lista aún no tiene precios.</p>
            ) : (
              <ul className="flex flex-col gap-2 text-sm">
                {items.map((item) => (
                  <li key={item.id} className="flex justify-between border-b py-2">
                    <span className="text-foreground">{item.product_name}</span>
                    <span className="text-muted-foreground">{item.price}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        ) : null}
      </aside>
    </div>
  )
}
