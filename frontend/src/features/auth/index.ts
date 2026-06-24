/*
  Contrato público de la feature auth. Lo de afuera SOLO importa desde aquí.
*/
export { authProvider } from './providers/authProvider'
export { authDataProvider } from './providers/authDataProvider'
export { LoginContainer } from './components/LoginContainer'
export { ChangePasswordForm } from './components/ChangePasswordForm'
export { ForcePasswordChangeGuard } from './components/ForcePasswordChangeGuard'
export { useChangePassword } from './hooks/useChangePassword'
export { usePermissions, derivePermissions } from './hooks/usePermissions'
export type { PermissionHelpers } from './hooks/usePermissions'
export { useSessionStore } from './store/sessionStore'
export type {
  UserIdentity,
  Role,
  ProfileType,
  LoginInput,
  ChangePasswordInput,
} from './types/auth.types'
