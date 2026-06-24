import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { FieldError } from '@/components/custom/FieldError'

import { useChangePassword } from '../hooks/useChangePassword'
import { changePasswordSchema, type ChangePasswordInput } from '../types/auth.types'

/*
  Formulario de cambio de contraseña propia. React Hook Form + zodResolver sobre el schema
  generado. Los errores 400 del backend (contraseña actual incorrecta / nueva no cumple la
  política) llegan por campo y se pintan junto al input correspondiente con `setError`.
  Tokens del theme (cero hex); inputs 16px; alto táctil ≥44px.
*/

const changePasswordFormSchema = changePasswordSchema.extend({
  current_password: z.string().min(1, 'Ingrese su contraseña actual.'),
  new_password: z.string().min(8, 'La nueva contraseña debe tener al menos 8 caracteres.'),
})

const inputClass =
  'h-11 w-full rounded-md border bg-surface px-3 text-base text-foreground ' +
  'outline-none focus:border-primary focus:ring-2 focus:ring-primary/40 ' +
  'disabled:opacity-60'

const labelClass = 'mb-1 block text-sm font-medium text-foreground'

const FIELD_NAMES: ReadonlyArray<keyof ChangePasswordInput> = [
  'current_password',
  'new_password',
]

export function ChangePasswordForm() {
  const { changePassword, isPending } = useChangePassword()
  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors },
  } = useForm<ChangePasswordInput>({
    resolver: zodResolver(changePasswordFormSchema),
    defaultValues: { current_password: '', new_password: '' },
  })

  const onSubmit = (values: ChangePasswordInput) => {
    changePassword(values, {
      onSuccess: () => reset(),
      onError: (error) => {
        const fieldErrors = error.errors
        let mapped = false
        if (fieldErrors) {
          for (const field of FIELD_NAMES) {
            const messages = fieldErrors[field]
            if (messages) {
              const message = Array.isArray(messages) ? messages[0] : String(messages)
              setError(field, { message })
              mapped = true
            }
          }
        }
        if (!mapped) {
          setError('root', { message: error.message })
        }
      },
    })
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
      <div>
        <label htmlFor="current_password" className={labelClass}>
          Contraseña actual
        </label>
        <input
          id="current_password"
          type="password"
          autoComplete="current-password"
          aria-invalid={Boolean(errors.current_password)}
          className={inputClass}
          {...register('current_password')}
        />
        <FieldError message={errors.current_password?.message} />
      </div>

      <div>
        <label htmlFor="new_password" className={labelClass}>
          Nueva contraseña
        </label>
        <input
          id="new_password"
          type="password"
          autoComplete="new-password"
          aria-invalid={Boolean(errors.new_password)}
          className={inputClass}
          {...register('new_password')}
        />
        <FieldError message={errors.new_password?.message} />
      </div>

      {errors.root?.message ? <FieldError message={errors.root.message} /> : null}

      <button
        type="submit"
        disabled={isPending}
        className="h-11 rounded-md bg-primary px-4 text-base font-medium text-primary-foreground transition-opacity hover:opacity-90 active:opacity-80 focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-60"
      >
        {isPending ? 'Guardando…' : 'Cambiar contraseña'}
      </button>
    </form>
  )
}
