import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'

import { INTAKE_TYPE_LABELS, type Category, type CategoryWriteInput } from '../types/products.types'
import { categoryFormSchema, type CategoryFormValues } from './category-form-schema'

/*
  Formulario de categoría (F5). Presentacional: recibe la categoría a editar (opcional) y los
  callbacks; no llama a la API (eso lo hace el contenedor). RHF + zodResolver. Caducidad, tipo de
  ingreso y el rango de merma (valores opcionales). Errores de servidor por campo vía `serverError`.
  Tokens del theme; cero hex. Inputs numéricos con texto ≥16px (iOS) y controles ≥44px.
*/

const inputClass =
  'h-11 rounded-md border bg-surface px-3 text-base text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40'
const labelClass = 'flex flex-col gap-1 text-sm text-muted-foreground'
const errorClass = 'text-sm text-danger'

interface Props {
  category?: Category
  isPending: boolean
  serverError?: string
  onSubmit: (values: CategoryWriteInput) => void
}

function toFormValues(category?: Category): CategoryFormValues {
  return {
    name: category?.name ?? '',
    shelf_life_days: category?.shelf_life_days ?? 7,
    intake_type: category?.intake_type ?? 'GAVETA',
    merma_min: category?.merma_min ?? '',
    merma_max: category?.merma_max ?? '',
    reference_qty: category?.reference_qty ?? '',
  }
}

export function CategoryForm({ category, isPending, serverError, onSubmit }: Props) {
  const isEdit = Boolean(category)
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CategoryFormValues>({
    resolver: zodResolver(categoryFormSchema),
    defaultValues: toFormValues(category),
  })

  const submit = (values: CategoryFormValues) => {
    const payload: CategoryWriteInput = {
      name: values.name,
      shelf_life_days: values.shelf_life_days,
      intake_type: values.intake_type,
      merma_min: values.merma_min ? values.merma_min : null,
      merma_max: values.merma_max ? values.merma_max : null,
      ...(values.reference_qty ? { reference_qty: values.reference_qty } : {}),
    }
    onSubmit(payload)
  }

  return (
    <form onSubmit={handleSubmit(submit)} noValidate className="flex flex-col gap-4">
      <label className={labelClass}>
        Nombre
        <input type="text" className={inputClass} {...register('name')} aria-invalid={Boolean(errors.name)} />
        {errors.name ? <span className={errorClass}>{errors.name.message}</span> : null}
      </label>

      <label className={labelClass}>
        Días de caducidad
        <input
          type="number"
          min={0}
          className={inputClass}
          {...register('shelf_life_days', { valueAsNumber: true })}
          aria-invalid={Boolean(errors.shelf_life_days)}
        />
        {errors.shelf_life_days ? (
          <span className={errorClass}>{errors.shelf_life_days.message}</span>
        ) : null}
      </label>

      <label className={labelClass}>
        Tipo de ingreso
        <select className={inputClass} {...register('intake_type')}>
          {(Object.keys(INTAKE_TYPE_LABELS) as Array<keyof typeof INTAKE_TYPE_LABELS>).map(
            (value) => (
              <option key={value} value={value}>
                {INTAKE_TYPE_LABELS[value]}
              </option>
            ),
          )}
        </select>
      </label>

      <fieldset className="grid gap-4 rounded-md border p-3 sm:grid-cols-3">
        <legend className="px-1 text-sm text-muted-foreground">Rango de merma (opcional)</legend>
        <label className={labelClass}>
          Mínimo (lb)
          <input type="text" inputMode="decimal" className={inputClass} {...register('merma_min')} />
          {errors.merma_min ? <span className={errorClass}>{errors.merma_min.message}</span> : null}
        </label>
        <label className={labelClass}>
          Máximo (lb)
          <input type="text" inputMode="decimal" className={inputClass} {...register('merma_max')} />
          {errors.merma_max ? <span className={errorClass}>{errors.merma_max.message}</span> : null}
        </label>
        <label className={labelClass}>
          Referencia (lb)
          <input
            type="text"
            inputMode="decimal"
            placeholder="100"
            className={inputClass}
            {...register('reference_qty')}
          />
          {errors.reference_qty ? (
            <span className={errorClass}>{errors.reference_qty.message}</span>
          ) : null}
        </label>
      </fieldset>

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
        {isPending ? 'Guardando…' : isEdit ? 'Guardar cambios' : 'Crear categoría'}
      </button>
    </form>
  )
}
