import { type HttpError, useCustom, useCustomMutation, useInvalidate } from '@refinedev/core'
import { z } from 'zod'

import {
  type UnitOfMeasure,
  type UnitOfMeasureWriteInput,
  unitReadSchema,
} from '../types/products.types'

/*
  CRUD de unidades de medida (F5). Listado con useCustom (GET) y escrituras con useCustomMutation
  contra el dataProvider 'auth'. La respuesta del listado se valida contra el schema Zod generado
  antes de exponerla. El nombre duplicado (409) llega como HttpError.message.
*/

const listSchema = z.array(unitReadSchema)
const RESOURCE = 'units'
const BASE_URL = '/products/units'

interface MutationCallbacks {
  onSuccess?: () => void
  onError?: (error: HttpError) => void
}

export function useUnits() {
  const { query, result } = useCustom<UnitOfMeasure[]>({
    url: BASE_URL,
    method: 'get',
    dataProviderName: 'auth',
  })
  const { mutate, mutation } = useCustomMutation<Record<string, unknown>, HttpError>()
  const invalidate = useInvalidate()

  const refresh = () =>
    invalidate({ dataProviderName: 'auth', resource: RESOURCE, invalidates: ['all'] })

  const parsed = listSchema.safeParse(result.data ?? [])

  const create = (values: UnitOfMeasureWriteInput, callbacks?: MutationCallbacks): void => {
    mutate(
      {
        url: BASE_URL,
        method: 'post',
        values,
        dataProviderName: 'auth',
        successNotification: { type: 'success', message: 'Unidad creada.' },
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
    values: Partial<UnitOfMeasureWriteInput>,
    callbacks?: MutationCallbacks,
  ): void => {
    mutate(
      {
        url: `${BASE_URL}/${id}`,
        method: 'patch',
        values,
        dataProviderName: 'auth',
        successNotification: { type: 'success', message: 'Unidad actualizada.' },
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
        successNotification: { type: 'success', message: 'Unidad dada de baja.' },
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
    units: parsed.success ? parsed.data : [],
    isLoading: query.isLoading,
    isError: query.isError || !parsed.success,
    refetch: query.refetch,
    create,
    update,
    remove,
    isPending: mutation.isPending,
  }
}
