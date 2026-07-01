import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { Category, UnitOfMeasure } from '../types/products.types'
import { ProductForm } from './ProductForm'

/*
  ProductForm es presentacional: se prueba la validación de cliente (categoría/unidad requeridas),
  el payload de éxito y el mapeo de errores del backend por campo (400) y general (409).
*/

const onSubmit = vi.fn()

const CATEGORY_ID = '11111111-1111-4111-8111-111111111111'
const UNIT_ID = '22222222-2222-4222-8222-222222222222'

const categories = [{ id: CATEGORY_ID, name: 'Verduras' }] as Category[]
const units = [{ id: UNIT_ID, name: 'Libras', symbol: 'lb' }] as UnitOfMeasure[]

function renderForm(props: Partial<Parameters<typeof ProductForm>[0]> = {}) {
  return render(
    <ProductForm
      categories={categories}
      units={units}
      isPending={false}
      onSubmit={onSubmit}
      {...props}
    />,
  )
}

describe('ProductForm', () => {
  beforeEach(() => {
    onSubmit.mockReset()
  })

  it('valida la categoría y la unidad requeridas y no envía', async () => {
    renderForm()

    fireEvent.input(screen.getByLabelText('Nombre'), { target: { value: 'Tomate' } })
    fireEvent.click(screen.getByRole('button', { name: /crear producto/i }))

    expect(await screen.findByText('Seleccione una categoría.')).toBeInTheDocument()
    expect(screen.getByText('Seleccione una unidad de medida.')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('crea el producto con el payload capturado', async () => {
    renderForm()

    fireEvent.input(screen.getByLabelText('Nombre'), { target: { value: 'Tomate riñón' } })
    fireEvent.change(screen.getByLabelText('Categoría'), { target: { value: CATEGORY_ID } })
    fireEvent.change(screen.getByLabelText('Unidad de medida'), { target: { value: UNIT_ID } })
    fireEvent.click(screen.getByRole('button', { name: /crear producto/i }))

    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith(
        {
          name: 'Tomate riñón',
          category: CATEGORY_ID,
          unit_of_measure: UNIT_ID,
        },
        expect.anything(),
      ),
    )
  })

  it('muestra el error de servidor por campo (400) y el general (409)', () => {
    renderForm({ fieldErrors: { category: 'No existe la categoría.' }, serverError: undefined })
    expect(screen.getByText('No existe la categoría.')).toBeInTheDocument()
  })
})
