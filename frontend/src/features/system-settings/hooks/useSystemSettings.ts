import { type HttpError, useCustom, useCustomMutation, useInvalidate } from '@refinedev/core'

import {
  type SystemSettingsType,
  type SystemSettingsUpdateInput,
  systemSettingsReadSchema,
} from '../types/system-settings.types'

/*
  Lectura y edición del singleton de configuración global (F8). Al no tener `id`, se usa
  useCustom (GET) + useCustomMutation (PATCH) contra el dataProvider 'auth'. La respuesta
  del GET se valida contra el schema Zod generado antes de exponerla. El error cruzado
  "al menos una base activa" (400 non_field_errors) llega como HttpError.
*/

const RESOURCE = 'system-settings'
const BASE_URL = '/system-settings/'

interface MutationCallbacks {
  onSuccess?: () => void
  onError?: (error: HttpError) => void
}

export function useSystemSettings() {
  const { query, result } = useCustom<SystemSettingsType>({
    url: BASE_URL,
    method: 'get',
    dataProviderName: 'auth',
  })
  const { mutate, mutation } = useCustomMutation<Record<string, unknown>, HttpError>()
  const invalidate = useInvalidate()

  const refresh = () =>
    invalidate({ dataProviderName: 'auth', resource: RESOURCE, invalidates: ['all'] })

  const parsed = systemSettingsReadSchema.safeParse(result.data)

  const update = (values: SystemSettingsUpdateInput, callbacks?: MutationCallbacks): void => {
    mutate(
      {
        url: BASE_URL,
        method: 'patch',
        values,
        dataProviderName: 'auth',
        successNotification: { type: 'success', message: 'Configuración actualizada.' },
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
    settings: parsed.success ? parsed.data : undefined,
    isLoading: query.isLoading,
    isError: query.isError || (result.data !== undefined && !parsed.success),
    refetch: query.refetch,
    update,
    isPending: mutation.isPending,
  }
}
