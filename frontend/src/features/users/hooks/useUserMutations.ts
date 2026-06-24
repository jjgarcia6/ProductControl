import { type HttpError, useCustomMutation, useInvalidate } from '@refinedev/core'

import type { UserAdminWriteInput } from '../types/users.types'

/*
  Alta y edición de usuarios (F3). useCustomMutation contra el dataProvider 'auth'. Tras el
  éxito se invalida el listado. Los errores 400 (identificador duplicado / contraseña débil)
  llegan como HttpError.errors y el formulario los pinta por campo.
*/

interface MutationCallbacks {
  onSuccess?: () => void
  onError?: (error: HttpError) => void
}

export function useUserMutations() {
  const { mutate, mutation } = useCustomMutation<Record<string, unknown>, HttpError>()
  const invalidate = useInvalidate()

  const refresh = () =>
    invalidate({ dataProviderName: 'auth', resource: 'users', invalidates: ['all'] })

  const createUser = (values: UserAdminWriteInput, callbacks?: MutationCallbacks): void => {
    mutate(
      {
        url: '/auth/users',
        method: 'post',
        values,
        dataProviderName: 'auth',
        successNotification: { type: 'success', message: 'Usuario creado.' },
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

  const updateUser = (
    id: number,
    values: { first_name?: string; last_name?: string },
    callbacks?: MutationCallbacks,
  ): void => {
    mutate(
      {
        url: `/auth/users/${id}`,
        method: 'patch',
        values,
        dataProviderName: 'auth',
        successNotification: { type: 'success', message: 'Usuario actualizado.' },
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

  return { createUser, updateUser, isPending: mutation.isPending }
}
