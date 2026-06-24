import type { HttpError } from '@refinedev/core'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useSessionStore } from '../store/sessionStore'
import type { UserIdentity } from '../types/auth.types'

vi.mock('../api/httpClient', () => ({
  authHttpClient: { post: vi.fn(), get: vi.fn() },
}))

import { authHttpClient } from '../api/httpClient'
import { authProvider } from './authProvider'

const post = vi.mocked(authHttpClient.post)
const get = vi.mocked(authHttpClient.get)

const USER: UserIdentity = {
  id: 1,
  username: 'ana',
  first_name: 'Ana',
  last_name: 'Pérez',
  role: 'SUPERVISOR',
  is_active: true,
  profile: null,
  must_change_password: false,
}

beforeEach(() => {
  vi.clearAllMocks()
  useSessionStore.getState().clear()
})

describe('authProvider.login', () => {
  it('guarda la sesión y redirige al éxito', async () => {
    post.mockResolvedValueOnce({ data: { access: 'acc', user: USER } })

    const result = await authProvider.login!({ username: 'ana', password: 'x' })

    expect(result).toMatchObject({ success: true, redirectTo: '/' })
    expect(useSessionStore.getState().accessToken).toBe('acc')
    expect(useSessionStore.getState().user).toMatchObject({ username: 'ana' })
  })

  it('devuelve error sin sesión ante credenciales inválidas', async () => {
    const error: HttpError = { message: 'Credenciales inválidas.', statusCode: 401 }
    post.mockRejectedValueOnce(error)

    const result = await authProvider.login!({ username: 'ana', password: 'mala' })

    expect(result.success).toBe(false)
    expect(result.error?.message).toBe('Credenciales inválidas.')
    expect(useSessionStore.getState().accessToken).toBeNull()
  })
})

describe('authProvider.logout', () => {
  it('limpia la sesión y redirige a /login', async () => {
    useSessionStore.getState().setSession('acc', USER)
    post.mockResolvedValueOnce({ data: { detail: 'Sesión cerrada.' } })

    const result = await authProvider.logout!({})

    expect(result).toMatchObject({ success: true, redirectTo: '/login' })
    expect(useSessionStore.getState().accessToken).toBeNull()
  })
})

describe('authProvider.check (refresh silencioso)', () => {
  it('autentica si ya hay access en memoria', async () => {
    useSessionStore.getState().setSession('acc', USER)
    const result = await authProvider.check!()
    expect(result).toEqual({ authenticated: true })
    expect(post).not.toHaveBeenCalled()
  })

  it('repone la sesión desde la cookie al cargar', async () => {
    post.mockResolvedValueOnce({ data: { access: 'nuevo' } })
    get.mockResolvedValueOnce({ data: USER })

    const result = await authProvider.check!()

    expect(result).toEqual({ authenticated: true })
    expect(useSessionStore.getState().accessToken).toBe('nuevo')
  })

  it('manda al login si no hay refresh válido', async () => {
    post.mockRejectedValueOnce({ message: 'x', statusCode: 401 })

    const result = await authProvider.check!()

    expect(result).toMatchObject({ authenticated: false, redirectTo: '/login' })
  })
})

describe('authProvider.onError', () => {
  it('cierra sesión ante 401', async () => {
    const result = await authProvider.onError!({ statusCode: 401 } as HttpError)
    expect(result).toMatchObject({ logout: true, redirectTo: '/login' })
  })

  it('ignora otros errores', async () => {
    const result = await authProvider.onError!({ statusCode: 500 } as HttpError)
    expect(result).toEqual({})
  })
})
