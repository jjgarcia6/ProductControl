import type { FieldErrors, UseFormRegister } from 'react-hook-form'

import { FieldError } from '@/components/custom/FieldError'

import {
  IDENTIFICATION_TYPE_LABELS,
  ROLE_LABELS,
  type FichaRole,
  type IdentificationType,
} from '../types/directory.types'
import type { FichaFormValues } from './ficha-form-schema'

/*
  Campos del formulario de ficha. Presentacional: recibe el `register` de RHF, los errores y
  un resolutor de error por campo; sin estado asíncrono ni llamadas a la API. Tokens del theme
  (cero hex); inputs ≥16px (text-base); alto táctil ≥44px (h-11).
*/

const inputClass =
  'h-11 w-full rounded-md border bg-surface px-3 text-base text-foreground outline-none ' +
  'focus:border-primary focus:ring-2 focus:ring-primary/40 disabled:opacity-60'
const labelClass = 'mb-1 block text-sm font-medium text-foreground'

interface Props {
  register: UseFormRegister<FichaFormValues>
  errors: FieldErrors<FichaFormValues>
  errorFor: (field: keyof FichaFormValues) => string | undefined
}

const ID_TYPES = Object.keys(IDENTIFICATION_TYPE_LABELS) as IdentificationType[]
const ROLES = Object.keys(ROLE_LABELS) as FichaRole[]

export function FichaFormFields({ register, errors, errorFor }: Props) {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <label htmlFor="name" className={labelClass}>
          Nombre o razón social
        </label>
        <input
          id="name"
          aria-invalid={Boolean(errorFor('name'))}
          className={inputClass}
          {...register('name')}
        />
        <FieldError message={errorFor('name')} />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="identification_type" className={labelClass}>
            Tipo de identificación
          </label>
          <select id="identification_type" className={inputClass} {...register('identification_type')}>
            {ID_TYPES.map((type) => (
              <option key={type} value={type}>
                {IDENTIFICATION_TYPE_LABELS[type]}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="identification_number" className={labelClass}>
            Número
          </label>
          <input
            id="identification_number"
            inputMode="numeric"
            aria-invalid={Boolean(errorFor('identification_number'))}
            className={inputClass}
            {...register('identification_number')}
          />
          <FieldError message={errorFor('identification_number')} />
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="email" className={labelClass}>
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="off"
            aria-invalid={Boolean(errorFor('email'))}
            className={inputClass}
            {...register('email')}
          />
          <FieldError message={errorFor('email')} />
        </div>
        <div>
          <label htmlFor="phone" className={labelClass}>
            Teléfono / WhatsApp
          </label>
          <input id="phone" inputMode="tel" className={inputClass} {...register('phone')} />
        </div>
      </div>

      <fieldset>
        <legend className={labelClass}>Roles</legend>
        <div className="flex flex-wrap gap-3">
          {ROLES.map((role) => (
            <label
              key={role}
              className="flex h-11 items-center gap-2 rounded-md border bg-surface px-3 text-sm text-foreground"
            >
              <input type="checkbox" value={role} className="size-4" {...register('roles')} />
              {ROLE_LABELS[role]}
            </label>
          ))}
        </div>
        <FieldError message={errors.roles?.message} />
      </fieldset>
    </div>
  )
}
