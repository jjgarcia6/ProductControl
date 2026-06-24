import { useGetIdentity } from '@refinedev/core'

import type { ProfileType, UserIdentity } from '../types/auth.types'

/*
  Gating por perfil (F2, access-control). Deriva del perfil que viaja en la identidad
  (`me`) los helpers `canDo` / `canSee`. Es DEFENSA SECUNDARIA: oculta acciones/columnas
  en la UI. La autoritativa es el backend — un campo omitido por el serializer nunca
  llega al cliente y una acción denegada responde 403.
*/

export interface PermissionHelpers {
  profile: ProfileType | null
  /** ¿El perfil permite `action` sobre `module`? */
  canDo: (module: string, action: string) => boolean
  /** ¿El perfil puede ver el campo sensible `resource.field`? */
  canSee: (resource: string, field: string) => boolean
}

/** Lógica pura de gating derivada del perfil. Testeable sin contexto de Refine. */
export function derivePermissions(profile: ProfileType | null): PermissionHelpers {
  return {
    profile,
    canDo: (module, action) => profile?.permissions?.[module]?.includes(action) ?? false,
    canSee: (resource, field) =>
      profile?.visible_sensitive_fields?.includes(`${resource}.${field}`) ?? false,
  }
}

/** Hook de gating: obtiene la identidad de Refine y expone los helpers de permisos. */
export function usePermissions(): PermissionHelpers {
  const { data: identity } = useGetIdentity<UserIdentity>()
  return derivePermissions(identity?.profile ?? null)
}
