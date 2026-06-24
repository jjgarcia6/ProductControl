import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { PermissionMatrix } from './PermissionMatrix'

const CATALOG = { 'access-control': ['read', 'create', 'update'] }

describe('PermissionMatrix', () => {
  it('marca un permiso al activarlo', () => {
    const onChange = vi.fn()
    render(<PermissionMatrix catalog={CATALOG} value={{}} onChange={onChange} />)

    fireEvent.click(screen.getByLabelText('Crear'))

    expect(onChange).toHaveBeenCalledWith({ 'access-control': ['create'] })
  })

  it('desmarca un permiso y elimina el módulo si queda vacío', () => {
    const onChange = vi.fn()
    render(
      <PermissionMatrix
        catalog={CATALOG}
        value={{ 'access-control': ['read'] }}
        onChange={onChange}
      />,
    )

    fireEvent.click(screen.getByLabelText('Ver'))

    expect(onChange).toHaveBeenCalledWith({})
  })

  it('deshabilita los controles cuando no se puede gestionar', () => {
    render(
      <PermissionMatrix catalog={CATALOG} value={{}} onChange={vi.fn()} disabled />,
    )

    expect(screen.getByLabelText('Ver')).toBeDisabled()
  })
})
