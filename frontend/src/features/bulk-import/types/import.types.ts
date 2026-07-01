/*
  Tipos de la feature bulk-import (F7). Re-exporta los schemas Zod generados del OpenAPI
  (src/shared/api/zod.ts) — fuente de verdad. NUNCA se escriben a mano (z.infer<>).
*/
import type { z } from 'zod'

import { schemas } from '@/shared/api/zod'

export const importResultSchema = schemas.ImportResult
export const rowReportSchema = schemas.RowReport

export type ImportResultType = z.infer<typeof importResultSchema>
export type RowReportType = z.infer<typeof rowReportSchema>

/** Entidades importables (coinciden con el segmento de la ruta del backend). */
export type ImportEntity = 'products' | 'fichas'

/** Etiquetas en español de cada entidad importable (UI). */
export const ENTITY_LABELS: Record<ImportEntity, string> = {
  products: 'Productos',
  fichas: 'Fichas del Directorio',
}
