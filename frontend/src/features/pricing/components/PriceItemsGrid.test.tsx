import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { Product } from '@/features/products'

import type { PriceListItem } from '../types/pricing.types'
import { PriceItemsGrid } from './PriceItemsGrid'

/*
  PriceItemsGrid es presentacional: se prueba el estado vacío, la validación del precio (formato
  decimal ≥ 0), el payload de alta y el mapeo del error de servidor por campo (400 precio
  negativo) y general (409 producto duplicado).
*/

const onAdd = vi.fn()
const onRemove = vi.fn()

const PRODUCT_ID = '33333333-3333-4333-8333-333333333333'
const products = [{ id: PRODUCT_ID, name: 'Tomate' }] as Product[]

function renderGrid(props: Partial<Parameters<typeof PriceItemsGrid>[0]> = {}) {
  return render(
    <PriceItemsGrid
      items={[]}
      products={products}
      isPending={false}
      onAdd={onAdd}
      onRemove={onRemove}
      {...props}
    />,
  )
}

describe('PriceItemsGrid', () => {
  beforeEach(() => {
    onAdd.mockReset()
    onRemove.mockReset()
  })

  it('muestra el estado vacío', () => {
    renderGrid()
    expect(screen.getByText('Esta lista aún no tiene precios.')).toBeInTheDocument()
  })

  it('rechaza un precio inválido y no envía', async () => {
    renderGrid()

    fireEvent.change(screen.getByLabelText('Producto'), { target: { value: PRODUCT_ID } })
    fireEvent.input(screen.getByLabelText('Precio (USD)'), { target: { value: '-1' } })
    fireEvent.click(screen.getByRole('button', { name: /agregar precio/i }))

    expect(
      await screen.findByText('Ingrese un precio válido (≥ 0, hasta 2 decimales).'),
    ).toBeInTheDocument()
    expect(onAdd).not.toHaveBeenCalled()
  })

  it('agrega el precio con el payload capturado', async () => {
    renderGrid()

    fireEvent.change(screen.getByLabelText('Producto'), { target: { value: PRODUCT_ID } })
    fireEvent.input(screen.getByLabelText('Precio (USD)'), { target: { value: '12.50' } })
    fireEvent.click(screen.getByRole('button', { name: /agregar precio/i }))

    await waitFor(() =>
      expect(onAdd).toHaveBeenCalledWith({ product: PRODUCT_ID, price: '12.50' }),
    )
  })

  it('muestra el error de servidor por campo (400) y el general (409)', () => {
    const items = [
      {
        id: 'aaaa1111-1111-4111-8111-111111111111',
        product: PRODUCT_ID,
        product_name: 'Tomate',
        price: '9.00',
      },
    ] as PriceListItem[]
    renderGrid({ items, serverError: 'El producto ya tiene un precio en esta lista.' })

    expect(screen.getByText('Tomate')).toBeInTheDocument()
    expect(
      screen.getByText('El producto ya tiene un precio en esta lista.'),
    ).toBeInTheDocument()
  })
})
