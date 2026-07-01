import { type HttpError, useCustomMutation } from '@refinedev/core'

import {
  type ImportEntity,
  type ImportResultType,
  importResultSchema,
} from '../types/import.types'

/*
  Confirmación (commit) de una importación (F7). Sube el archivo a `POST /bulk-import/{entity}`
  (sin `dry_run`). El backend persiste all-or-nothing: 201 con los conteos si ninguna fila
  falla; 400 si alguna fila es inválida (llega como HttpError). La respuesta 201 se valida
  contra el schema Zod generado antes de exponerla.
*/

const INVALID_RESPONSE: HttpError = {
  message: 'La respuesta del servidor no tiene el formato esperado.',
  statusCode: 500,
}

interface Callbacks {
  onSuccess?: (result: ImportResultType) => void
  onError?: (error: HttpError) => void
}

export function useImportCommit() {
  const { mutate, mutation } = useCustomMutation<ImportResultType, HttpError, FormData>()

  const commit = (entity: ImportEntity, file: File, callbacks?: Callbacks): void => {
    const values = new FormData()
    values.append('file', file)
    mutate(
      {
        url: `/bulk-import/${entity}`,
        method: 'post',
        values,
        dataProviderName: 'auth',
        successNotification: { type: 'success', message: 'Importación confirmada.' },
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

  return { commit, isPending: mutation.isPending }
}
