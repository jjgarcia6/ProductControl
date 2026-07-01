import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { type RowReportType } from '../types/import.types'
import { ImportReportTable } from './ImportReportTable'

/*
  ImportReportTable es presentacional: se prueba el render de estados (valid/skipped/error),
  los errores por campo y el estado vacío. Sin hooks ni red.
*/

describe('ImportReportTable', () => {
  it('muestra un mensaje cuando no hay filas', () => {
    render(<ImportReportTable rows={[]} />)
    expect(screen.getByText(/no tiene filas de datos/i)).toBeInTheDocument()
  })

  it('renderiza el estado de cada fila y los errores por campo', () => {
    const rows: RowReportType[] = [
      { row_number: 2, status: 'valid' },
      { row_number: 3, status: 'skipped' },
      { row_number: 4, status: 'error', errors: { category: ['No existe la categoría.'] } },
    ]

    render(<ImportReportTable rows={rows} />)

    expect(screen.getByText('Válida')).toBeInTheDocument()
    expect(screen.getByText('Omitida (duplicada)')).toBeInTheDocument()
    expect(screen.getByText('Con error')).toBeInTheDocument()
    expect(screen.getByText(/category: No existe la categoría\./)).toBeInTheDocument()
  })
})
