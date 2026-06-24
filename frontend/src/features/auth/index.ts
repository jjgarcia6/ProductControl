/*
  Contrato público de la feature auth. Lo de afuera SOLO importa desde aquí.
*/
export { authProvider } from './providers/authProvider'
export { authDataProvider } from './providers/authDataProvider'
export { LoginContainer } from './components/LoginContainer'
export { ChangePasswordForm } from './components/ChangePasswordForm'
export { useChangePassword } from './hooks/useChangePassword'
export { useSessionStore } from './store/sessionStore'
export type {
  UserIdentity,
  Role,
  LoginInput,
  ChangePasswordInput,
} from './types/auth.types'
