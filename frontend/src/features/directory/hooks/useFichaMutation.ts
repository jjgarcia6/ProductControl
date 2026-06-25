import { type HttpError, useCustomMutation, useInvalidate } from '@refinedev/core'

import type { FichaWriteInput } from '../types/directory.types'

/*
  Alta y edición de fichas (F4). useCustomMutation contra el dataProvider 'auth'. Tras el
  éxito se invalida el listado. Los errores 400 (dígito verificador, roles, email) llegan
  como HttpError.errors y el formulario los pinta por campo; el 409 (número duplicado) llega
  como HttpError.message.
*/

interface MutationCallbacks {
  onSuccess?: () => void
  onError?: (error: HttpError) => void
}

export function useFichaMutation() {
  const { mutate, mutation } = useCustomMutation<Record<string, unknown>, HttpError>()
  const invalidate = useInvalidate()

  const refresh = () =>
    invalidate({ dataProviderName: 'auth', resource: 'fichas', invalidates: ['all'] })

  const createFicha = (values: FichaWriteInput, callbacks?: MutationCallbacks): void => {
    mutate(
      {
        url: '/directory/fichas',
        method: 'post',
        values,
        dataProviderName: 'auth',
        successNotification: { type: 'success', message: 'Ficha creada.' },
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

  const updateFicha = (
    id: string,
    values: Partial<FichaWriteInput>,
    callbacks?: MutationCallbacks,
  ): void => {
    mutate(
      {
        url: `/directory/fichas/${id}`,
        method: 'patch',
        values,
        dataProviderName: 'auth',
        successNotification: { type: 'success', message: 'Ficha actualizada.' },
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

  return { createFicha, updateFicha, isPending: mutation.isPending }
}
