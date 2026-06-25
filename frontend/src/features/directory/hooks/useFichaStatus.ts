import { type HttpError, useCustomMutation, useInvalidate } from '@refinedev/core'

/*
  Transiciones de estado de una ficha (F4): bloquear/desbloquear/dar de baja/reactivar.
  useCustomMutation contra el dataProvider 'auth'. Cada acción es un POST explícito (no PUT).
  Tras el éxito se invalida el listado.
*/

type Transition = 'block' | 'unblock' | 'deactivate' | 'reactivate'

const MESSAGES: Record<Transition, string> = {
  block: 'Ficha bloqueada.',
  unblock: 'Ficha desbloqueada.',
  deactivate: 'Ficha dada de baja.',
  reactivate: 'Ficha reactivada.',
}

interface ActionCallbacks {
  onSuccess?: () => void
  onError?: (error: HttpError) => void
}

export function useFichaStatus() {
  const { mutate, mutation } = useCustomMutation<Record<string, unknown>, HttpError>()
  const invalidate = useInvalidate()

  const changeStatus = (id: string, action: Transition, callbacks?: ActionCallbacks): void => {
    mutate(
      {
        url: `/directory/fichas/${id}/${action}`,
        method: 'post',
        values: {},
        dataProviderName: 'auth',
        successNotification: { type: 'success', message: MESSAGES[action] },
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

  return { changeStatus, isPending: mutation.isPending }
}
