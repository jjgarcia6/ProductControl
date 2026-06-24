import { type HttpError } from '@refinedev/core'
import { useState } from 'react'

import { usePermissions } from '@/features/auth'
import { useProfilesList } from '@/features/profiles'

import { useUserAdminActions } from '../hooks/useUserAdminActions'
import { useUserMutations } from '../hooks/useUserMutations'
import { useUsersList } from '../hooks/useUsersList'
import type { UserAdmin } from '../types/users.types'
import { ResetPasswordDialog } from './ResetPasswordDialog'
import { UserForm, type UserFormValues } from './UserForm'

/*
  Consola de administración de usuarios (F3). Contenedor: orquesta listado, alta y acciones
  de ciclo de vida (desactivar/reactivar, reset, cambio de perfil) + la lista de perfiles.
  Visible solo para quien su perfil autoriza (gating de F2). Estados vacío/carga/error/éxito.
  Tokens del theme; cero hex.
*/

const cardClass = 'rounded-lg border bg-surface p-5'
const SERVER_FIELDS: ReadonlyArray<keyof UserFormValues> = ['username', 'password', 'profile_id']

export function UsersAdminConsole() {
  const { canDo } = usePermissions()
  const { users, isLoading, isError, refetch } = useUsersList()
  const { profiles } = useProfilesList()
  const { createUser, isPending: isCreating } = useUserMutations()
  const { deactivate, reactivate, assignProfile, resetPassword, isPending } =
    useUserAdminActions()

  const [createErrors, setCreateErrors] = useState<Partial<Record<keyof UserFormValues, string>>>(
    {},
  )
  const [resetFor, setResetFor] = useState<UserAdmin | null>(null)
  const [tempPassword, setTempPassword] = useState<string | null>(null)
  const [resetError, setResetError] = useState<string | null>(null)

  const canManage = canDo('access-control', 'update')
  const canCreate = canDo('access-control', 'create')

  const onCreate = (values: UserFormValues) => {
    setCreateErrors({})
    createUser(values, {
      onError: (error: HttpError) => {
        const next: Partial<Record<keyof UserFormValues, string>> = {}
        for (const field of SERVER_FIELDS) {
          const messages = error.errors?.[field]
          if (messages) next[field] = Array.isArray(messages) ? messages[0] : String(messages)
        }
        setCreateErrors(next)
      },
    })
  }

  const openReset = (user: UserAdmin) => {
    setResetFor(user)
    setTempPassword(null)
    setResetError(null)
  }

  if (isLoading) {
    return (
      <p role="status" aria-live="polite" className="text-muted-foreground">
        Cargando usuarios…
      </p>
    )
  }

  if (isError) {
    return (
      <div role="alert" className="flex flex-col items-start gap-3 text-danger">
        <p>No se pudieron cargar los usuarios.</p>
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
    <div className="grid gap-6 lg:grid-cols-[1fr_22rem]">
      <section aria-label="Usuarios" className={cardClass}>
        {users.length === 0 ? (
          <p className="text-sm text-muted-foreground">No hay usuarios registrados.</p>
        ) : (
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="py-2 pr-4 font-medium">Usuario</th>
                <th className="py-2 pr-4 font-medium">Perfil</th>
                <th className="py-2 pr-4 font-medium">Estado</th>
                <th className="py-2 font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className="border-b align-middle">
                  <td className="py-3 pr-4">
                    <span className="font-medium text-foreground">{user.username}</span>
                    {user.first_name ? (
                      <span className="text-muted-foreground"> · {user.first_name}</span>
                    ) : null}
                  </td>
                  <td className="py-3 pr-4">
                    {canManage ? (
                      <select
                        aria-label={`Perfil de ${user.username}`}
                        value={user.profile?.id ?? ''}
                        disabled={isPending}
                        onChange={(event) => assignProfile(user.id, event.target.value)}
                        className="h-11 rounded-md border bg-surface px-2 text-sm text-foreground"
                      >
                        {profiles.map((profile) => (
                          <option key={profile.id} value={profile.id}>
                            {profile.name}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <span className="text-muted-foreground">{user.profile?.name ?? '—'}</span>
                    )}
                  </td>
                  <td className="py-3 pr-4">
                    <span className={user.is_active ? 'text-success' : 'text-muted-foreground'}>
                      {user.is_active ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                  <td className="py-3">
                    {canManage ? (
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => openReset(user)}
                          className="h-11 rounded-md border px-3 text-sm font-medium text-foreground hover:bg-muted"
                        >
                          Resetear
                        </button>
                        {user.is_active ? (
                          <button
                            type="button"
                            onClick={() => deactivate(user.id)}
                            disabled={isPending}
                            className="h-11 rounded-md border border-danger px-3 text-sm font-medium text-danger hover:bg-danger/10 disabled:opacity-60"
                          >
                            Desactivar
                          </button>
                        ) : (
                          <button
                            type="button"
                            onClick={() => reactivate(user.id)}
                            disabled={isPending}
                            className="h-11 rounded-md border px-3 text-sm font-medium text-foreground hover:bg-muted disabled:opacity-60"
                          >
                            Reactivar
                          </button>
                        )}
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
        {canCreate ? (
          <section aria-label="Nuevo usuario" className={cardClass}>
            <h2 className="mb-4 text-lg font-semibold text-foreground">Nuevo usuario</h2>
            <UserForm
              profiles={profiles}
              onSubmit={onCreate}
              isPending={isCreating}
              serverErrors={createErrors}
            />
          </section>
        ) : null}

        {resetFor ? (
          <section className={cardClass}>
            <ResetPasswordDialog
              username={resetFor.username}
              isPending={isPending}
              temporaryPassword={tempPassword}
              errorMessage={resetError}
              onClose={() => setResetFor(null)}
              onSubmit={(values) => {
                setResetError(null)
                resetPassword(resetFor.id, values, {
                  onSuccess: (temporary) => setTempPassword(temporary),
                  onError: (error) => setResetError(error.message),
                })
              }}
            />
          </section>
        ) : null}
      </aside>
    </div>
  )
}
