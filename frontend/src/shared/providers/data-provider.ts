import simpleRestProvider from '@refinedev/simple-rest'

import { httpClient } from '@/shared/api/http'
import { API_URL } from '@/shared/config/env'

/*
  dataProvider de Refine sobre REST. Reusa el cliente HTTP con el interceptor del contrato
  de errores (§6.3): los errores ya llegan normalizados a la forma de Refine.
*/
export const dataProvider = simpleRestProvider(API_URL, httpClient)
