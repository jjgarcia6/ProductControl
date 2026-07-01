import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import type { UnitOfMeasure, UnitOfMeasureWriteInput } from '../types/products.types'

/*
  Formulario de unidad de medida (F5). Presentacional: recibe la unidad a editar (opcional) y los
  callbacks; no llama a la API. RHF + zodResolver. El factor de conversión se captura como string
  decimal (nunca float). Tokens del theme; cero hex.
*/

const CONVERSION_RE = /^-?\d{0,6}(?:\.\d{0,6})?$/

const unitFormSchema = z.object({
  name: z.string().trim().min(1, 'El nombre es obligatorio.').max(64),
  symbol: z.string().trim().min(1, 'El símbolo es obligatorio.').max(16),
  conversion_factor: z
    .string()
    .trim()
    .min(1, 'El factor es obligatorio.')
    .refine((value) => CONVERSION_RE.test(value), 'Ingrese un número válido (máx. 6 decimales).'),
})

type UnitFormValues = z.infer<typeof unitFormSchema>

const inputClass =
  'h-11 rounded-md border bg-surface px-3 text-base text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40'
const labelClass = 'flex flex-col gap-1 text-sm text-muted-foreground'
const errorClass = 'text-sm text-danger'

interface Props {
  unit?: UnitOfMeasure
  isPending: boolean
  serverError?: string
  onSubmit: (values: UnitOfMeasureWriteInput) => void
}

function toFormValues(unit?: UnitOfMeasure): UnitFormValues {
  return {
    name: unit?.name ?? '',
    symbol: unit?.symbol ?? '',
    conversion_factor: unit?.conversion_factor ?? '',
  }
}

export function UnitForm({ unit, isPending, serverError, onSubmit }: Props) {
  const isEdit = Boolean(unit)
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<UnitFormValues>({
    resolver: zodResolver(unitFormSchema),
    defaultValues: toFormValues(unit),
  })

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
      <label className={labelClass}>
        Nombre
        <input type="text" className={inputClass} {...register('name')} aria-invalid={Boolean(errors.name)} />
        {errors.name ? <span className={errorClass}>{errors.name.message}</span> : null}
      </label>

      <label className={labelClass}>
        Símbolo
        <input type="text" className={inputClass} {...register('symbol')} aria-invalid={Boolean(errors.symbol)} />
        {errors.symbol ? <span className={errorClass}>{errors.symbol.message}</span> : null}
      </label>

      <label className={labelClass}>
        Factor de conversión a libras
        <input
          type="text"
          inputMode="decimal"
          className={inputClass}
          {...register('conversion_factor')}
          aria-invalid={Boolean(errors.conversion_factor)}
        />
        {errors.conversion_factor ? (
          <span className={errorClass}>{errors.conversion_factor.message}</span>
        ) : null}
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
        {isPending ? 'Guardando…' : isEdit ? 'Guardar cambios' : 'Crear unidad'}
      </button>
    </form>
  )
}
