import { type HttpError, useCustom, useCustomMutation, useInvalidate } from '@refinedev/core'
import { z } from 'zod'

import { type Product, type ProductWriteInput, productReadSchema } from '../types/products.types'

/*
  CRUD de productos (F5). Listado con useCustom (GET) y escrituras con useCustomMutation contra
  el dataProvider 'auth'. La respuesta del listado se valida contra el schema Zod generado antes
  de exponerla. Las FK inexistentes (400) llegan por campo; el nombre duplicado (409) como
  HttpError.message.
*/

const listSchema = z.array(productReadSchema)
const RESOURCE = 'products'
const BASE_URL = '/products/products'

interface MutationCallbacks {
  onSuccess?: () => void
  onError?: (error: HttpError) => void
}

export function useProducts() {
  const { query, result } = useCustom<Product[]>({
    url: BASE_URL,
    method: 'get',
    dataProviderName: 'auth',
  })
  const { mutate, mutation } = useCustomMutation<Record<string, unknown>, HttpError>()
  const invalidate = useInvalidate()

  const refresh = () =>
    invalidate({ dataProviderName: 'auth', resource: RESOURCE, invalidates: ['all'] })

  const parsed = listSchema.safeParse(result.data ?? [])

  const create = (values: ProductWriteInput, callbacks?: MutationCallbacks): void => {
    mutate(
      {
        url: BASE_URL,
        method: 'post',
        values,
        dataProviderName: 'auth',
        successNotification: { type: 'success', message: 'Producto creado.' },
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
    values: Partial<ProductWriteInput>,
    callbacks?: MutationCallbacks,
  ): void => {
    mutate(
      {
        url: `${BASE_URL}/${id}`,
        method: 'patch',
        values,
        dataProviderName: 'auth',
        successNotification: { type: 'success', message: 'Producto actualizado.' },
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
        successNotification: { type: 'success', message: 'Producto dado de baja.' },
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
    products: parsed.success ? parsed.data : [],
    isLoading: query.isLoading,
    isError: query.isError || !parsed.success,
    refetch: query.refetch,
    create,
    update,
    remove,
    isPending: mutation.isPending,
  }
}
