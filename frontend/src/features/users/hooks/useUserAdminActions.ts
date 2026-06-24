import { type HttpError, useCustomMutation, useInvalidate } from '@refinedev/core'

import { type ResetPasswordInput, resetPasswordReadSchema } from '../types/users.types'

/*
  Acciones de ciclo de vida del usuario (F3): desactivar/reactivar, reset administrativo y
  asignación de perfil (endpoint de F2, extendido). useCustomMutation contra el dataProvider
  'auth'. El reset devuelve la contraseña temporal una sola vez (se valida con el schema
  generado). Tras cada éxito se invalida el listado.
*/

interface ActionCallbacks {
  onSuccess?: () => void
  onError?: (error: HttpError) => void
}

interface ResetCallbacks {
  onSuccess?: (temporaryPassword: string) => void
  onError?: (error: HttpError) => void
}

export function useUserAdminActions() {
  const { mutate, mutation } = useCustomMutation<Record<string, unknown>, HttpError>()
  const invalidate = useInvalidate()

  const refresh = () =>
    invalidate({ dataProviderName: 'auth', resource: 'users', invalidates: ['all'] })

  const post = (
    url: string,
    values: Record<string, unknown>,
    message: string,
    callbacks: ActionCallbacks | undefined,
    onData?: (data: Record<string, unknown>) => void,
  ): void => {
    mutate(
      {
        url,
        method: 'post',
        values,
        dataProviderName: 'auth',
        successNotification: { type: 'success', message },
      },
      {
        onSuccess: (response) => {
          void refresh()
          onData?.(response.data)
          callbacks?.onSuccess?.()
        },
        onError: (error) => callbacks?.onError?.(error),
      },
    )
  }

  const deactivate = (id: number, callbacks?: ActionCallbacks) =>
    post(`/auth/users/${id}/deactivate`, {}, 'Usuario desactivado.', callbacks)

  const reactivate = (id: number, callbacks?: ActionCallbacks) =>
    post(`/auth/users/${id}/reactivate`, {}, 'Usuario reactivado.', callbacks)

  const assignProfile = (id: number, profileId: string, callbacks?: ActionCallbacks) =>
    post(`/authz/users/${id}/assign-profile`, { profile_id: profileId }, 'Perfil asignado.', callbacks)

  const resetPassword = (id: number, values: ResetPasswordInput, callbacks?: ResetCallbacks): void => {
    post(
      `/auth/users/${id}/reset-password`,
      values as Record<string, unknown>,
      'Contraseña restablecida.',
      { onError: callbacks?.onError },
      (data) => {
        const { temporary_password } = resetPasswordReadSchema.parse(data)
        callbacks?.onSuccess?.(temporary_password)
      },
    )
  }

  return { deactivate, reactivate, assignProfile, resetPassword, isPending: mutation.isPending }
}
