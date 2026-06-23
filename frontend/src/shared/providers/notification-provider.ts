import type { NotificationProvider } from '@refinedev/core'

import { useNotificationStore } from './notification-store'

/*
  notificationProvider de Refine (§6.3). Muestra avisos limpios (toast/alert) con el
  mensaje ya redactado del backend. No expone status crudo, URL, JSON ni stack.
*/
export const notificationProvider: NotificationProvider = {
  open: ({ key, message, type }) => {
    useNotificationStore.getState().push({
      key: key ?? crypto.randomUUID(),
      message,
      type: type === 'success' ? 'success' : type === 'progress' ? 'progress' : 'error',
    })
  },
  close: (key) => {
    useNotificationStore.getState().dismiss(key)
  },
}
