import axios, { type AxiosError } from 'axios'

import { API_URL } from '@/shared/config/env'

import { normalizeError } from './errors'

/*
  Cliente HTTP del backend. El interceptor de respuesta traduce TODO error al contrato
  de Refine (§6.3) ANTES de que llegue a la app: así el dataProvider y los hooks nunca
  ven el cuerpo crudo del backend.
*/
export const httpClient = axios.create({
  baseURL: API_URL,
})

httpClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const statusCode = error.response?.status ?? 500
    return Promise.reject(normalizeError(statusCode, error.response?.data))
  },
)
