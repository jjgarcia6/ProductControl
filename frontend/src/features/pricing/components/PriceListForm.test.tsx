import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { PriceListForm } from './PriceListForm'

/*
  PriceListForm es presentacional: se prueba la validación de cliente (nombre requerido), el
  payload de éxito y el mapeo del error general del backend (409 nombre duplicado).
*/

const onSubmit = vi.fn()

function renderForm(props: Partial<Parameters<typeof PriceListForm>[0]> = {}) {
  return render(<PriceListForm isPending={false} onSubmit={onSubmit} {...props} />)
}

describe('PriceListForm', () => {
  beforeEach(() => {
    onSubmit.mockReset()
  })

  it('valida el nombre requerido y no envía', async () => {
    renderForm()

    fireEvent.click(screen.getByRole('button', { name: /crear lista/i }))

    expect(await screen.findByText('El nombre es obligatorio.')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('crea la lista con el payload capturado (tipo NORMAL por defecto)', async () => {
    renderForm()

    fireEvent.input(screen.getByLabelText('Nombre'), { target: { value: 'Mayorista' } })
    fireEvent.click(screen.getByRole('button', { name: /crear lista/i }))

    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith(
        { name: 'Mayorista', type: 'NORMAL' },
        expect.anything(),
      ),
    )
  })

  it('muestra el error general de servidor (409 nombre duplicado)', () => {
    renderForm({ serverError: 'Ya existe una lista de precios con este nombre.' })
    expect(
      screen.getByText('Ya existe una lista de precios con este nombre.'),
    ).toBeInTheDocument()
  })
})
