import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { FieldError } from '@/components/custom/FieldError'

import {
  FACET_REQUIRED_ROLE,
  ROLE_LABELS,
  type CreditFacet,
  type FichaRole,
} from '../types/directory.types'

/*
  Sub-formulario de términos de crédito por faceta. Presentacional: solo ofrece las facetas
  cuyo rol tiene la ficha. RHF + zodResolver. El error 400 (faceta↔rol) y 409 (duplicado) del
  backend se mapean al campo de faceta vía `serverError`. Tokens del theme; cero hex.
*/

const subformSchema = z.object({
  facet: z.enum(['CLIENTE', 'PROVEEDOR']),
  credit_limit: z
    .string()
    .regex(/^\d{0,10}(?:\.\d{0,2})?$/, 'Ingrese un monto válido (≥0).'),
  term_days: z.number({ error: 'Días inválidos.' }).int().min(0, 'Días inválidos.'),
  notice_days: z.number({ error: 'Días inválidos.' }).int().min(0, 'Días inválidos.'),
})

export type CreditTermsSubformValues = z.infer<typeof subformSchema>

const inputClass =
  'h-11 w-full rounded-md border bg-surface px-3 text-base text-foreground outline-none ' +
  'focus:border-primary focus:ring-2 focus:ring-primary/40 disabled:opacity-60'
const labelClass = 'mb-1 block text-sm font-medium text-foreground'

interface Props {
  fichaRoles: FichaRole[]
  isPending: boolean
  serverError?: string
  onSubmit: (values: CreditTermsSubformValues) => void
}

export function CreditTermsSubform({ fichaRoles, isPending, serverError, onSubmit }: Props) {
  const availableFacets = (Object.keys(FACET_REQUIRED_ROLE) as CreditFacet[]).filter((facet) =>
    fichaRoles.includes(FACET_REQUIRED_ROLE[facet]),
  )

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CreditTermsSubformValues>({
    resolver: zodResolver(subformSchema),
    defaultValues: {
      facet: availableFacets[0] ?? 'CLIENTE',
      credit_limit: '0',
      term_days: 0,
      notice_days: 2,
    },
  })

  if (availableFacets.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        La ficha no tiene rol de cliente ni proveedor: no aplican términos de crédito.
      </p>
    )
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
      <div>
        <label htmlFor="facet" className={labelClass}>
          Faceta
        </label>
        <select id="facet" aria-invalid={Boolean(serverError)} className={inputClass} {...register('facet')}>
          {availableFacets.map((facet) => (
            <option key={facet} value={facet}>
              {ROLE_LABELS[FACET_REQUIRED_ROLE[facet]]}
            </option>
          ))}
        </select>
        <FieldError message={serverError} />
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div>
          <label htmlFor="credit_limit" className={labelClass}>
            Límite
          </label>
          <input
            id="credit_limit"
            inputMode="decimal"
            aria-invalid={Boolean(errors.credit_limit)}
            className={inputClass}
            {...register('credit_limit')}
          />
          <FieldError message={errors.credit_limit?.message} />
        </div>
        <div>
          <label htmlFor="term_days" className={labelClass}>
            Plazo (días)
          </label>
          <input
            id="term_days"
            type="number"
            min={0}
            className={inputClass}
            {...register('term_days', { valueAsNumber: true })}
          />
          <FieldError message={errors.term_days?.message} />
        </div>
        <div>
          <label htmlFor="notice_days" className={labelClass}>
            Aviso (días)
          </label>
          <input
            id="notice_days"
            type="number"
            min={0}
            className={inputClass}
            {...register('notice_days', { valueAsNumber: true })}
          />
          <FieldError message={errors.notice_days?.message} />
        </div>
      </div>

      <button
        type="submit"
        disabled={isPending}
        className="h-11 rounded-md bg-primary px-4 text-base font-medium text-primary-foreground transition-opacity hover:opacity-90 active:opacity-80 focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-60"
      >
        {isPending ? 'Guardando…' : 'Guardar términos'}
      </button>
    </form>
  )
}
