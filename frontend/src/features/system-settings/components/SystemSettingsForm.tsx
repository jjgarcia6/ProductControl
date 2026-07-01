import { zodResolver } from '@hookform/resolvers/zod'
import { Controller, useForm } from 'react-hook-form'
import { z } from 'zod'

import type { SystemSettingsType, SystemSettingsUpdateInput } from '../types/system-settings.types'

/*
  Formulario de configuración global (F8). Presentacional: dos toggles de costeo. RHF +
  zodResolver. La regla cruzada "al menos una base activa" se valida en cliente (aviso
  general, no atado a un control) y también llega del backend (400 non_field_errors) por
  `serverError`. `readOnly` deja los toggles deshabilitados (Supervisor). Tokens del theme;
  cero hex; áreas táctiles ≥44px.
*/

const formSchema = z
  .object({
    costing_nominal_enabled: z.boolean(),
    costing_effective_enabled: z.boolean(),
  })
  .refine((v) => v.costing_nominal_enabled || v.costing_effective_enabled, {
    message: 'Al menos una base de costeo (nominal o efectiva) debe permanecer activa.',
    path: ['costing_base'],
  })

type SystemSettingsFormValues = z.infer<typeof formSchema>

const errorClass = 'text-sm text-danger'

interface ToggleDef {
  name: keyof SystemSettingsFormValues
  label: string
  description: string
}

const TOGGLES: ToggleDef[] = [
  {
    name: 'costing_nominal_enabled',
    label: 'Costo nominal',
    description: 'Mostrar la base de costo nominal (peso de factura) en reportes y dashboards.',
  },
  {
    name: 'costing_effective_enabled',
    label: 'Costo efectivo',
    description: 'Mostrar la base de costo efectivo (peso real) en reportes y dashboards.',
  },
]

interface Props {
  settings: SystemSettingsType
  isPending: boolean
  readOnly: boolean
  serverError?: string
  onSubmit: (values: SystemSettingsUpdateInput) => void
}

export function SystemSettingsForm({ settings, isPending, readOnly, serverError, onSubmit }: Props) {
  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<SystemSettingsFormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      costing_nominal_enabled: settings.costing_nominal_enabled,
      costing_effective_enabled: settings.costing_effective_enabled,
    },
  })

  // El error cruzado (client) se registra bajo la ruta sintética `costing_base`.
  const crossError = (errors as Record<string, { message?: string }>).costing_base?.message
  const generalError = crossError ?? serverError

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-5">
      <fieldset disabled={readOnly} className="flex flex-col gap-4">
        <legend className="sr-only">Bases de costeo</legend>
        {TOGGLES.map((toggle) => (
          <Controller
            key={toggle.name}
            name={toggle.name}
            control={control}
            render={({ field }) => (
              <label className="flex min-h-11 cursor-pointer items-start gap-3">
                <input
                  type="checkbox"
                  role="switch"
                  checked={field.value}
                  onChange={(e) => field.onChange(e.target.checked)}
                  onBlur={field.onBlur}
                  disabled={readOnly}
                  aria-describedby={`${toggle.name}-desc`}
                  className="mt-1 h-5 w-5 rounded border accent-primary focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-60"
                />
                <span className="flex flex-col gap-0.5">
                  <span className="text-sm font-medium text-foreground">{toggle.label}</span>
                  <span id={`${toggle.name}-desc`} className="text-sm text-muted-foreground">
                    {toggle.description}
                  </span>
                </span>
              </label>
            )}
          />
        ))}
      </fieldset>

      {generalError ? (
        <p role="alert" className={errorClass}>
          {generalError}
        </p>
      ) : null}

      {readOnly ? null : (
        <button
          type="submit"
          disabled={isPending}
          className="h-11 self-start rounded-md bg-primary px-4 text-base font-medium text-primary-foreground transition-opacity hover:opacity-90 active:opacity-80 focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-60"
        >
          {isPending ? 'Guardando…' : 'Guardar cambios'}
        </button>
      )}
    </form>
  )
}
