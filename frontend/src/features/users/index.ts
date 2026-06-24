/*
  Contrato público de la feature users. Lo de afuera SOLO importa desde aquí.
*/
export { UsersAdminConsole } from './components/UsersAdminConsole'
export { UserForm } from './components/UserForm'
export { ResetPasswordDialog } from './components/ResetPasswordDialog'
export { useUsersList } from './hooks/useUsersList'
export { useUserMutations } from './hooks/useUserMutations'
export { useUserAdminActions } from './hooks/useUserAdminActions'
export type { UserAdmin, UserAdminWriteInput, ResetPasswordInput } from './types/users.types'
