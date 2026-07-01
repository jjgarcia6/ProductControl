import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { type ImportResultType } from '../types/import.types'
import { ImportWizard } from './ImportWizard'

/*
  ImportWizard: se prueba el gating por perfil (sin permiso no muestra el asistente), el flujo
  previsualizar → confirmar (confirmar habilitado solo sin filas en error) y el bloqueo cuando
  hay filas en error. Los hooks asíncronos se mockean.
*/

let canDoReturn = true
const previewMock = vi.fn()
const commitMock = vi.fn()

vi.mock('@/features/auth', () => ({
  usePermissions: () => ({ canDo: () => canDoReturn }),
}))
vi.mock('../hooks/useImportDryRun', () => ({
  useImportDryRun: () => ({ preview: previewMock, isPending: false }),
}))
vi.mock('../hooks/useImportCommit', () => ({
  useImportCommit: () => ({ commit: commitMock, isPending: false }),
}))
vi.mock('../hooks/useImportTemplate', () => ({
  useImportTemplate: () => ({ download: vi.fn().mockResolvedValue(undefined) }),
}))

function uploadFile() {
  const input = screen.getByLabelText(/archivo csv o excel/i)
  const file = new File(['name\n'], 'p.csv', { type: 'text/csv' })
  fireEvent.change(input, { target: { files: [file] } })
}

describe('ImportWizard', () => {
  beforeEach(() => {
    canDoReturn = true
    previewMock.mockReset()
    commitMock.mockReset()
  })

  it('no muestra el asistente a un perfil sin permiso', () => {
    canDoReturn = false
    render(<ImportWizard />)
    expect(screen.getByText(/no tiene permiso para importar/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /previsualizar/i })).not.toBeInTheDocument()
  })

  it('deshabilita previsualizar sin archivo', () => {
    render(<ImportWizard />)
    expect(screen.getByRole('button', { name: /previsualizar/i })).toBeDisabled()
  })

  it('previsualiza y habilita confirmar cuando no hay filas en error', () => {
    const report: ImportResultType = {
      dry_run: true,
      inserted: 0,
      skipped: 0,
      rows: [{ row_number: 2, status: 'valid' }],
    }
    previewMock.mockImplementation((_entity, _file, callbacks) => callbacks.onSuccess(report))

    render(<ImportWizard />)
    uploadFile()
    fireEvent.click(screen.getByRole('button', { name: /previsualizar/i }))

    expect(previewMock).toHaveBeenCalledWith('products', expect.any(File), expect.anything())
    expect(screen.getByText('Previsualización')).toBeInTheDocument()

    const confirm = screen.getByRole('button', { name: /confirmar importación/i })
    expect(confirm).toBeEnabled()
    fireEvent.click(confirm)
    expect(commitMock).toHaveBeenCalledWith('products', expect.any(File), expect.anything())
  })

  it('bloquea confirmar cuando hay filas en error', () => {
    const report: ImportResultType = {
      dry_run: true,
      inserted: 0,
      skipped: 0,
      rows: [{ row_number: 2, status: 'error', errors: { name: ['Requerido.'] } }],
    }
    previewMock.mockImplementation((_entity, _file, callbacks) => callbacks.onSuccess(report))

    render(<ImportWizard />)
    uploadFile()
    fireEvent.click(screen.getByRole('button', { name: /previsualizar/i }))

    expect(screen.getByRole('button', { name: /confirmar importación/i })).toBeDisabled()
    expect(screen.getByText(/corrija las filas con error/i)).toBeInTheDocument()
  })
})
