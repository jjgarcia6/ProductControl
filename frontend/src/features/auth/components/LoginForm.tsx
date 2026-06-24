import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { FieldError } from '@/components/custom/FieldError'

import { loginSchema, type LoginInput } from '../types/auth.types'

/*
  Formulario de login PRESENTACIONAL. No conoce el authProvider: recibe `onSubmit`,
  `isSubmitting` y `errorMessage` del contenedor. React Hook Form + zodResolver sobre el
  schema generado (con mínimos locales para feedback temprano). Todo color sale de tokens
  del theme (cero hex). Inputs de 16px (evita el zoom de Safari iOS) y alto táctil ≥44px.
*/

// Refuerza el schema generado con mínimos para validación de cliente (UX), sin cambiar el tipo.
const loginFormSchema = loginSchema.extend({
  username: z.string().min(1, 'Ingrese su usuario.'),
  password: z.string().min(1, 'Ingrese su contraseña.'),
})

const inputClass =
  'h-11 w-full rounded-md border bg-surface px-3 text-base text-foreground ' +
  'outline-none focus:border-primary focus:ring-2 focus:ring-primary/40 ' +
  'disabled:opacity-60'

const labelClass = 'mb-1 block text-sm font-medium text-foreground'

interface LoginFormProps {
  onSubmit: (values: LoginInput) => void
  isSubmitting: boolean
  errorMessage?: string
}

export function LoginForm({ onSubmit, isSubmitting, errorMessage }: LoginFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginInput>({
    resolver: zodResolver(loginFormSchema),
    defaultValues: { username: '', password: '' },
  })

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
      <div>
        <label htmlFor="username" className={labelClass}>
          Usuario
        </label>
        <input
          id="username"
          type="text"
          autoComplete="username"
          autoFocus
          aria-invalid={Boolean(errors.username)}
          className={inputClass}
          {...register('username')}
        />
        <FieldError message={errors.username?.message} />
      </div>

      <div>
        <label htmlFor="password" className={labelClass}>
          Contraseña
        </label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          aria-invalid={Boolean(errors.password)}
          className={inputClass}
          {...register('password')}
        />
        <FieldError message={errors.password?.message} />
      </div>

      {errorMessage ? <FieldError message={errorMessage} /> : null}

      <button
        type="submit"
        disabled={isSubmitting}
        className="h-11 rounded-md bg-primary px-4 text-base font-medium text-primary-foreground transition-opacity hover:opacity-90 active:opacity-80 focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-60"
      >
        {isSubmitting ? 'Ingresando…' : 'Ingresar'}
      </button>
    </form>
  )
}
