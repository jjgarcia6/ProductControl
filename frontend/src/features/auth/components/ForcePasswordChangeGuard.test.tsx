import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { describe, expect, it, vi } from 'vitest'

import { ForcePasswordChangeGuard } from './ForcePasswordChangeGuard'

const useGetIdentity = vi.fn()
vi.mock('@refinedev/core', () => ({
  useGetIdentity: () => useGetIdentity(),
}))

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="/admin/users"
          element={
            <ForcePasswordChangeGuard>
              <div>contenido protegido</div>
            </ForcePasswordChangeGuard>
          }
        />
        <Route path="/account/change-password" element={<div>pantalla de cambio</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ForcePasswordChangeGuard', () => {
  it('redirige al cambio de contraseña cuando el flag está activo', () => {
    useGetIdentity.mockReturnValue({ data: { must_change_password: true } })

    renderAt('/admin/users')

    expect(screen.getByText('pantalla de cambio')).toBeInTheDocument()
    expect(screen.queryByText('contenido protegido')).not.toBeInTheDocument()
  })

  it('deja pasar cuando no hay cambio pendiente', () => {
    useGetIdentity.mockReturnValue({ data: { must_change_password: false } })

    renderAt('/admin/users')

    expect(screen.getByText('contenido protegido')).toBeInTheDocument()
  })
})
