import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { CreditTermsSubform } from './CreditTermsSubform'

describe('CreditTermsSubform', () => {
  it('solo ofrece la faceta cuyo rol tiene la ficha', () => {
    render(
      <CreditTermsSubform fichaRoles={['PROVEEDOR']} isPending={false} onSubmit={vi.fn()} />,
    )

    const select = screen.getByLabelText('Faceta') as HTMLSelectElement
    const options = Array.from(select.options).map((option) => option.value)
    expect(options).toEqual(['PROVEEDOR'])
  })

  it('muestra un aviso cuando la ficha no es cliente ni proveedor', () => {
    render(
      <CreditTermsSubform fichaRoles={['CHOFER']} isPending={false} onSubmit={vi.fn()} />,
    )

    expect(screen.getByText(/no aplican términos de crédito/i)).toBeInTheDocument()
    expect(screen.queryByLabelText('Faceta')).not.toBeInTheDocument()
  })

  it('envía los términos capturados', async () => {
    const onSubmit = vi.fn()
    render(
      <CreditTermsSubform fichaRoles={['CLIENTE']} isPending={false} onSubmit={onSubmit} />,
    )

    fireEvent.input(screen.getByLabelText('Límite'), { target: { value: '1500.50' } })
    fireEvent.click(screen.getByRole('button', { name: /guardar términos/i }))

    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({ facet: 'CLIENTE', credit_limit: '1500.50', notice_days: 2 }),
        expect.anything(),
      ),
    )
  })

  it('muestra el error del servidor en el campo de faceta', () => {
    render(
      <CreditTermsSubform
        fichaRoles={['CLIENTE']}
        isPending={false}
        serverError="La ficha no tiene el rol requerido para la faceta CLIENTE."
        onSubmit={vi.fn()}
      />,
    )

    expect(
      screen.getByText('La ficha no tiene el rol requerido para la faceta CLIENTE.'),
    ).toBeInTheDocument()
  })
})
