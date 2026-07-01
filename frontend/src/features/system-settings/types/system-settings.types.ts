/*
  Tipos de la feature system-settings (F8). Re-exporta los schemas Zod generados del
  OpenAPI (src/shared/api/zod.ts) — fuente de verdad. NUNCA se escriben a mano (z.infer<>).
*/
import type { z } from 'zod'

import { schemas } from '@/shared/api/zod'

export const systemSettingsReadSchema = schemas.SystemSettingsRead
export const systemSettingsUpdateSchema = schemas.PatchedSystemSettingsUpdate

export type SystemSettingsType = z.infer<typeof systemSettingsReadSchema>
export type SystemSettingsUpdateInput = z.infer<typeof systemSettingsUpdateSchema>
