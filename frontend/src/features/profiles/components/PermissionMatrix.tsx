import { ACTION_LABELS, MODULE_LABELS } from '../types/profiles.types'

/*
  Matriz de permisos (módulo × acción). Presentacional: recibe el catálogo, el valor actual
  y `onChange`; sin estado propio ni llamadas a la API. Tokens del theme (cero hex); celdas
  táctiles ≥44px. Es defensa secundaria: la autorización real la decide el backend.
*/

type Permissions = Record<string, string[]>

interface PermissionMatrixProps {
  catalog: Readonly<Record<string, readonly string[]>>
  value: Permissions
  onChange: (next: Permissions) => void
  disabled?: boolean
}

export function PermissionMatrix({
  catalog,
  value,
  onChange,
  disabled = false,
}: PermissionMatrixProps) {
  const toggle = (module: string, action: string, checked: boolean) => {
    const current = new Set(value[module] ?? [])
    if (checked) current.add(action)
    else current.delete(action)
    const merged = [...current]
    const next: Permissions = { ...value, [module]: merged }
    if (merged.length === 0) delete next[module]
    onChange(next)
  }

  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="border-b text-left text-muted-foreground">
          <th className="py-2 pr-4 font-medium">Módulo</th>
          <th className="py-2 font-medium">Acciones</th>
        </tr>
      </thead>
      <tbody>
        {Object.entries(catalog).map(([module, actions]) => (
          <tr key={module} className="border-b align-top">
            <th scope="row" className="py-3 pr-4 text-left font-medium text-foreground">
              {MODULE_LABELS[module] ?? module}
            </th>
            <td className="py-3">
              <div className="flex flex-wrap gap-x-6 gap-y-2">
                {actions.map((action) => {
                  const id = `perm-${module}-${action}`
                  const checked = value[module]?.includes(action) ?? false
                  return (
                    <label
                      key={action}
                      htmlFor={id}
                      className="flex min-h-11 items-center gap-2 text-foreground"
                    >
                      <input
                        id={id}
                        type="checkbox"
                        checked={checked}
                        disabled={disabled}
                        onChange={(event) => toggle(module, action, event.target.checked)}
                        className="size-4 accent-primary disabled:opacity-60"
                      />
                      {ACTION_LABELS[action] ?? action}
                    </label>
                  )
                })}
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
