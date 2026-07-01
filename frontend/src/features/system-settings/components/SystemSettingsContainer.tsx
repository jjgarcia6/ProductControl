import { type HttpError } from '@refinedev/core'
import { useState } from 'react'

import { usePermissions } from '@/features/auth'

import { useSystemSettings } from '../hooks/useSystemSettings'
import type { SystemSettingsUpdateInput } from '../types/system-settings.types'
import { SystemSettingsForm } from './SystemSettingsForm'

/*
  Consola de configuración global (F8). Contenedor: orquesta el hook del singleton, aplica
  el gating por perfil (módulo `system-settings`) y resuelve los estados vacío/carga/error/
  éxito. El Jefe (`update`) edita; el Supervisor (`read`) ve en solo lectura. El error
  cruzado "al menos una base activa" (400 non_field_errors) se muestra como aviso general.
  Tokens del theme; cero hex.
*/

const cardClass = 'rounded-lg border bg-surface p-6'

export function SystemSettingsContainer() {
  const { canDo } = usePermissions()
  const canRead = canDo('system-settings', 'read')
  const canUpdate = canDo('system-settings', 'update')

  const { settings, isLoading, isError, refetch, update, isPending } = useSystemSettings()
  const [serverError, setServerError] = useState<string | undefined>(undefined)

  if (!canRead) {
    return (
      <div role="alert" className={cardClass}>
        <p className="text-sm text-muted-foreground">
          No tiene permiso para ver la configuración del sistema.
        </p>
      </div>
    )
  }

  if (isLoading) {
    return (
      <p role="status" aria-live="polite" className="text-muted-foreground">
        Cargando configuración…
      </p>
    )
  }

  if (isError || !settings) {
    return (
      <div role="alert" className="flex flex-col items-start gap-3 text-danger">
        <p>No se pudo cargar la configuración del sistema.</p>
        <button
          type="button"
          onClick={() => refetch()}
          className="h-11 rounded-md border px-4 text-sm font-medium text-foreground hover:bg-muted"
        >
          Reintentar
        </button>
      </div>
    )
  }

  const handleSubmit = (values: SystemSettingsUpdateInput) => {
    setServerError(undefined)
    update(values, {
      onError: (error: HttpError) => setServerError(error.message),
    })
  }

  return (
    <section aria-label="Bases de costeo" className={cardClass}>
      <SystemSettingsForm
        settings={settings}
        isPending={isPending}
        readOnly={!canUpdate}
        serverError={serverError}
        onSubmit={handleSubmit}
      />
    </section>
  )
}
