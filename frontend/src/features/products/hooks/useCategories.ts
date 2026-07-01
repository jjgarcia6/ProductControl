import { type HttpError, useCustom, useCustomMutation, useInvalidate } from '@refinedev/core'
import { z } from 'zod'

import { type Category, type CategoryWriteInput, categoryReadSchema } from '../types/products.types'

/*
  CRUD de categorías (F5). El listado usa useCustom (GET) y las escrituras useCustomMutation,
  ambos contra el dataProvider 'auth' (lleva el Authorization). La respuesta del listado se
  valida contra el schema Zod generado (Fase 0) antes de exponerla; si no coincide, se trata
  como error. La unicidad de nombre (409) llega como HttpError.message.
*/

const listSchema = z.array(categoryReadSchema)
const RESOURCE = 'categories'
const BASE_URL = '/products/categories'

interface MutationCallbacks {
  onSuccess?: () => void
  onError?: (error: HttpError) => void
}

export function useCategories() {
  const { query, result } = useCustom<Category[]>({
    url: BASE_URL,
    method: 'get',
    dataProviderName: 'auth',
  })
  const { mutate, mutation } = useCustomMutation<Record<string, unknown>, HttpError>()
  const invalidate = useInvalidate()

  const refresh = () =>
    invalidate({ dataProviderName: 'auth', resource: RESOURCE, invalidates: ['all'] })

  const parsed = listSchema.safeParse(result.data ?? [])

  const create = (values: CategoryWriteInput, callbacks?: MutationCallbacks): void => {
    mutate(
      {
        url: BASE_URL,
        method: 'post',
        values,
        dataProviderName: 'auth',
        successNotification: { type: 'success', message: 'Categoría creada.' },
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
    values: Partial<CategoryWriteInput>,
    callbacks?: MutationCallbacks,
  ): void => {
    mutate(
      {
        url: `${BASE_URL}/${id}`,
        method: 'patch',
        values,
        dataProviderName: 'auth',
        successNotification: { type: 'success', message: 'Categoría actualizada.' },
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
        successNotification: { type: 'success', message: 'Categoría dada de baja.' },
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
    categories: parsed.success ? parsed.data : [],
    isLoading: query.isLoading,
    isError: query.isError || !parsed.success,
    refetch: query.refetch,
    create,
    update,
    remove,
    isPending: mutation.isPending,
  }
}
