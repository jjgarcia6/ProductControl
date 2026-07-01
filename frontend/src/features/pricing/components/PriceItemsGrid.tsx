import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import type { Product } from '@/features/products'

import type { PriceListItem, PriceListItemWriteInput } from '../types/pricing.types'

/*
  Grilla de precios de una lista (F6). Presentacional: recibe los ítems, los productos
  disponibles y los callbacks; no llama a la API. El alta usa RHF + zodResolver (precio decimal,
  2 lugares, ≥ 0). Errores de servidor por campo (`fieldErrors`, p. ej. precio negativo 400) o
  generales (`serverError`, p. ej. producto duplicado 409). Tokens del theme; cero hex.
*/

const addItemSchema = z.object({
  product: z.string().uuid('Seleccione un producto.'),
  price: z
    .string()
    .trim()
    .regex(/^\d{0,10}(?:\.\d{1,2})?$/, 'Ingrese un precio válido (≥ 0, hasta 2 decimales).'),
})

type AddItemValues = z.infer<typeof addItemSchema>

const inputClass =
  'h-11 rounded-md border bg-surface px-3 text-base text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40'
const labelClass = 'flex flex-col gap-1 text-sm text-muted-foreground'
const errorClass = 'text-sm text-danger'

interface Props {
  items: PriceListItem[]
  products: Product[]
  isPending: boolean
  serverError?: string
  fieldErrors?: Partial<Record<keyof AddItemValues, string>>
  onAdd: (values: PriceListItemWriteInput) => void
  onRemove: (itemId: string) => void
}

export function PriceItemsGrid({
  items,
  products,
  isPending,
  serverError,
  fieldErrors,
  onAdd,
  onRemove,
}: Props) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<AddItemValues>({
    resolver: zodResolver(addItemSchema),
    defaultValues: { product: '', price: '' },
  })

  const errorFor = (field: keyof AddItemValues) => errors[field]?.message ?? fieldErrors?.[field]

  // Solo productos que aún no tienen precio en esta lista.
  const pricedIds = new Set(items.map((item) => item.product))
  const available = products.filter((product) => !pricedIds.has(product.id))

  const submit = (values: AddItemValues) => {
    onAdd(values)
    reset({ product: '', price: '' })
  }

  return (
    <div className="flex flex-col gap-5">
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">Esta lista aún no tiene precios.</p>
      ) : (
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="py-2 pr-4 font-medium">Producto</th>
              <th className="py-2 pr-4 font-medium">Precio (USD)</th>
              <th className="py-2 font-medium">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="border-b align-middle">
                <td className="py-3 pr-4 font-medium text-foreground">{item.product_name}</td>
                <td className="py-3 pr-4 text-muted-foreground">{item.price}</td>
                <td className="py-3">
                  <button
                    type="button"
                    onClick={() => onRemove(item.id)}
                    disabled={isPending}
                    className="h-11 rounded-md border border-danger px-3 text-sm font-medium text-danger hover:bg-danger/10 disabled:opacity-60"
                  >
                    Quitar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <form
        onSubmit={handleSubmit(submit)}
        noValidate
        className="flex flex-wrap items-end gap-3 border-t pt-4"
      >
        <label className={`${labelClass} min-w-48 flex-1`}>
          Producto
          <select
            className={inputClass}
            {...register('product')}
            aria-invalid={Boolean(errorFor('product'))}
          >
            <option value="">Seleccione…</option>
            {available.map((product) => (
              <option key={product.id} value={product.id}>
                {product.name}
              </option>
            ))}
          </select>
          {errorFor('product') ? <span className={errorClass}>{errorFor('product')}</span> : null}
        </label>

        <label className={labelClass}>
          Precio (USD)
          <input
            type="text"
            inputMode="decimal"
            className={inputClass}
            {...register('price')}
            aria-invalid={Boolean(errorFor('price'))}
          />
          {errorFor('price') ? <span className={errorClass}>{errorFor('price')}</span> : null}
        </label>

        <button
          type="submit"
          disabled={isPending}
          className="h-11 rounded-md bg-primary px-4 text-base font-medium text-primary-foreground transition-opacity hover:opacity-90 active:opacity-80 focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-60"
        >
          {isPending ? 'Agregando…' : 'Agregar precio'}
        </button>
      </form>

      {serverError ? (
        <p role="alert" className={errorClass}>
          {serverError}
        </p>
      ) : null}
    </div>
  )
}
