import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { FichaForm } from './FichaForm'

/*
  El contenedor usa hooks de mutación (Refine). Se mockean para aislar el flujo del
  formulario: validación de cliente, payload de éxito y mapeo de errores del backend.
*/

const createFicha = vi.fn()
const updateFicha = vi.fn()
const createTerms = vi.fn()

vi.mock('../hooks/useFichaMutation', () => ({
  useFichaMutation: () => ({ createFicha, updateFicha, isPending: false }),
}))
vi.mock('../hooks/useCreditTerms', () => ({
  useCreditTerms: () => ({ createTerms, updateTerms: vi.fn(), isPending: false }),
}))

describe('FichaForm', () => {
  beforeEach(() => {
    createFicha.mockReset()
    updateFicha.mockReset()
    createTerms.mockReset()
  })

  it('valida los campos requeridos y no envía', async () => {
    render(<FichaForm />)

    fireEvent.click(screen.getByRole('button', { name: /crear ficha/i }))

    expect(await screen.findByText('Ingrese un nombre o razón social.')).toBeInTheDocument()
    expect(screen.getByText('Seleccione al menos un rol.')).toBeInTheDocument()
    expect(createFicha).not.toHaveBeenCalled()
  })

  it('crea la ficha con el payload capturado', async () => {
    render(<FichaForm />)

    fireEvent.input(screen.getByLabelText('Nombre o razón social'), {
      target: { value: 'Distribuidora Andina' },
    })
    fireEvent.input(screen.getByLabelText('Número'), { target: { value: '1710034065' } })
    fireEvent.click(screen.getByLabelText('Cliente'))
    fireEvent.click(screen.getByRole('button', { name: /crear ficha/i }))

    await waitFor(() =>
      expect(createFicha).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'Distribuidora Andina',
          identification_type: 'CEDULA',
          identification_number: '1710034065',
          roles: ['CLIENTE'],
        }),
        expect.anything(),
      ),
    )
  })

  it('mapea el error del backend al campo del número', async () => {
    createFicha.mockImplementation((_values, callbacks) => {
      callbacks.onError({
        message: 'Conflicto',
        statusCode: 400,
        errors: { identification_number: ['El número no es válido para el tipo CEDULA.'] },
      })
    })
    render(<FichaForm />)

    fireEvent.input(screen.getByLabelText('Nombre o razón social'), {
      target: { value: 'X' },
    })
    fireEvent.input(screen.getByLabelText('Número'), { target: { value: '1710034060' } })
    fireEvent.click(screen.getByLabelText('Cliente'))
    fireEvent.click(screen.getByRole('button', { name: /crear ficha/i }))

    expect(
      await screen.findByText('El número no es válido para el tipo CEDULA.'),
    ).toBeInTheDocument()
  })
})
