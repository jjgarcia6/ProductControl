/*
  Tipos de la feature profiles. Re-exporta los schemas Zod generados del OpenAPI
  (src/shared/api/zod.ts) — fuente de verdad. NUNCA se escriben a mano (z.infer<>).
*/
import type { z } from 'zod'

import { schemas } from '@/shared/api/zod'

export const profileReadSchema = schemas.ProfileRead
export const profileAdminWriteSchema = schemas.PatchedProfileAdminWrite

export type Profile = z.infer<typeof profileReadSchema>
export type ProfileAdminWriteInput = z.infer<typeof profileAdminWriteSchema>

/*
  Catálogo de permisos conocido por el cliente para pintar la matriz (módulo × acción).
  Espeja el catálogo del backend (`apps/authz/catalog.py`). Mientras el backend no exponga
  el catálogo por API, vive aquí como dato de referencia; una fase posterior puede sustituirlo
  por un endpoint para no mantener dos fuentes. La autorización real la decide el backend.
*/
export const PERMISSION_CATALOG: Readonly<Record<string, readonly string[]>> = {
  'access-control': ['read', 'create', 'update'],
}

export const ACTION_LABELS: Readonly<Record<string, string>> = {
  read: 'Ver',
  create: 'Crear',
  update: 'Editar',
}

export const MODULE_LABELS: Readonly<Record<string, string>> = {
  'access-control': 'Control de acceso',
}
