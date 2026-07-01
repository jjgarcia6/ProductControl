import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import type {
  Category,
  Product,
  ProductWriteInput,
  UnitOfMeasure,
} from '../types/products.types'

/*
  Formulario de producto (F5). Presentacional: recibe el producto a editar (opcional), las
  opciones de categoría y unidad, y los callbacks; no llama a la API. RHF + zodResolver. Errores
  de servidor por campo (`fieldErrors`) o generales (`serverError`). Tokens del theme; cero hex.
*/

const productFormSchema = z.object({
  name: z.string().trim().min(1, 'El nombre es obligatorio.').max(128),
  category: z.string().uuid('Seleccione una categoría.'),
  unit_of_measure: z.string().uuid('Seleccione una unidad de medida.'),
})

type ProductFormValues = z.infer<typeof productFormSchema>

const inputClass =
  'h-11 rounded-md border bg-surface px-3 text-base text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40'
const labelClass = 'flex flex-col gap-1 text-sm text-muted-foreground'
const errorClass = 'text-sm text-danger'

interface Props {
  product?: Product
  categories: Category[]
  units: UnitOfMeasure[]
  isPending: boolean
  serverError?: string
  fieldErrors?: Partial<Record<keyof ProductFormValues, string>>
  onSubmit: (values: ProductWriteInput) => void
}

function toFormValues(product?: Product): ProductFormValues {
  return {
    name: product?.name ?? '',
    category: product?.category ?? '',
    unit_of_measure: product?.unit_of_measure ?? '',
  }
}

export function ProductForm({
  product,
  categories,
  units,
  isPending,
  serverError,
  fieldErrors,
  onSubmit,
}: Props) {
  const isEdit = Boolean(product)
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ProductFormValues>({
    resolver: zodResolver(productFormSchema),
    defaultValues: toFormValues(product),
  })

  const errorFor = (field: keyof ProductFormValues) => errors[field]?.message ?? fieldErrors?.[field]

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
      <label className={labelClass}>
        Nombre
        <input type="text" className={inputClass} {...register('name')} aria-invalid={Boolean(errorFor('name'))} />
        {errorFor('name') ? <span className={errorClass}>{errorFor('name')}</span> : null}
      </label>

      <label className={labelClass}>
        Categoría
        <select className={inputClass} {...register('category')} aria-invalid={Boolean(errorFor('category'))}>
          <option value="">Seleccione…</option>
          {categories.map((category) => (
            <option key={category.id} value={category.id}>
              {category.name}
            </option>
          ))}
        </select>
        {errorFor('category') ? <span className={errorClass}>{errorFor('category')}</span> : null}
      </label>

      <label className={labelClass}>
        Unidad de medida
        <select
          className={inputClass}
          {...register('unit_of_measure')}
          aria-invalid={Boolean(errorFor('unit_of_measure'))}
        >
          <option value="">Seleccione…</option>
          {units.map((unit) => (
            <option key={unit.id} value={unit.id}>
              {unit.name} ({unit.symbol})
            </option>
          ))}
        </select>
        {errorFor('unit_of_measure') ? (
          <span className={errorClass}>{errorFor('unit_of_measure')}</span>
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
        {isPending ? 'Guardando…' : isEdit ? 'Guardar cambios' : 'Crear producto'}
      </button>
    </form>
  )
}
