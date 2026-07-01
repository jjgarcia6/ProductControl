import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import {
  PRICE_LIST_TYPE_LABELS,
  type PriceList,
  type PriceListType,
  type PriceListWriteInput,
} from '../types/pricing.types'

/*
  Formulario de lista de precios (F6). Presentacional: recibe la lista a editar (opcional) y los
  callbacks; no llama a la API. RHF + zodResolver. Errores de servidor por campo (`fieldErrors`)
  o generales (`serverError`, p. ej. nombre duplicado 409). Tokens del theme; cero hex.
*/

const priceListFormSchema = z.object({
  name: z.string().trim().min(1, 'El nombre es obligatorio.').max(120),
  type: z.enum(['NORMAL', 'DESCARTE']),
})

type PriceListFormValues = z.infer<typeof priceListFormSchema>

const TYPES = Object.keys(PRICE_LIST_TYPE_LABELS) as PriceListType[]

const inputClass =
  'h-11 rounded-md border bg-surface px-3 text-base text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40'
const labelClass = 'flex flex-col gap-1 text-sm text-muted-foreground'
const errorClass = 'text-sm text-danger'

interface Props {
  priceList?: PriceList
  isPending: boolean
  serverError?: string
  fieldErrors?: Partial<Record<keyof PriceListFormValues, string>>
  onSubmit: (values: PriceListWriteInput) => void
}

function toFormValues(priceList?: PriceList): PriceListFormValues {
  return {
    name: priceList?.name ?? '',
    type: priceList?.type ?? 'NORMAL',
  }
}

export function PriceListForm({ priceList, isPending, serverError, fieldErrors, onSubmit }: Props) {
  const isEdit = Boolean(priceList)
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<PriceListFormValues>({
    resolver: zodResolver(priceListFormSchema),
    defaultValues: toFormValues(priceList),
  })

  const errorFor = (field: keyof PriceListFormValues) =>
    errors[field]?.message ?? fieldErrors?.[field]

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
      <label className={labelClass}>
        Nombre
        <input
          type="text"
          className={inputClass}
          {...register('name')}
          aria-invalid={Boolean(errorFor('name'))}
        />
        {errorFor('name') ? <span className={errorClass}>{errorFor('name')}</span> : null}
      </label>

      <label className={labelClass}>
        Tipo
        <select
          className={inputClass}
          {...register('type')}
          aria-invalid={Boolean(errorFor('type'))}
        >
          {TYPES.map((value) => (
            <option key={value} value={value}>
              {PRICE_LIST_TYPE_LABELS[value]}
            </option>
          ))}
        </select>
        {errorFor('type') ? <span className={errorClass}>{errorFor('type')}</span> : null}
      </label>

      {serverError ? (
        <p role="alert" className={errorClass}>
          {serverError}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={isPending}
        className="h-11 rounded-md bg-primary px-4 text-base font-medium text-primary-foreground transition-opacity hover:opacity-90 active:opacity-80 focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-60"
      >
        {isPending ? 'Guardando…' : isEdit ? 'Guardar cambios' : 'Crear lista'}
      </button>
    </form>
  )
}
