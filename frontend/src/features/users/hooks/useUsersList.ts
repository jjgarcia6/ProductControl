import { useCustom } from '@refinedev/core'

import type { UserAdmin } from '../types/users.types'

/*
  Listado de usuarios. useCustom (GET) de Refine contra el dataProvider 'auth'. React Query
  vive DENTRO de Refine. El endpoint devuelve un arreglo plano de usuarios.
*/
export function useUsersList() {
  const { query, result } = useCustom<UserAdmin[]>({
    url: '/auth/users',
    method: 'get',
    config: {},
    dataProviderName: 'auth',
  })

  return {
    users: result.data ?? [],
    isLoading: query.isLoading,
    isError: query.isError,
    refetch: query.refetch,
  }
}
