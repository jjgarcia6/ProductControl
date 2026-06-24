import { type HttpError, useCustomMutation, useInvalidate } from '@refinedev/core'

import type { ProfileAdminWriteInput } from '../types/profiles.types'

/*
  Acciones de administración de perfiles (F3): editar permisos (PATCH) y dar de baja
  (DELETE). useCustomMutation contra el dataProvider 'auth'. Tras cada éxito se invalida
  el listado para que la consola se refresque. Los errores (400 catálogo / 409 en uso /
  403) llegan como HttpError y los pinta quien llama.
*/

interface ActionCallbacks {
  onSuccess?: () => void
  onError?: (error: HttpError) => void
}

export function useProfileAdminActions() {
  const { mutate, mutation } = useCustomMutation<Record<string, unknown>, HttpError>()
  const invalidate = useInvalidate()

  const refresh = () =>
    invalidate({ dataProviderName: 'auth', resource: 'profiles', invalidates: ['all'] })

  const editPermissions = (
    id: string,
    values: ProfileAdminWriteInput,
    callbacks?: ActionCallbacks,
  ): void => {
    mutate(
      {
        url: `/authz/profiles/${id}`,
        method: 'patch',
        values,
        dataProviderName: 'auth',
        successNotification: { type: 'success', message: 'Perfil actualizado.' },
      },
      {
        onSuccess: () => {
          void refresh()
          callbacks?.onSuccess?.()
        },
        onError: (error) => callbacks?.onError?.(error),
      },
    )
  }

  const deactivate = (id: string, callbacks?: ActionCallbacks): void => {
    mutate(
      {
        url: `/authz/profiles/${id}`,
        method: 'delete',
        values: {},
        dataProviderName: 'auth',
        successNotification: { type: 'success', message: 'Perfil dado de baja.' },
      },
      {
        onSuccess: () => {
          void refresh()
          callbacks?.onSuccess?.()
        },
        onError: (error) => callbacks?.onError?.(error),
      },
    )
  }

  return { editPermissions, deactivate, isPending: mutation.isPending }
}
