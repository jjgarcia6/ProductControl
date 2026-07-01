/*
  Tipos de la feature pricing (F6). Re-exporta los schemas Zod generados del OpenAPI
  (src/shared/api/zod.ts) — fuente de verdad. NUNCA se escriben a mano (z.infer<>).
*/
import type { z } from 'zod'

import { schemas } from '@/shared/api/zod'

export const priceListReadSchema = schemas.PriceListRead
export const priceListWriteSchema = schemas.PriceListWrite
export const priceListItemReadSchema = schemas.PriceListItemRead
export const priceListItemWriteSchema = schemas.PriceListItemWrite

export type PriceList = z.infer<typeof priceListReadSchema>
export type PriceListWriteInput = z.infer<typeof priceListWriteSchema>
export type PriceListItem = z.infer<typeof priceListItemReadSchema>
export type PriceListItemWriteInput = z.infer<typeof priceListItemWriteSchema>

export type PriceListType = PriceList['type']

/** Etiquetas en español para los valores de enum del dominio (UI). */
export const PRICE_LIST_TYPE_LABELS: Record<PriceListType, string> = {
  NORMAL: 'Normal',
  DESCARTE: 'Descarte',
}
