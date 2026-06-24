import simpleRestProvider from '@refinedev/simple-rest'

import { API_URL } from '@/shared/config/env'

import { authHttpClient } from '../api/httpClient'

/*
  dataProvider 'auth' de Refine sobre el cliente con conciencia de sesión (Authorization +
  refresh silencioso). Lo usa useChangePassword (useCustomMutation con dataProviderName
  'auth'), separado del dataProvider de negocio para que las peticiones autenticadas de
  auth pasen por el cliente correcto.
*/
export const authDataProvider = simpleRestProvider(API_URL, authHttpClient)
