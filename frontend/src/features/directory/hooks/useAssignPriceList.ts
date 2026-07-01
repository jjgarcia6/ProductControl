import { type HttpError, useCustomMutation, useInvalidate } from '@refinedev/core'

/*
  Asignación (o desasignación) de una lista de precios a una ficha de cliente (F6).
  useCustomMutation contra el dataProvider 'auth': PATCH /directory/fichas/{id}/assign-price-list.
  La integridad asignación↔rol cliente (400) llega por el campo `price_list`. Tras el éxito se
  invalida el listado de fichas.
*/

interface ActionCallbacks {
  onSuccess?: () => void
  onError?: (error: HttpError) => void
}

export function useAssignPriceList() {
  const { mutate, mutation } = useCustomMutation<Record<string, unknown>, HttpError>()
  const invalidate = useInvalidate()

  const assign = (
    fichaId: string,
    priceListId: string | null,
    callbacks?: ActionCallbacks,
  ): void => {
    mutate(
      {
        url: `/directory/fichas/${fichaId}/assign-price-list`,
        method: 'patch',
        values: { price_list: priceListId },
        dataProviderName: 'auth',
        successNotification: {
          type: 'success',
          message: priceListId ? 'Lista de precios asignada.' : 'Lista de precios desasignada.',
        },
      },
      {
        onSuccess: () => {
          void invalidate({ dataProviderName: 'auth', resource: 'fichas', invalidates: ['all'] })
          callbacks?.onSuccess?.()
        },
        onError: (error) => callbacks?.onError?.(error),
      },
    )
  }

  return { assign, isPending: mutation.isPending }
}
