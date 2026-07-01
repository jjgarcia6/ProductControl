import { useState } from 'react'

import { usePermissions } from '@/features/auth'

import { useFichas } from '../hooks/useFichas'
import { useFichaStatus } from '../hooks/useFichaStatus'
import {
  ROLE_LABELS,
  STATUS_LABELS,
  type Ficha,
  type FichaRole,
  type FichaStatus,
} from '../types/directory.types'
import { FichaForm } from './FichaForm'
import { PriceListSelect } from './PriceListSelect'

/*
  Consola del Directorio (F4). Contenedor: orquesta el listado con filtros (rol/estado), las
  transiciones de estado y el alta/edición de fichas (con su sub-formulario de crédito).
  Gating por perfil (F2, módulo `directory`). Estados vacío/carga/error/éxito. Tokens del
  theme; cero hex.
*/

const cardClass = 'rounded-lg border bg-surface p-5'
const inputClass = 'h-11 rounded-md border bg-surface px-3 text-sm text-foreground'

const ROLES = Object.keys(ROLE_LABELS) as FichaRole[]
const STATUSES = Object.keys(STATUS_LABELS) as FichaStatus[]

export function DirectoryList() {
  const { canDo } = usePermissions()
  const canCreate = canDo('directory', 'create')
  const canManage = canDo('directory', 'update')

  const [role, setRole] = useState('')
  const [status, setStatus] = useState('')
  const [includeInactive, setIncludeInactive] = useState(false)
  const [selected, setSelected] = useState<Ficha | null>(null)

  const { fichas, isLoading, isError, refetch } = useFichas({
    role: role || undefined,
    status: status || undefined,
    includeInactive,
  })
  const { changeStatus, isPending } = useFichaStatus()

  const renderStatusActions = (ficha: Ficha) => {
    if (!canManage) return <span className="text-muted-foreground">—</span>
    return (
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setSelected(ficha)}
          className="h-11 rounded-md border px-3 text-sm font-medium text-foreground hover:bg-muted"
        >
          Editar
        </button>
        {ficha.status === 'ACTIVO' ? (
          <button
            type="button"
            onClick={() => changeStatus(ficha.id, 'block')}
            disabled={isPending}
            className="h-11 rounded-md border px-3 text-sm font-medium text-foreground hover:bg-muted disabled:opacity-60"
          >
            Bloquear
          </button>
        ) : null}
        {ficha.status === 'BLOQUEADO' ? (
          <button
            type="button"
            onClick={() => changeStatus(ficha.id, 'unblock')}
            disabled={isPending}
            className="h-11 rounded-md border px-3 text-sm font-medium text-foreground hover:bg-muted disabled:opacity-60"
          >
            Desbloquear
          </button>
        ) : null}
        {ficha.status === 'INACTIVO' ? (
          <button
            type="button"
            onClick={() => changeStatus(ficha.id, 'reactivate')}
            disabled={isPending}
            className="h-11 rounded-md border px-3 text-sm font-medium text-foreground hover:bg-muted disabled:opacity-60"
          >
            Reactivar
          </button>
        ) : (
          <button
            type="button"
            onClick={() => changeStatus(ficha.id, 'deactivate')}
            disabled={isPending}
            className="h-11 rounded-md border border-danger px-3 text-sm font-medium text-danger hover:bg-danger/10 disabled:opacity-60"
          >
            Dar de baja
          </button>
        )}
      </div>
    )
  }

  if (isLoading) {
    return (
      <p role="status" aria-live="polite" className="text-muted-foreground">
        Cargando directorio…
      </p>
    )
  }

  if (isError) {
    return (
      <div role="alert" className="flex flex-col items-start gap-3 text-danger">
        <p>No se pudo cargar el directorio.</p>
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
      <section aria-label="Fichas" className={cardClass}>
        <div className="mb-4 flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-sm text-muted-foreground">
            Rol
            <select
              aria-label="Filtrar por rol"
              value={role}
              onChange={(event) => setRole(event.target.value)}
              className={inputClass}
            >
              <option value="">Todos</option>
              {ROLES.map((value) => (
                <option key={value} value={value}>
                  {ROLE_LABELS[value]}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm text-muted-foreground">
            Estado
            <select
              aria-label="Filtrar por estado"
              value={status}
              onChange={(event) => setStatus(event.target.value)}
              className={inputClass}
            >
              <option value="">Todos (activos)</option>
              {STATUSES.map((value) => (
                <option key={value} value={value}>
                  {STATUS_LABELS[value]}
                </option>
              ))}
            </select>
          </label>
          <label className="flex h-11 items-center gap-2 text-sm text-foreground">
            <input
              type="checkbox"
              checked={includeInactive}
              onChange={(event) => setIncludeInactive(event.target.checked)}
              className="size-4"
            />
            Incluir inactivas
          </label>
        </div>

        {fichas.length === 0 ? (
          <p className="text-sm text-muted-foreground">No hay fichas que coincidan con el filtro.</p>
        ) : (
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="py-2 pr-4 font-medium">Nombre</th>
                <th className="py-2 pr-4 font-medium">Identificación</th>
                <th className="py-2 pr-4 font-medium">Roles</th>
                <th className="py-2 pr-4 font-medium">Estado</th>
                <th className="py-2 font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {fichas.map((ficha) => (
                <tr key={ficha.id} className="border-b align-middle">
                  <td className="py-3 pr-4 font-medium text-foreground">{ficha.name}</td>
                  <td className="py-3 pr-4 text-muted-foreground">{ficha.identification_number}</td>
                  <td className="py-3 pr-4 text-muted-foreground">
                    {ficha.roles.map((value) => ROLE_LABELS[value]).join(', ')}
                  </td>
                  <td className="py-3 pr-4">
                    <span
                      className={
                        ficha.status === 'ACTIVO'
                          ? 'text-success'
                          : ficha.status === 'BLOQUEADO'
                            ? 'text-warning'
                            : 'text-muted-foreground'
                      }
                    >
                      {STATUS_LABELS[ficha.status]}
                    </span>
                  </td>
                  <td className="py-3">{renderStatusActions(ficha)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <aside className="flex flex-col gap-6">
        {selected ? (
          <section aria-label="Editar ficha" className={cardClass}>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-foreground">Editar ficha</h2>
              <button
                type="button"
                onClick={() => setSelected(null)}
                className="h-11 rounded-md border px-3 text-sm font-medium text-foreground hover:bg-muted"
              >
                Cerrar
              </button>
            </div>
            <FichaForm ficha={selected} onSaved={() => setSelected(null)} />
            {selected.roles.includes('CLIENTE') ? (
              <div className="mt-5 border-t pt-5">
                <PriceListSelect ficha={selected} />
              </div>
            ) : null}
          </section>
        ) : canCreate ? (
          <section aria-label="Nueva ficha" className={cardClass}>
            <h2 className="mb-4 text-lg font-semibold text-foreground">Nueva ficha</h2>
            <FichaForm />
          </section>
        ) : null}
      </aside>
    </div>
  )
}
