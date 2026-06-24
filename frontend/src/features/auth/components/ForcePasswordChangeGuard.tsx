import { useGetIdentity } from '@refinedev/core'
import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router'

import type { UserIdentity } from '../types/auth.types'

/*
  Guard de cambio de contraseña forzado (F3). Si la identidad (`me`) indica
  `must_change_password`, bloquea la navegación y redirige a la pantalla de cambio hasta
  completarlo. Es defensa secundaria de UX: el backend además rechaza (403) cualquier
  operación distinta del cambio mientras el flag esté activo (middleware).
*/

const CHANGE_PASSWORD_PATH = '/account/change-password'

export function ForcePasswordChangeGuard({ children }: { children: ReactNode }) {
  const { data: identity } = useGetIdentity<UserIdentity>()
  const location = useLocation()

  if (
    identity?.must_change_password &&
    location.pathname !== CHANGE_PASSWORD_PATH
  ) {
    return <Navigate to={CHANGE_PASSWORD_PATH} replace />
  }

  return <>{children}</>
}
