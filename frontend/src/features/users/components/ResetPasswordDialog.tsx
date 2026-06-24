import { useState } from 'react'

import { FieldError } from '@/components/custom/FieldError'

import type { ResetPasswordInput } from '../types/users.types'

/*
  Panel de reset administrativo de contraseña. Presentacional: recibe `onSubmit`, `isPending`,
  la contraseña temporal resultante (`temporaryPassword`, se muestra UNA vez) y un error
  opcional. El admin elige generar la temporal o definirla. Tokens del theme; cero hex.
*/

interface ResetPasswordDialogProps {
  username: string
  onSubmit: (values: ResetPasswordInput) => void
  onClose: () => void
  isPending: boolean
  temporaryPassword?: string | null
  errorMessage?: string | null
}

const inputClass =
  'h-11 w-full rounded-md border bg-surface px-3 text-base text-foreground outline-none ' +
  'focus:border-primary focus:ring-2 focus:ring-primary/40 disabled:opacity-60'

export function ResetPasswordDialog({
  username,
  onSubmit,
  onClose,
  isPending,
  temporaryPassword,
  errorMessage,
}: ResetPasswordDialogProps) {
  const [mode, setMode] = useState<'generate' | 'manual'>('generate')
  const [password, setPassword] = useState('')

  const submit = () => {
    if (mode === 'generate') onSubmit({ generate: true })
    else onSubmit({ temporary_password: password, generate: false })
  }

  if (temporaryPassword) {
    return (
      <section aria-label="Contraseña temporal" className="flex flex-col gap-3">
        <p className="text-sm text-muted-foreground">
          Contraseña temporal de <span className="font-medium text-foreground">{username}</span>.
          Comuníquela al usuario; deberá cambiarla en el primer acceso. No se mostrará otra vez.
        </p>
        <output className="rounded-md border bg-muted px-3 py-2 font-mono text-base text-foreground">
          {temporaryPassword}
        </output>
        <button
          type="button"
          onClick={onClose}
          className="h-11 self-start rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          Listo
        </button>
      </section>
    )
  }

  return (
    <section aria-label="Restablecer contraseña" className="flex flex-col gap-4">
      <p className="text-sm text-muted-foreground">
        Restablecer la contraseña de{' '}
        <span className="font-medium text-foreground">{username}</span> y forzar el cambio en el
        primer acceso.
      </p>

      <fieldset className="flex flex-col gap-2">
        <legend className="sr-only">Tipo de contraseña temporal</legend>
        <label className="flex min-h-11 items-center gap-2 text-sm text-foreground">
          <input
            type="radio"
            name="reset-mode"
            checked={mode === 'generate'}
            onChange={() => setMode('generate')}
            className="size-4 accent-primary"
          />
          Generar automáticamente
        </label>
        <label className="flex min-h-11 items-center gap-2 text-sm text-foreground">
          <input
            type="radio"
            name="reset-mode"
            checked={mode === 'manual'}
            onChange={() => setMode('manual')}
            className="size-4 accent-primary"
          />
          Definir manualmente
        </label>
      </fieldset>

      {mode === 'manual' ? (
        <div>
          <label htmlFor="temporary_password" className="mb-1 block text-sm font-medium text-foreground">
            Contraseña temporal
          </label>
          <input
            id="temporary_password"
            type="text"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className={inputClass}
          />
        </div>
      ) : null}

      <FieldError message={errorMessage ?? undefined} />

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          onClick={submit}
          disabled={isPending || (mode === 'manual' && password.length === 0)}
          className="h-11 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-60"
        >
          {isPending ? 'Restableciendo…' : 'Restablecer'}
        </button>
        <button
          type="button"
          onClick={onClose}
          className="h-11 rounded-md border px-4 text-sm font-medium text-foreground hover:bg-muted"
        >
          Cancelar
        </button>
      </div>
    </section>
  )
}
