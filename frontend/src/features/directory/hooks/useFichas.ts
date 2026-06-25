import { useCustom } from '@refinedev/core'
import { z } from 'zod'

import { type Ficha, fichaReadSchema } from '../types/directory.types'

/*
  Listado de fichas del Directorio. useCustom (GET) de Refine contra el dataProvider 'auth'
  (lleva el Authorization). El endpoint devuelve un arreglo plano. Filtros opcionales por rol
  y estado; INACTIVO se excluye por defecto salvo include_inactive. La respuesta se valida
  contra el schema Zod generado (Fase 0) antes de exponerla.
*/

export interface FichaFilters {
  role?: string
  status?: string
  includeInactive?: boolean
}

const listSchema = z.array(fichaReadSchema)

export function useFichas(filters: FichaFilters = {}) {
  const query: Record<string, string> = {}
  if (filters.role) query.role = filters.role
  if (filters.status) query.status = filters.status
  if (filters.includeInactive) query.include_inactive = 'true'

  const { query: q, result } = useCustom<Ficha[]>({
    url: '/directory/fichas',
    method: 'get',
    config: { query },
    dataProviderName: 'auth',
  })

  const parsed = listSchema.safeParse(result.data ?? [])

  return {
    fichas: parsed.success ? parsed.data : [],
    isLoading: q.isLoading,
    isError: q.isError || !parsed.success,
    refetch: q.refetch,
  }
}
