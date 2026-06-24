import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'

import { normalizeError } from '@/shared/api/errors'
import { API_URL } from '@/shared/config/env'

import { useSessionStore } from '../store/sessionStore'

/*
  Cliente HTTP con conciencia de sesión (§5.4). Lo usan el authProvider y el dataProvider
  'auth' (cambio de contraseña).

  - withCredentials: el refresh token viaja en la cookie httpOnly; sin esto no se envía.
  - Request: adjunta `Authorization: Bearer <access>` desde el store en memoria.
  - Response 401: intenta UN refresh silencioso (single-flight) y reintenta la petición
    original una sola vez. Si el refresh falla, limpia la sesión y redirige a /login.
  - Todo error sale normalizado al contrato de Refine (HttpError): la UI nunca ve el
    cuerpo crudo del backend.
*/

const REFRESH_URL = '/auth/refresh'
const AUTH_ROUTES = ['/auth/login', REFRESH_URL, '/auth/logout']

export const authHttpClient = axios.create({
  baseURL: API_URL,
  withCredentials: true,
})

authHttpClient.interceptors.request.use((config) => {
  const token = useSessionStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Single-flight: varias peticiones que fallan con 401 a la vez comparten UN solo refresh.
let refreshInFlight: Promise<string> | null = null

function refreshAccessToken(): Promise<string> {
  if (!refreshInFlight) {
    // axios "crudo" (sin interceptores) para no recursar sobre este mismo cliente.
    refreshInFlight = axios
      .post<{ access: string }>(`${API_URL}${REFRESH_URL}`, null, { withCredentials: true })
      .then((response) => {
        const access = response.data.access
        useSessionStore.getState().setAccessToken(access)
        return access
      })
      .finally(() => {
        refreshInFlight = null
      })
  }
  return refreshInFlight
}

function redirectToLogin(): void {
  if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
    window.location.assign('/login')
  }
}

interface RetriableConfig extends InternalAxiosRequestConfig {
  _retried?: boolean
}

authHttpClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as RetriableConfig | undefined
    const status = error.response?.status ?? 500
    const url = original?.url ?? ''
    const isAuthRoute = AUTH_ROUTES.some((route) => url.includes(route))

    if (status === 401 && original && !original._retried && !isAuthRoute) {
      original._retried = true
      try {
        const access = await refreshAccessToken()
        original.headers.Authorization = `Bearer ${access}`
        return authHttpClient(original)
      } catch {
        useSessionStore.getState().clear()
        redirectToLogin()
        return Promise.reject(normalizeError(401, error.response?.data))
      }
    }

    return Promise.reject(normalizeError(status, error.response?.data))
  },
)
