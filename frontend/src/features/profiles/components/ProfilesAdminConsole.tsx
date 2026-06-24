import { type HttpError } from '@refinedev/core'
import { useState } from 'react'

import { usePermissions } from '@/features/auth'

import { useProfileAdminActions } from '../hooks/useProfileAdminActions'
import { useProfilesList } from '../hooks/useProfilesList'
import {
  PERMISSION_CATALOG,
  type Profile,
  type ProfileAdminWriteInput,
} from '../types/profiles.types'
import { PermissionMatrix } from './PermissionMatrix'

/*
  Consola de administración de perfiles (F3). Contenedor: orquesta los hooks (listado +
  acciones) y la matriz presentacional. Visible solo para quien su perfil autoriza a
  administrar el control de acceso (gating de F2); la autorización real es del backend.
  Cubre estados vacío/carga/error/éxito. Tokens del theme; cero hex.
*/

const cardClass = 'rounded-lg border bg-surface p-5'

export function ProfilesAdminConsole() {
  const { canDo } = usePermissions()
  const { profiles, isLoading, isError, refetch } = useProfilesList()
  const { editPermissions, deactivate, isPending } = useProfileAdminActions()

  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [draft, setDraft] = useState<Record<string, string[]>>({})
  const [actionError, setActionError] = useState<string | null>(null)

  const canManage = canDo('access-control', 'update')
  const selected = profiles.find((profile) => profile.id === selectedId) ?? null

  const select = (profile: Profile) => {
    setSelectedId(profile.id)
    setDraft({ ...(profile.permissions as Record<string, string[]>) })
    setActionError(null)
  }

  const onError = (error: HttpError) => setActionError(error.message)

  const save = () => {
    if (!selected) return
    setActionError(null)
    const values = { permissions: draft } as ProfileAdminWriteInput
    editPermissions(selected.id, values, { onError })
  }

  const remove = () => {
    if (!selected) return
    setActionError(null)
    deactivate(selected.id, {
      onSuccess: () => {
        setSelectedId(null)
        setDraft({})
      },
      onError,
    })
  }

  if (isLoading) {
    return (
      <p role="status" aria-live="polite" className="text-muted-foreground">
        Cargando perfiles…
      </p>
    )
  }

  if (isError) {
    return (
      <div role="alert" className="flex flex-col items-start gap-3 text-danger">
        <p>No se pudieron cargar los perfiles.</p>
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
    <div className="grid gap-6 md:grid-cols-[18rem_1fr]">
      <section aria-label="Perfiles" className={cardClass}>
        {profiles.length === 0 ? (
          <p className="text-sm text-muted-foreground">No hay perfiles registrados.</p>
        ) : (
          <ul className="flex flex-col gap-1">
            {profiles.map((profile) => (
              <li key={profile.id}>
                <button
                  type="button"
                  onClick={() => select(profile)}
                  aria-current={profile.id === selectedId}
                  className={`flex min-h-11 w-full items-center rounded-md px-3 text-left text-sm transition-colors ${
                    profile.id === selectedId
                      ? 'bg-primary/10 font-medium text-foreground'
                      : 'text-muted-foreground hover:bg-muted'
                  }`}
                >
                  {profile.name}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-label="Detalle del perfil" className={cardClass}>
        {!selected ? (
          <p className="text-sm text-muted-foreground">
            Seleccione un perfil para ver y editar sus permisos.
          </p>
        ) : (
          <div className="flex flex-col gap-5">
            <header className="flex flex-col gap-1">
              <h2 className="text-lg font-semibold text-foreground">{selected.name}</h2>
              {selected.description ? (
                <p className="text-sm text-muted-foreground">{selected.description}</p>
              ) : null}
            </header>

            <PermissionMatrix
              catalog={PERMISSION_CATALOG}
              value={draft}
              onChange={setDraft}
              disabled={!canManage || isPending}
            />

            {actionError ? (
              <p role="alert" className="text-sm text-danger">
                {actionError}
              </p>
            ) : null}

            {canManage ? (
              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={save}
                  disabled={isPending}
                  className="h-11 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-60"
                >
                  {isPending ? 'Guardando…' : 'Guardar permisos'}
                </button>
                <button
                  type="button"
                  onClick={remove}
                  disabled={isPending}
                  className="h-11 rounded-md border border-danger px-4 text-sm font-medium text-danger hover:bg-danger/10 disabled:opacity-60"
                >
                  Dar de baja
                </button>
              </div>
            ) : null}
          </div>
        )}
      </section>
    </div>
  )
}
