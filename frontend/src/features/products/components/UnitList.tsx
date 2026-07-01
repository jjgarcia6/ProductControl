import { type HttpError } from '@refinedev/core'
import { useState } from 'react'

import { usePermissions } from '@/features/auth'

import { useUnits } from '../hooks/useUnits'
import { type UnitOfMeasure, type UnitOfMeasureWriteInput } from '../types/products.types'
import { UnitForm } from './UnitForm'

/*
  Consola de unidades de medida (F5). Contenedor: orquesta el listado y el alta/edición/baja.
  Gating por perfil (F2, módulo `products`). Estados vacío/carga/error/éxito. Tokens del theme.
*/

const cardClass = 'rounded-lg border bg-surface p-5'

export function UnitList() {
  const { canDo } = usePermissions()
  const canCreate = canDo('products', 'create')
  const canManage = canDo('products', 'update')

  const { units, isLoading, isError, refetch, create, update, remove, isPending } = useUnits()
  const [selected, setSelected] = useState<UnitOfMeasure | null>(null)
  const [serverError, setServerError] = useState<string | undefined>(undefined)

  const onError = (error: HttpError) => setServerError(error.message)

  const handleSubmit = (values: UnitOfMeasureWriteInput) => {
    setServerError(undefined)
    const callbacks = { onSuccess: () => setSelected(null), onError }
    if (selected) update(selected.id, values, callbacks)
    else create(values, callbacks)
  }

  if (isLoading) {
    return (
      <p role="status" aria-live="polite" className="text-muted-foreground">
        Cargando unidades…
      </p>
    )
  }

  if (isError) {
    return (
      <div role="alert" className="flex flex-col items-start gap-3 text-danger">
        <p>No se pudieron cargar las unidades.</p>
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
      <section aria-label="Unidades de medida" className={cardClass}>
        {units.length === 0 ? (
          <p className="text-sm text-muted-foreground">Aún no hay unidades registradas.</p>
        ) : (
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="py-2 pr-4 font-medium">Nombre</th>
                <th className="py-2 pr-4 font-medium">Símbolo</th>
                <th className="py-2 pr-4 font-medium">Factor (lb)</th>
                <th className="py-2 font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {units.map((unit) => (
                <tr key={unit.id} className="border-b align-middle">
                  <td className="py-3 pr-4 font-medium text-foreground">{unit.name}</td>
                  <td className="py-3 pr-4 text-muted-foreground">{unit.symbol}</td>
                  <td className="py-3 pr-4 text-muted-foreground">{unit.conversion_factor}</td>
                  <td className="py-3">
                    {canManage ? (
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => {
                            setServerError(undefined)
                            setSelected(unit)
                          }}
                          className="h-11 rounded-md border px-3 text-sm font-medium text-foreground hover:bg-muted"
                        >
                          Editar
                        </button>
                        <button
                          type="button"
                          onClick={() => remove(unit.id, { onError })}
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
          <section aria-label="Editar unidad" className={cardClass}>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-foreground">Editar unidad</h2>
              <button
                type="button"
                onClick={() => setSelected(null)}
                className="h-11 rounded-md border px-3 text-sm font-medium text-foreground hover:bg-muted"
              >
                Cerrar
              </button>
            </div>
            <UnitForm unit={selected} isPending={isPending} serverError={serverError} onSubmit={handleSubmit} />
          </section>
        ) : canCreate ? (
          <section aria-label="Nueva unidad" className={cardClass}>
            <h2 className="mb-4 text-lg font-semibold text-foreground">Nueva unidad</h2>
            <UnitForm isPending={isPending} serverError={serverError} onSubmit={handleSubmit} />
          </section>
        ) : null}
      </aside>
    </div>
  )
}
