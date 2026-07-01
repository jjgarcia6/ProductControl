import { type HttpError } from '@refinedev/core'
import { useState } from 'react'

import { usePermissions } from '@/features/auth'
import { usePriceLists } from '@/features/pricing'

import { useAssignPriceList } from '../hooks/useAssignPriceList'
import { type Ficha } from '../types/directory.types'

/*
  Selector de lista de precios de una ficha de cliente (F6). Se muestra SOLO si la ficha tiene el
  rol CLIENTE; la asignación se autoriza por el perfil (F2, módulo `directory` en `update`).
  Presentacional-ligero: encapsula usePriceLists + useAssignPriceList. Tokens del theme; cero hex.
*/

const inputClass =
  'h-11 rounded-md border bg-surface px-3 text-base text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40'
const labelClass = 'flex flex-col gap-1 text-sm text-muted-foreground'
const errorClass = 'text-sm text-danger'

interface Props {
  ficha: Ficha
}

export function PriceListSelect({ ficha }: Props) {
  const { canDo } = usePermissions()
  const canManage = canDo('directory', 'update')

  const { priceLists } = usePriceLists()
  const { assign, isPending } = useAssignPriceList()

  const [value, setValue] = useState<string>(ficha.price_list ?? '')
  const [fieldError, setFieldError] = useState<string | undefined>(undefined)

  if (!ficha.roles.includes('CLIENTE')) return null

  const onChange = (next: string) => {
    setValue(next)
    setFieldError(undefined)
    assign(ficha.id, next || null, {
      onError: (error: HttpError) => {
        const messages = error.errors?.price_list
        setFieldError(
          messages ? (Array.isArray(messages) ? messages[0] : String(messages)) : error.message,
        )
        setValue(ficha.price_list ?? '')
      },
    })
  }

  return (
    <label className={labelClass}>
      Lista de precios
      <select
        className={inputClass}
        value={value}
        disabled={!canManage || isPending}
        aria-invalid={Boolean(fieldError)}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">Sin lista asignada</option>
        {priceLists.map((priceList) => (
          <option key={priceList.id} value={priceList.id}>
            {priceList.name}
          </option>
        ))}
      </select>
      {fieldError ? <span className={errorClass}>{fieldError}</span> : null}
    </label>
  )
}
