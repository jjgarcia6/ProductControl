import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { FieldError } from './FieldError'

describe('FieldError', () => {
  it('muestra el mensaje con role=alert', () => {
    render(<FieldError message="El RUC ingresado no es válido." />)
    expect(screen.getByRole('alert')).toHaveTextContent('El RUC ingresado no es válido.')
  })

  it('no renderiza nada sin mensaje', () => {
    const { container } = render(<FieldError />)
    expect(container).toBeEmptyDOMElement()
  })
})
