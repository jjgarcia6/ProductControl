import { cn } from '@/shared/lib/utils'
import { useNotificationStore } from '@/shared/providers/notification-store'

/*
  Renderiza los avisos globales. Los colores salen de tokens semánticos de ESTADO
  (success/danger/info), nunca del acento índigo. Cada aviso muestra solo su mensaje.
*/
const TYPE_STYLES = {
  success: 'border-success text-success',
  error: 'border-danger text-danger',
  progress: 'border-info text-info',
} as const

export function Toaster() {
  const notifications = useNotificationStore((state) => state.notifications)
  const dismiss = useNotificationStore((state) => state.dismiss)

  if (notifications.length === 0) return null

  return (
    <div className="fixed bottom-4 right-4 flex flex-col gap-2">
      {notifications.map((notification) => (
        <div
          key={notification.key}
          role="status"
          className={cn(
            'flex items-center gap-3 rounded-md border bg-surface px-4 py-3 text-sm',
            TYPE_STYLES[notification.type],
          )}
        >
          <span className="text-foreground">{notification.message}</span>
          <button
            type="button"
            onClick={() => dismiss(notification.key)}
            className="text-muted-foreground"
            aria-label="Cerrar"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  )
}
