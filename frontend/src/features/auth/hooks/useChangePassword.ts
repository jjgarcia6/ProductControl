import { type HttpError, useCustomMutation } from '@refinedev/core'

import { changePasswordSchema, type ChangePasswordInput } from '../types/auth.types'

/*
  Cambio de la contraseña propia. Usa useCustomMutation de Refine contra el dataProvider
  'auth' (cliente con Authorization + refresh silencioso). Los errores 400 del backend
  llegan como HttpError.errors y el formulario los pinta por campo; el éxito dispara un
  aviso por el notificationProvider.
*/

interface ChangePasswordResponse extends Record<string, unknown> {
  detail: string
}

interface ChangePasswordCallbacks {
  onSuccess?: () => void
  onError?: (error: HttpError) => void
}

export function useChangePassword() {
  const { mutate, mutation } = useCustomMutation<
    ChangePasswordResponse,
    HttpError,
    ChangePasswordInput
  >()

  const changePassword = (
    values: ChangePasswordInput,
    callbacks?: ChangePasswordCallbacks,
  ): void => {
    // Valida la forma contra el schema generado antes de salir a la red.
    const payload = changePasswordSchema.parse(values)
    mutate(
      {
        url: '/auth/change-password',
        method: 'post',
        values: payload,
        dataProviderName: 'auth',
        successNotification: {
          type: 'success',
          message: 'Contraseña actualizada. Vuelva a iniciar sesión.',
        },
      },
      {
        onSuccess: () => callbacks?.onSuccess?.(),
        onError: (error) => callbacks?.onError?.(error),
      },
    )
  }

  return {
    changePassword,
    isPending: mutation.isPending,
    error: mutation.error,
  }
}
