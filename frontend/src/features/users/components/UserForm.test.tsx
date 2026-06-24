import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { UserForm } from './UserForm'

const PROFILES = [
  { id: 'p1', name: 'Jefe' },
  { id: 'p2', name: 'Supervisor' },
]

describe('UserForm', () => {
  it('valida campos requeridos y no invoca onSubmit', async () => {
    const onSubmit = vi.fn()
    render(<UserForm profiles={PROFILES} onSubmit={onSubmit} isPending={false} />)

    fireEvent.click(screen.getByRole('button', { name: /crear usuario/i }))

    expect(await screen.findByText('Ingrese un identificador.')).toBeInTheDocument()
    expect(screen.getByText('Seleccione un perfil.')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('envía los datos capturados', async () => {
    const onSubmit = vi.fn()
    render(<UserForm profiles={PROFILES} onSubmit={onSubmit} isPending={false} />)

    fireEvent.input(screen.getByLabelText('Identificador'), { target: { value: 'ana' } })
    fireEvent.input(screen.getByLabelText('Contraseña inicial'), {
      target: { value: 'Str0ng-Pass!' },
    })
    fireEvent.change(screen.getByLabelText('Perfil'), { target: { value: 'p2' } })
    fireEvent.click(screen.getByRole('button', { name: /crear usuario/i }))

    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({ username: 'ana', password: 'Str0ng-Pass!', profile_id: 'p2' }),
        expect.anything(),
      ),
    )
  })

  it('muestra los errores del servidor por campo', () => {
    render(
      <UserForm
        profiles={PROFILES}
        onSubmit={vi.fn()}
        isPending={false}
        serverErrors={{ username: 'Ya existe un usuario con este identificador.' }}
      />,
    )

    expect(
      screen.getByText('Ya existe un usuario con este identificador.'),
    ).toBeInTheDocument()
  })
})
