import { type HttpError, useCustom, useCustomMutation, useInvalidate } from '@refinedev/core'
import { z } from 'zod'

import {
  type PriceListItem,
  type PriceListItemWriteInput,
  priceListItemReadSchema,
} from '../types/pricing.types'

/*
  Ítems de precio de una lista (F6). Listado con useCustom (GET) y escrituras con
  useCustomMutation contra el dataProvider 'auth'. La respuesta se valida contra el schema Zod
  generado antes de exponerla. El producto duplicado (409) llega como HttpError.message; el
  precio negativo (400) por campo `price`.
*/

const listSchema = z.array(priceListItemReadSchema)
const RESOURCE = 'price-list-items'

interface MutationCallbacks {
  onSuccess?: () => void
  onError?: (error: HttpError) => void
}

export function usePriceListItems(priceListId: string | undefined) {
  const { query, result } = useCustom<PriceListItem[]>({
    url: `/pricing/price-lists/${priceListId}/items`,
    method: 'get',
    dataProviderName: 'auth',
    queryOptions: { enabled: Boolean(priceListId) },
  })
  const { mutate, mutation } = useCustomMutation<Record<string, unknown>, HttpError>()
  const invalidate = useInvalidate()

  const refresh = () =>
    invalidate({ dataProviderName: 'auth', resource: RESOURCE, invalidates: ['all'] })

  const parsed = listSchema.safeParse(result.data ?? [])

  const addItem = (values: PriceListItemWriteInput, callbacks?: MutationCallbacks): void => {
    mutate(
      {
        url: `/pricing/price-lists/${priceListId}/items`,
        method: 'post',
        values,
        dataProviderName: 'auth',
        successNotification: { type: 'success', message: 'Precio agregado.' },
      },
      {
        onSuccess: () => {
          void refresh()
          void query.refetch()
          callbacks?.onSuccess?.()
        },
        onError: (error) => callbacks?.onError?.(error),
      },
    )
  }

  const updateItem = (
    itemId: string,
    values: Partial<PriceListItemWriteInput>,
    callbacks?: MutationCallbacks,
  ): void => {
    mutate(
      {
        url: `/pricing/price-list-items/${itemId}`,
        method: 'patch',
        values,
        dataProviderName: 'auth',
        successNotification: { type: 'success', message: 'Precio actualizado.' },
      },
      {
        onSuccess: () => {
          void refresh()
          void query.refetch()
          callbacks?.onSuccess?.()
        },
        onError: (error) => callbacks?.onError?.(error),
      },
    )
  }

  const removeItem = (itemId: string, callbacks?: MutationCallbacks): void => {
    mutate(
      {
        url: `/pricing/price-list-items/${itemId}`,
        method: 'delete',
        values: {},
        dataProviderName: 'auth',
        successNotification: { type: 'success', message: 'Precio quitado de la lista.' },
      },
      {
        onSuccess: () => {
          void refresh()
          void query.refetch()
          callbacks?.onSuccess?.()
        },
        onError: (error) => callbacks?.onError?.(error),
      },
    )
  }

  return {
    items: parsed.success ? parsed.data : [],
    isLoading: query.isLoading,
    isError: query.isError || !parsed.success,
    refetch: query.refetch,
    addItem,
    updateItem,
    removeItem,
    isPending: mutation.isPending,
  }
}
