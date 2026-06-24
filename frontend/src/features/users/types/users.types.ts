/*
  Tipos de la feature users. Re-exporta los schemas Zod generados del OpenAPI
  (src/shared/api/zod.ts) — fuente de verdad. NUNCA se escriben a mano (z.infer<>).
*/
import type { z } from 'zod'

import { schemas } from '@/shared/api/zod'

export const userAdminReadSchema = schemas.UserAdminRead
export const userAdminWriteSchema = schemas.UserAdminWrite
export const resetPasswordWriteSchema = schemas.ResetPasswordWrite
export const resetPasswordReadSchema = schemas.ResetPasswordRead

export type UserAdmin = z.infer<typeof userAdminReadSchema>
export type UserAdminWriteInput = z.infer<typeof userAdminWriteSchema>
export type ResetPasswordInput = z.infer<typeof resetPasswordWriteSchema>
