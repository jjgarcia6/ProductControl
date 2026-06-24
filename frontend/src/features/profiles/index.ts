/*
  Contrato público de la feature profiles. Lo de afuera SOLO importa desde aquí.
*/
export { ProfilesAdminConsole } from './components/ProfilesAdminConsole'
export { PermissionMatrix } from './components/PermissionMatrix'
export { useProfilesList } from './hooks/useProfilesList'
export { useProfileAdminActions } from './hooks/useProfileAdminActions'
export { PERMISSION_CATALOG } from './types/profiles.types'
export type { Profile, ProfileAdminWriteInput } from './types/profiles.types'
