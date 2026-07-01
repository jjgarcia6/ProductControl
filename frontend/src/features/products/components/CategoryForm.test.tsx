import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { CategoryForm } from './CategoryForm'

/*
  CategoryForm es presentacional (recibe onSubmit por props): se prueba la validación de cliente,
  el payload de éxito y el render del error de servidor, sin mockear la API.
*/

const onSubmit = vi.fn()

describe('CategoryForm', () => {
  beforeEach(() => {
    onSubmit.mockReset()
  })

  it('valida el nombre requerido y no envía', async () => {
    render(<CategoryForm isPending={false} onSubmit={onSubmit} />)

    fireEvent.input(screen.getByLabelText('Nombre'), { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: /crear categoría/i }))

    expect(await screen.findByText('El nombre es obligatorio.')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('crea la categoría con el payload capturado', async () => {
    render(<CategoryForm isPending={false} onSubmit={onSubmit} />)

    fireEvent.input(screen.getByLabelText('Nombre'), { target: { value: 'Lácteos' } })
    fireEvent.input(screen.getByLabelText('Días de caducidad'), { target: { value: '5' } })
    fireEvent.change(screen.getByLabelText('Tipo de ingreso'), { target: { value: 'PESO' } })
    fireEvent.click(screen.getByRole('button', { name: /crear categoría/i }))

    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'Lácteos',
          shelf_life_days: 5,
          intake_type: 'PESO',
          merma_min: null,
          merma_max: null,
        }),
      ),
    )
  })

  it('muestra el error de servidor (409) como aviso', () => {
    render(
      <CategoryForm
        isPending={false}
        serverError="Ya existe una categoría con este nombre."
        onSubmit={onSubmit}
      />,
    )

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Ya existe una categoría con este nombre.',
    )
  })
})
