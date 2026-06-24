import axios, { AxiosError, type AxiosAdapter } from 'axios'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useSessionStore } from '../store/sessionStore'
import { authHttpClient } from './httpClient'

/*
  Verifica el interceptor de refresh: ante 401 hace UN refresh silencioso y reintenta la
  petición original una sola vez; si el refresh falla, limpia la sesión.
*/

const originalAdapter = authHttpClient.defaults.adapter

beforeEach(() => {
  vi.restoreAllMocks()
  useSessionStore.getState().clear()
})

afterEach(() => {
  authHttpClient.defaults.adapter = originalAdapter
})

function adapter401ThenOk(): AxiosAdapter {
  let calls = 0
  return async (config) => {
    calls += 1
    if (calls === 1) {
      throw new AxiosError('no autorizado', 'ERR_BAD_REQUEST', config, null, {
        status: 401,
        statusText: 'Unauthorized',
        data: { detail: 'La sesión expiró.' },
        headers: {},
        config,
      })
    }
    return { data: { ok: true }, status: 200, statusText: 'OK', headers: {}, config }
  }
}

describe('authHttpClient — interceptor de refresh', () => {
  it('refresca y reintenta una vez ante 401', async () => {
    useSessionStore.getState().setAccessToken('viejo')
    authHttpClient.defaults.adapter = adapter401ThenOk()
    const postSpy = vi
      .spyOn(axios, 'post')
      .mockResolvedValue({ data: { access: 'fresco' } })

    const response = await authHttpClient.get('/recurso-protegido')

    expect(response.data).toEqual({ ok: true })
    expect(postSpy).toHaveBeenCalledWith(
      expect.stringContaining('/auth/refresh'),
      null,
      expect.objectContaining({ withCredentials: true }),
    )
    expect(useSessionStore.getState().accessToken).toBe('fresco')
  })

  it('limpia la sesión si el refresh falla', async () => {
    useSessionStore.getState().setAccessToken('viejo')
    authHttpClient.defaults.adapter = adapter401ThenOk()
    vi.spyOn(axios, 'post').mockRejectedValue(new Error('refresh muerto'))
    // Ya estando en /login, el guard de redirección no toca window.location.assign
    // (jsdom no implementa la navegación y no permite redefinir assign).
    window.history.pushState({}, '', '/login')

    await expect(authHttpClient.get('/recurso-protegido')).rejects.toMatchObject({
      statusCode: 401,
    })
    expect(useSessionStore.getState().accessToken).toBeNull()
  })
})
