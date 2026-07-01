import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { SystemSettingsType } from '../types/system-settings.types'
import { SystemSettingsForm } from './SystemSettingsForm'

/*
  SystemSettingsForm es presentacional: se prueba el render de los toggles, el modo solo
  lectura (Supervisor), la validación cruzada de cliente (no ambas bases desactivadas), el
  payload de éxito y el mapeo del error general del backend (400 non_field_errors).
*/

const onSubmit = vi.fn()

const settings: SystemSettingsType = {
  costing_nominal_enabled: true,
  costing_effective_enabled: true,
  created_at: '2026-07-01T00:00:00Z',
  updated_at: '2026-07-01T00:00:00Z',
}

function renderForm(props: Partial<Parameters<typeof SystemSettingsForm>[0]> = {}) {
  return render(
    <SystemSettingsForm
      settings={settings}
      isPending={false}
      readOnly={false}
      onSubmit={onSubmit}
      {...props}
    />,
  )
}

describe('SystemSettingsForm', () => {
  beforeEach(() => {
    onSubmit.mockReset()
  })

  it('renderiza los dos toggles marcados según la configuración', () => {
    renderForm()
    const switches = screen.getAllByRole('switch')
    expect(switches).toHaveLength(2)
    switches.forEach((s) => expect(s).toBeChecked())
  })

  it('en solo lectura deshabilita los toggles y oculta el botón guardar', () => {
    renderForm({ readOnly: true })
    screen.getAllByRole('switch').forEach((s) => expect(s).toBeDisabled())
    expect(screen.queryByRole('button', { name: /guardar/i })).not.toBeInTheDocument()
  })

  it('bloquea desactivar ambas bases y muestra el aviso general (validación cliente)', async () => {
    renderForm()

    fireEvent.click(screen.getByRole('switch', { name: /costo nominal/i }))
    fireEvent.click(screen.getByRole('switch', { name: /costo efectivo/i }))
    fireEvent.click(screen.getByRole('button', { name: /guardar/i }))

    expect(
      await screen.findByText(/al menos una base de costeo .* debe permanecer activa/i),
    ).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('envía el payload al desactivar solo una base', async () => {
    renderForm()
    fireEvent.click(screen.getByRole('switch', { name: /costo efectivo/i })) // desactiva efectivo
    fireEvent.click(screen.getByRole('button', { name: /guardar/i }))

    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith(
        { costing_nominal_enabled: true, costing_effective_enabled: false },
        expect.anything(),
      ),
    )
  })

  it('muestra el error general del servidor (400 non_field_errors)', () => {
    renderForm({
      serverError: 'Al menos una base de costeo (nominal o efectiva) MUST permanecer activa.',
    })
    expect(screen.getByRole('alert')).toHaveTextContent(/al menos una base de costeo/i)
  })
})
