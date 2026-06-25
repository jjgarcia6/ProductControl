/*
  Tipos de la feature directory. Re-exporta los schemas Zod generados del OpenAPI
  (src/shared/api/zod.ts) — fuente de verdad. NUNCA se escriben a mano (z.infer<>).
*/
import type { z } from 'zod'

import { schemas } from '@/shared/api/zod'

export const fichaReadSchema = schemas.FichaRead
export const fichaWriteSchema = schemas.FichaWrite
export const creditTermsReadSchema = schemas.CreditTermsRead
export const creditTermsWriteSchema = schemas.CreditTermsWrite

export type Ficha = z.infer<typeof fichaReadSchema>
export type FichaWriteInput = z.infer<typeof fichaWriteSchema>
export type CreditTerms = z.infer<typeof creditTermsReadSchema>
export type CreditTermsWriteInput = z.infer<typeof creditTermsWriteSchema>

export type FichaRole = Ficha['roles'][number]
export type FichaStatus = Ficha['status']
export type IdentificationType = Ficha['identification_type']
export type CreditFacet = CreditTerms['facet']

/** Etiquetas en español para los valores de enum del dominio (UI). */
export const ROLE_LABELS: Record<FichaRole, string> = {
  CLIENTE: 'Cliente',
  PROVEEDOR: 'Proveedor',
  RESPONSABLE_RUTA: 'Responsable de ruta',
  CHOFER: 'Chofer',
}

export const STATUS_LABELS: Record<FichaStatus, string> = {
  ACTIVO: 'Activo',
  BLOQUEADO: 'Bloqueado',
  INACTIVO: 'Inactivo',
}

export const IDENTIFICATION_TYPE_LABELS: Record<IdentificationType, string> = {
  CEDULA: 'Cédula',
  RUC: 'RUC',
  PASAPORTE: 'Pasaporte',
}

/** Faceta de crédito ⇄ rol que la habilita en la ficha. */
export const FACET_REQUIRED_ROLE: Record<CreditFacet, FichaRole> = {
  CLIENTE: 'CLIENTE',
  PROVEEDOR: 'PROVEEDOR',
}
