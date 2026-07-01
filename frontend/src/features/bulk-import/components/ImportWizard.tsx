import { type HttpError } from '@refinedev/core'
import { useState } from 'react'

import { usePermissions } from '@/features/auth'

import { useImportCommit } from '../hooks/useImportCommit'
import { useImportDryRun } from '../hooks/useImportDryRun'
import { useImportTemplate } from '../hooks/useImportTemplate'
import { ENTITY_LABELS, type ImportEntity, type ImportResultType } from '../types/import.types'
import { ImportReportTable } from './ImportReportTable'

/*
  Asistente de importación masiva (F7). Contenedor: orquesta los hooks y los pasos
  entidad → plantilla → carga → previsualización (dry-run) → confirmación. Gating por perfil
  (módulo `bulk-import`, acción `create`): DEFENSA SECUNDARIA, la autoritativa es el backend.
  Estados vacío/carga/error/éxito. Confirmar solo se habilita sin filas en error. Cero hex
  (tokens del theme); áreas táctiles ≥44px (h-11).
*/

const cardClass = 'rounded-lg border bg-surface p-5'
const ENTITIES: ImportEntity[] = ['products', 'fichas']

export function ImportWizard() {
  const { canDo } = usePermissions()
  const canImport = canDo('bulk-import', 'create')

  const { download } = useImportTemplate()
  const { preview, isPending: isPreviewing } = useImportDryRun()
  const { commit, isPending: isCommitting } = useImportCommit()

  const [entity, setEntity] = useState<ImportEntity>('products')
  const [file, setFile] = useState<File | null>(null)
  const [fileInputKey, setFileInputKey] = useState(0)
  const [report, setReport] = useState<ImportResultType | null>(null)
  const [committed, setCommitted] = useState<ImportResultType | null>(null)
  const [error, setError] = useState<string | undefined>(undefined)

  if (!canImport) {
    return (
      <div role="alert" className={cardClass}>
        <p className="text-sm text-muted-foreground">
          No tiene permiso para importar. Solicite acceso al módulo de importación.
        </p>
      </div>
    )
  }

  const resetFlow = () => {
    setReport(null)
    setCommitted(null)
    setError(undefined)
  }

  const onEntityChange = (next: ImportEntity) => {
    setEntity(next)
    setFile(null)
    setFileInputKey((key) => key + 1)
    resetFlow()
  }

  const onFileChange = (selected: File | null) => {
    setFile(selected)
    resetFlow()
  }

  const onError = (err: HttpError) => setError(err.message)

  const handleDownloadTemplate = () => {
    setError(undefined)
    download(entity).catch(() => setError('No se pudo descargar la plantilla.'))
  }

  const handlePreview = () => {
    if (!file) return
    setError(undefined)
    setCommitted(null)
    preview(entity, file, { onSuccess: setReport, onError })
  }

  const handleCommit = () => {
    if (!file) return
    setError(undefined)
    commit(entity, file, {
      onSuccess: (result) => {
        setCommitted(result)
        setReport(null)
        setFile(null)
        setFileInputKey((key) => key + 1)
      },
      onError,
    })
  }

  const errorRows = report?.rows.filter((row) => row.status === 'error').length ?? 0
  const canConfirm = report !== null && errorRows === 0 && file !== null && !isCommitting

  return (
    <div className="flex flex-col gap-6">
      <section aria-label="Configuración de la importación" className={cardClass}>
        <div className="flex flex-col gap-4">
          <fieldset className="flex flex-col gap-2">
            <legend className="text-sm font-medium text-foreground">Entidad a importar</legend>
            <div className="flex flex-wrap gap-2">
              {ENTITIES.map((value) => (
                <label
                  key={value}
                  className={`flex h-11 cursor-pointer items-center gap-2 rounded-md border px-4 text-sm font-medium ${
                    entity === value
                      ? 'border-primary bg-primary/10 text-foreground'
                      : 'text-muted-foreground hover:bg-muted'
                  }`}
                >
                  <input
                    type="radio"
                    name="entity"
                    value={value}
                    checked={entity === value}
                    onChange={() => onEntityChange(value)}
                    className="sr-only"
                  />
                  {ENTITY_LABELS[value]}
                </label>
              ))}
            </div>
          </fieldset>

          <button
            type="button"
            onClick={handleDownloadTemplate}
            className="h-11 w-fit rounded-md border px-4 text-sm font-medium text-foreground hover:bg-muted"
          >
            Descargar plantilla ({ENTITY_LABELS[entity]})
          </button>

          <div className="flex flex-col gap-2">
            <label htmlFor="import-file" className="text-sm font-medium text-foreground">
              Archivo CSV o Excel (.xlsx)
            </label>
            <input
              id="import-file"
              key={fileInputKey}
              type="file"
              accept=".csv,.xlsx"
              onChange={(event) => onFileChange(event.target.files?.[0] ?? null)}
              className="text-sm text-foreground file:mr-4 file:h-11 file:rounded-md file:border file:bg-muted file:px-4 file:text-sm file:font-medium"
            />
          </div>

          <button
            type="button"
            onClick={handlePreview}
            disabled={!file || isPreviewing}
            className="h-11 w-fit rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60"
          >
            {isPreviewing ? 'Previsualizando…' : 'Previsualizar'}
          </button>
        </div>
      </section>

      {error ? (
        <div role="alert" className={`${cardClass} text-danger`}>
          {error}
        </div>
      ) : null}

      {committed ? (
        <div role="status" aria-live="polite" className={`${cardClass} text-success`}>
          Importación confirmada: {committed.inserted} insertadas, {committed.skipped} omitidas.
        </div>
      ) : null}

      {report ? (
        <section aria-label="Reporte de previsualización" className={cardClass}>
          <div className="mb-4 flex flex-col gap-1">
            <h2 className="text-lg font-semibold text-foreground">Previsualización</h2>
            <p className="text-sm text-muted-foreground">
              {report.rows.length} filas · {errorRows} con error ·{' '}
              {report.skipped} a omitir por duplicado.
            </p>
          </div>

          <ImportReportTable rows={report.rows} />

          <div className="mt-5 flex items-center gap-3">
            <button
              type="button"
              onClick={handleCommit}
              disabled={!canConfirm}
              className="h-11 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60"
            >
              {isCommitting ? 'Confirmando…' : 'Confirmar importación'}
            </button>
            {errorRows > 0 ? (
              <p className="text-sm text-danger">
                Corrija las filas con error antes de confirmar.
              </p>
            ) : null}
          </div>
        </section>
      ) : null}
    </div>
  )
}
