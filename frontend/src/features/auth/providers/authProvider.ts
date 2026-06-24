import type { AuthProvider, HttpError } from '@refinedev/core'

import { authHttpClient } from '../api/httpClient'
import { useSessionStore } from '../store/sessionStore'
import {
  accessTokenSchema,
  tokenResponseSchema,
  userIdentitySchema,
} from '../types/auth.types'

/*
  authProvider de Refine (§5 UI). Concentra login/logout/check/getIdentity/onError.

  - El access vive en memoria (sessionStore); el refresh en cookie httpOnly.
  - `check` hace el REFRESH SILENCIOSO al cargar la app: como el access se pierde al
    recargar, intenta reponerlo desde la cookie antes de mandar al login.
  - Las respuestas se validan contra los schemas Zod generados del OpenAPI.
*/

const GENERIC_LOGIN_ERROR = 'No se pudo iniciar sesión. Intente nuevamente.'

export const authProvider: AuthProvider = {
  login: async ({ username, password }) => {
    try {
      const response = await authHttpClient.post('/auth/login', { username, password })
      const { access, user } = tokenResponseSchema.parse(response.data)
      useSessionStore.getState().setSession(access, user)
      return { success: true, redirectTo: '/' }
    } catch (error) {
      const message = (error as HttpError)?.message ?? GENERIC_LOGIN_ERROR
      return {
        success: false,
        error: { name: 'Error de acceso', message },
      }
    }
  },

  logout: async () => {
    try {
      await authHttpClient.post('/auth/logout')
    } catch {
      // El logout del backend es idempotente; limpiamos la sesión local pase lo que pase.
    }
    useSessionStore.getState().clear()
    return { success: true, redirectTo: '/login' }
  },

  check: async () => {
    if (useSessionStore.getState().accessToken) {
      return { authenticated: true }
    }
    try {
      const refreshed = await authHttpClient.post('/auth/refresh')
      const { access } = accessTokenSchema.parse(refreshed.data)
      const me = await authHttpClient.get('/auth/me')
      const user = userIdentitySchema.parse(me.data)
      useSessionStore.getState().setSession(access, user)
      return { authenticated: true }
    } catch {
      useSessionStore.getState().clear()
      return { authenticated: false, redirectTo: '/login' }
    }
  },

  getIdentity: async () => {
    const cached = useSessionStore.getState().user
    if (cached) return cached
    try {
      const me = await authHttpClient.get('/auth/me')
      const user = userIdentitySchema.parse(me.data)
      const token = useSessionStore.getState().accessToken
      if (token) useSessionStore.getState().setSession(token, user)
      return user
    } catch {
      return null
    }
  },

  onError: async (error) => {
    if ((error as HttpError)?.statusCode === 401) {
      return { logout: true, redirectTo: '/login', error }
    }
    return {}
  },

  getPermissions: async () => useSessionStore.getState().user?.role ?? null,
}
