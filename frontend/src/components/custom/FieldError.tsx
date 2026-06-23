import { cn } from '@/shared/lib/utils'

/*
  Muestra el mensaje de error junto a un campo de formulario. Es el MISMO componente
  para los errores de validación de Zod (cliente) y los del backend (§6.3): un único
  lenguaje visual de error en toda la app. Usa el token semántico `danger` (color de
  estado, nunca el acento índigo).
*/
export function FieldError({ message, className }: { message?: string; className?: string }) {
  if (!message) return null
  return (
    <p role="alert" className={cn('mt-1 text-sm text-danger', className)}>
      {message}
    </p>
  )
}
