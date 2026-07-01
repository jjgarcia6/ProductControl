import { FieldError } from '@/components/custom/FieldError'

import { type RowReportType } from '../types/import.types'

/*
  Tabla presentacional del reporte de importación (F7): una fila por registro del archivo con
  su número, estado y errores por campo. Reutiliza `FieldError` (mismo lenguaje visual de error
  que los formularios). Sin estado ni llamadas: recibe `rows` por props. Tokens del theme.
*/

const STATUS_LABELS: Record<RowReportType['status'], string> = {
  valid: 'Válida',
  skipped: 'Omitida (duplicada)',
  error: 'Con error',
}

const STATUS_CLASSES: Record<RowReportType['status'], string> = {
  valid: 'text-success',
  skipped: 'text-muted-foreground',
  error: 'text-danger',
}

export function ImportReportTable({ rows }: { rows: RowReportType[] }) {
  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">El archivo no tiene filas de datos.</p>
  }

  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="border-b text-left text-muted-foreground">
          <th className="w-16 py-2 pr-4 font-medium">Fila</th>
          <th className="w-40 py-2 pr-4 font-medium">Estado</th>
          <th className="py-2 font-medium">Errores</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.row_number} className="border-b align-top">
            <td className="py-3 pr-4 font-medium text-foreground">{row.row_number}</td>
            <td className={`py-3 pr-4 font-medium ${STATUS_CLASSES[row.status]}`}>
              {STATUS_LABELS[row.status]}
            </td>
            <td className="py-3">
              {row.errors && Object.keys(row.errors).length > 0 ? (
                <ul className="flex flex-col gap-1">
                  {Object.entries(row.errors).map(([field, messages]) => (
                    <li key={field}>
                      <FieldError message={`${field}: ${messages.join(' ')}`} />
                    </li>
                  ))}
                </ul>
              ) : (
                <span className="text-muted-foreground">—</span>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
