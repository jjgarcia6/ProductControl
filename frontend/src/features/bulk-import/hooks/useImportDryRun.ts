import { type HttpError, useCustomMutation } from '@refinedev/core'

import {
  type ImportEntity,
  type ImportResultType,
  importResultSchema,
} from '../types/import.types'

/*
  Previsualización (dry-run) de una importación (F7). Sube el archivo con useCustomMutation
  (dataProvider 'auth', sin TanStack paralelo) a `POST /bulk-import/{entity}?dry_run=true`.
  El backend responde 200 con el reporte por fila aunque haya filas en error. La respuesta se
  valida contra el schema Zod GENERADO antes de exponerla (defensa de contrato).
*/

const INVALID_RESPONSE: HttpError = {
  message: 'La respuesta del servidor no tiene el formato esperado.',
  statusCode: 500,
}

interface Callbacks {
  onSuccess?: (result: ImportResultType) => void
  onError?: (error: HttpError) => void
}

export function useImportDryRun() {
  const { mutate, mutation } = useCustomMutation<ImportResultType, HttpError, FormData>()

  const preview = (entity: ImportEntity, file: File, callbacks?: Callbacks): void => {
    const values = new FormData()
    values.append('file', file)
    mutate(
      {
        url: `/bulk-import/${entity}?dry_run=true`,
        method: 'post',
        values,
        dataProviderName: 'auth',
      },
      {
        onSuccess: (response) => {
          const parsed = importResultSchema.safeParse(response.data)
          if (!parsed.success) {
            callbacks?.onError?.(INVALID_RESPONSE)
            return
          }
          callbacks?.onSuccess?.(parsed.data as ImportResultType)
        },
        onError: (error) => callbacks?.onError?.(error),
      },
    )
  }

  return { preview, isPending: mutation.isPending }
}
