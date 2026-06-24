import { useCustom } from '@refinedev/core'

import type { Profile } from '../types/profiles.types'

/*
  Listado de perfiles. useCustom (GET) de Refine contra el dataProvider 'auth' (cliente con
  Authorization + refresh silencioso). React Query vive DENTRO de Refine; no se monta nada
  paralelo. El endpoint devuelve un arreglo plano de perfiles vivos.
*/
export function useProfilesList() {
  const { query, result } = useCustom<Profile[]>({
    url: '/authz/profiles',
    method: 'get',
    config: {},
    dataProviderName: 'auth',
  })

  return {
    profiles: result.data ?? [],
    isLoading: query.isLoading,
    isError: query.isError,
    refetch: query.refetch,
  }
}
