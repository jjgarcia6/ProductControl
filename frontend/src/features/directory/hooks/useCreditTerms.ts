import { type HttpError, useCustomMutation, useInvalidate } from '@refinedev/core'

import type { CreditTermsWriteInput } from '../types/directory.types'

/*
  Términos de crédito por faceta (F4). useCustomMutation contra el dataProvider 'auth'.
  Crear (POST) o editar (PATCH) por id. La integridad faceta↔rol (400) y la unicidad por
  (ficha, faceta) (409) las resuelve el backend; el error se mapea al campo de faceta.
*/

interface MutationCallbacks {
  onSuccess?: () => void
  onError?: (error: HttpError) => void
}

export function useCreditTerms() {
  const { mutate, mutation } = useCustomMutation<Record<string, unknown>, HttpError>()
  const invalidate = useInvalidate()

  const refresh = () =>
    invalidate({ dataProviderName: 'auth', resource: 'fichas', invalidates: ['all'] })

  const createTerms = (values: CreditTermsWriteInput, callbacks?: MutationCallbacks): void => {
    mutate(
      {
        url: '/credit/terms',
        method: 'post',
        values,
        dataProviderName: 'auth',
        successNotification: { type: 'success', message: 'Términos de crédito guardados.' },
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

  const updateTerms = (
    id: string,
    values: Partial<CreditTermsWriteInput>,
    callbacks?: MutationCallbacks,
  ): void => {
    mutate(
      {
        url: `/credit/terms/${id}`,
        method: 'patch',
        values,
        dataProviderName: 'auth',
        successNotification: { type: 'success', message: 'Términos de crédito actualizados.' },
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

  return { createTerms, updateTerms, isPending: mutation.isPending }
}
