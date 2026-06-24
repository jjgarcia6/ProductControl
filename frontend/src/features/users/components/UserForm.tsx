import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { FieldError } from '@/components/custom/FieldError'

/*
  Formulario de alta de usuario. Presentacional: recibe la lista de perfiles, `onSubmit`,
  `isPending` y los errores del servidor por campo (`serverErrors`); sin estado asíncrono ni
  llamadas a la API. RHF + zodResolver para la validación de cliente. Tokens del theme (cero
  hex); inputs ≥16px (text-base); alto táctil ≥44px (h-11).
*/

const formSchema = z.object({
  username: z.string().min(1, 'Ingrese un identificador.'),
  password: z.string().min(8, 'La contraseña debe tener al menos 8 caracteres.'),
  profile_id: z.string().min(1, 'Seleccione un perfil.'),
  first_name: z.string().optional(),
})

export type UserFormValues = z.infer<typeof formSchema>

interface ProfileOption {
  id: string
  name: string
}

interface UserFormProps {
  profiles: ProfileOption[]
  onSubmit: (values: UserFormValues) => void
  isPending: boolean
  serverErrors?: Partial<Record<keyof UserFormValues, string>>
}

const inputClass =
  'h-11 w-full rounded-md border bg-surface px-3 text-base text-foreground outline-none ' +
  'focus:border-primary focus:ring-2 focus:ring-primary/40 disabled:opacity-60'
const labelClass = 'mb-1 block text-sm font-medium text-foreground'

export function UserForm({ profiles, onSubmit, isPending, serverErrors }: UserFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<UserFormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { username: '', password: '', profile_id: '', first_name: '' },
  })

  const errorFor = (field: keyof UserFormValues) =>
    errors[field]?.message ?? serverErrors?.[field]

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
      <div>
        <label htmlFor="username" className={labelClass}>
          Identificador
        </label>
        <input
          id="username"
          autoComplete="off"
          aria-invalid={Boolean(errorFor('username'))}
          className={inputClass}
          {...register('username')}
        />
        <FieldError message={errorFor('username')} />
      </div>

      <div>
        <label htmlFor="first_name" className={labelClass}>
          Nombre
        </label>
        <input id="first_name" className={inputClass} {...register('first_name')} />
      </div>

      <div>
        <label htmlFor="profile_id" className={labelClass}>
          Perfil
        </label>
        <select
          id="profile_id"
          aria-invalid={Boolean(errorFor('profile_id'))}
          className={inputClass}
          {...register('profile_id')}
        >
          <option value="">Seleccione…</option>
          {profiles.map((profile) => (
            <option key={profile.id} value={profile.id}>
              {profile.name}
            </option>
          ))}
        </select>
        <FieldError message={errorFor('profile_id')} />
      </div>

      <div>
        <label htmlFor="password" className={labelClass}>
          Contraseña inicial
        </label>
        <input
          id="password"
          type="password"
          autoComplete="new-password"
          aria-invalid={Boolean(errorFor('password'))}
          className={inputClass}
          {...register('password')}
        />
        <FieldError message={errorFor('password')} />
      </div>

      <button
        type="submit"
        disabled={isPending}
        className="h-11 rounded-md bg-primary px-4 text-base font-medium text-primary-foreground transition-opacity hover:opacity-90 active:opacity-80 focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-60"
      >
        {isPending ? 'Creando…' : 'Crear usuario'}
      </button>
    </form>
  )
}
