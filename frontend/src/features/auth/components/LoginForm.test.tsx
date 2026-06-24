import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { LoginForm } from './LoginForm'

describe('LoginForm', () => {
  it('valida campos vacíos y no invoca onSubmit', async () => {
    const onSubmit = vi.fn()
    render(<LoginForm onSubmit={onSubmit} isSubmitting={false} />)

    fireEvent.click(screen.getByRole('button', { name: /ingresar/i }))

    expect(await screen.findByText('Ingrese su usuario.')).toBeInTheDocument()
    expect(screen.getByText('Ingrese su contraseña.')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('envía las credenciales capturadas', async () => {
    const onSubmit = vi.fn()
    render(<LoginForm onSubmit={onSubmit} isSubmitting={false} />)

    fireEvent.input(screen.getByLabelText('Usuario'), { target: { value: 'ana' } })
    fireEvent.input(screen.getByLabelText('Contraseña'), { target: { value: 'secreta' } })
    fireEvent.click(screen.getByRole('button', { name: /ingresar/i }))

    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({ username: 'ana', password: 'secreta' }),
        expect.anything(),
      ),
    )
  })

  it('muestra el error del servidor con role=alert', () => {
    render(
      <LoginForm
        onSubmit={vi.fn()}
        isSubmitting={false}
        errorMessage="Credenciales inválidas."
      />,
    )
    expect(screen.getByRole('alert')).toHaveTextContent('Credenciales inválidas.')
  })

  it('deshabilita el botón mientras envía (estado de carga)', () => {
    render(<LoginForm onSubmit={vi.fn()} isSubmitting />)
    expect(screen.getByRole('button', { name: /ingresando/i })).toBeDisabled()
  })

  it('los inputs son accesibles por etiqueta (teclado/ARIA)', () => {
    render(<LoginForm onSubmit={vi.fn()} isSubmitting={false} />)
    expect(screen.getByLabelText('Usuario')).toHaveAttribute('type', 'text')
    expect(screen.getByLabelText('Contraseña')).toHaveAttribute('type', 'password')
  })
})
