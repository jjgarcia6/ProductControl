/*
  Tipos de la feature products (F5). Re-exporta los schemas Zod generados del OpenAPI
  (src/shared/api/zod.ts) — fuente de verdad. NUNCA se escriben a mano (z.infer<>).
*/
import type { z } from 'zod'

import { schemas } from '@/shared/api/zod'

export const categoryReadSchema = schemas.CategoryRead
export const categoryWriteSchema = schemas.CategoryWrite
export const productReadSchema = schemas.ProductRead
export const productWriteSchema = schemas.ProductWrite
export const unitReadSchema = schemas.UnitOfMeasureRead
export const unitWriteSchema = schemas.UnitOfMeasureWrite

export type Category = z.infer<typeof categoryReadSchema>
export type CategoryWriteInput = z.infer<typeof categoryWriteSchema>
export type Product = z.infer<typeof productReadSchema>
export type ProductWriteInput = z.infer<typeof productWriteSchema>
export type UnitOfMeasure = z.infer<typeof unitReadSchema>
export type UnitOfMeasureWriteInput = z.infer<typeof unitWriteSchema>

export type IntakeType = Category['intake_type']

/** Etiquetas en español para los valores de enum del dominio (UI). */
export const INTAKE_TYPE_LABELS: Record<IntakeType, string> = {
  GAVETA: 'Gaveta',
  PESO: 'Peso',
}
