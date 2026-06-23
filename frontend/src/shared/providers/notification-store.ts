import { create } from 'zustand'

/*
  Cola de notificaciones (estado de UI -> Zustand). El notificationProvider de Refine
  escribe aquí y el <Toaster /> las renderiza. Solo el mensaje redactado llega a la UI.
*/

export type NotificationType = 'success' | 'error' | 'progress'

export interface Notification {
  key: string
  message: string
  type: NotificationType
}

interface NotificationState {
  notifications: Notification[]
  push: (notification: Notification) => void
  dismiss: (key: string) => void
}

export const useNotificationStore = create<NotificationState>((set) => ({
  notifications: [],
  push: (notification) =>
    set((state) => ({
      notifications: [
        ...state.notifications.filter((item) => item.key !== notification.key),
        notification,
      ],
    })),
  dismiss: (key) =>
    set((state) => ({
      notifications: state.notifications.filter((item) => item.key !== key),
    })),
}))
