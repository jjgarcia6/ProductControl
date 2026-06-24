import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { ResetPasswordDialog } from './ResetPasswordDialog'

const baseProps = {
  username: 'ana',
  onClose: vi.fn(),
  isPending: false,
}

describe('ResetPasswordDialog', () => {
  it('por defecto solicita generar la contraseña automáticamente', () => {
    const onSubmit = vi.fn()
    render(<ResetPasswordDialog {...baseProps} onSubmit={onSubmit} />)

    fireEvent.click(screen.getByRole('button', { name: /restablecer/i }))

    expect(onSubmit).toHaveBeenCalledWith({ generate: true })
  })

  it('permite definir una contraseña temporal manual', () => {
    const onSubmit = vi.fn()
    render(<ResetPasswordDialog {...baseProps} onSubmit={onSubmit} />)

    fireEvent.click(screen.getByLabelText('Definir manualmente'))
    fireEvent.input(screen.getByLabelText('Contraseña temporal'), {
      target: { value: 'Temp0ral-99' },
    })
    fireEvent.click(screen.getByRole('button', { name: /restablecer/i }))

    expect(onSubmit).toHaveBeenCalledWith({
      temporary_password: 'Temp0ral-99',
      generate: false,
    })
  })

  it('muestra la contraseña temporal resultante una vez', () => {
    render(
      <ResetPasswordDialog
        {...baseProps}
        onSubmit={vi.fn()}
        temporaryPassword="Generada-123"
      />,
    )

    expect(screen.getByText('Generada-123')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /listo/i })).toBeInTheDocument()
  })
})
