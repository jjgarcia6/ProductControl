import { type HttpError, useCustom, useCustomMutation, useInvalidate } from '@refinedev/core'
import { z } from 'zod'

import {
  type PriceList,
  type PriceListWriteInput,
  priceListReadSchema,
} from '../types/pricing.types'

/*
  CRUD de listas de precios (F6). Listado con useCustom (GET) y escrituras con useCustomMutation
  contra el dataProvider 'auth'. La respuesta del listado se valida contra el schema Zod generado
  antes de exponerla. El nombre duplicado y la baja bloqueada por uso (409) llegan como
  HttpError.message.
*/

const listSchema = z.array(priceListReadSchema)
const RESOURCE = 'price-lists'
const BASE_URL = '/pricing/price-lists'

interface MutationCallbacks {
  onSuccess?: () => void
  onError?: (error: HttpError) => void
}

export function usePriceLists() {
  const { query, result } = useCustom<PriceList[]>({
    url: BASE_URL,
    method: 'get',
    dataProviderName: 'auth',
  })
  const { mutate, mutation } = useCustomMutation<Record<string, unknown>, HttpError>()
  const invalidate = useInvalidate()

  const refresh = () =>
    invalidate({ dataProviderName: 'auth', resource: RESOURCE, invalidates: ['all'] })

  const parsed = listSchema.safeParse(result.data ?? [])

  const create = (values: PriceListWriteInput, callbacks?: MutationCallbacks): void => {
    mutate(
      {
        url: BASE_URL,
        method: 'post',
        values,
        dataProviderName: 'auth',
        successNotification: { type: 'success', message: 'Lista de precios creada.' },
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

  const update = (
    id: string,
    values: Partial<PriceListWriteInput>,
    callbacks?: MutationCallbacks,
  ): void => {
    mutate(
      {
        url: `${BASE_URL}/${id}`,
        method: 'patch',
        values,
        dataProviderName: 'auth',
        successNotification: { type: 'success', message: 'Lista de precios actualizada.' },
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

  const remove = (id: string, callbacks?: MutationCallbacks): void => {
    mutate(
      {
        url: `${BASE_URL}/${id}`,
        method: 'delete',
        values: {},
        dataProviderName: 'auth',
        successNotification: { type: 'success', message: 'Lista de precios dada de baja.' },
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

  return {
    priceLists: parsed.success ? parsed.data : [],
    isLoading: query.isLoading,
    isError: query.isError || !parsed.success,
    refetch: query.refetch,
    create,
    update,
    remove,
    isPending: mutation.isPending,
  }
}
