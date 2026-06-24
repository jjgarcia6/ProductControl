/*
  Tipos de la feature auth. Re-exporta los schemas Zod generados del OpenAPI
  (src/shared/api/zod.ts) — fuente de verdad de tipos. NUNCA se escriben a mano:
  se derivan con z.infer<>. Si el contrato del backend cambia, `npm run codegen`
  regenera y estos tipos se actualizan solos.
*/
import type { z } from 'zod'

import { schemas } from '@/shared/api/zod'

export const loginSchema = schemas.Login
export const changePasswordSchema = schemas.ChangePassword
export const userIdentitySchema = schemas.UserIdentity
export const tokenResponseSchema = schemas.TokenResponse
export const accessTokenSchema = schemas.AccessToken

export type LoginInput = z.infer<typeof loginSchema>
export type ChangePasswordInput = z.infer<typeof changePasswordSchema>
export type UserIdentity = z.infer<typeof userIdentitySchema>
export type Role = UserIdentity['role']
