import { expect, test, type Page } from '@playwright/test'

/*
  Smoke del Directorio (cross-browser, incluye WebKit móvil por la config de Playwright).
  No depende del backend: mockea con page.route el refresh silencioso + identidad (perfil con
  permisos `directory`) y los endpoints de fichas. Ejercita el flujo principal (listar, crear)
  y verifica que el input de identificación mide ≥16px para que Safari iOS no haga zoom.
*/

const IDENTITY = {
  id: 1,
  username: 'jefe',
  first_name: '',
  last_name: '',
  role: 'JEFE',
  is_active: true,
  profile: {
    id: '0fe3e18a-fe08-4b53-83fc-fbd915a701be',
    name: 'Gestor Directorio',
    description: '',
    permissions: { directory: ['read', 'create', 'update'] },
    visible_sensitive_fields: [],
    auto_approval: false,
  },
  must_change_password: false,
}

const FICHA = {
  id: '610e000d-c216-40b3-a80c-6abfc27bd201',
  name: 'GARCIA ALMEIDA JIMMY JAVIER',
  identification_type: 'CEDULA',
  identification_number: '0920275229',
  email: 'jimmyjavier@outlook.com',
  phone: '0984169998',
  roles: ['CLIENTE', 'PROVEEDOR'],
  status: 'ACTIVO',
  user: null,
  created_at: '2026-06-25T20:00:00Z',
  updated_at: '2026-06-25T20:00:00Z',
}

/** Mockea la sesión (refresh silencioso + identidad) y los endpoints del Directorio. */
async function mockBackend(page: Page): Promise<void> {
  await page.route('**/auth/refresh', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ access: 'fake-access' }) }),
  )
  await page.route('**/auth/me', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(IDENTITY) }),
  )
  await page.route('**/directory/fichas**', (route) => {
    if (route.request().method() === 'POST') {
      const created = { ...FICHA, id: 'new-ficha-id', roles: ['CLIENTE'] }
      return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(created) })
    }
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([FICHA]) })
  })
}

test.describe('Directorio', () => {
  test.beforeEach(async ({ page }) => {
    await mockBackend(page)
  })

  test('carga la consola y lista las fichas', async ({ page }) => {
    await page.goto('/directory')

    await expect(page.getByRole('heading', { name: 'Directorio' })).toBeVisible()
    await expect(page.getByText('GARCIA ALMEIDA JIMMY JAVIER')).toBeVisible()
    await expect(page.getByText('0920275229')).toBeVisible()
    // Filtros de listado presentes.
    await expect(page.getByLabel('Filtrar por rol')).toBeVisible()
    await expect(page.getByLabel('Filtrar por estado')).toBeVisible()
  })

  test('crea una ficha desde el formulario', async ({ page }) => {
    await page.goto('/directory')

    await page.getByLabel('Nombre o razón social').fill('Distribuidora Andina')
    await page.getByLabel('Número').fill('1710034065')
    await page.getByLabel('Cliente').check()
    await page.getByRole('button', { name: 'Crear ficha' }).click()

    await expect(page.getByText('Ficha creada.')).toBeVisible()
  })

  test('el input de identificación mide ≥16px (sin zoom en iOS Safari)', async ({ page }) => {
    await page.goto('/directory')

    const fontSize = await page
      .locator('#identification_number')
      .evaluate((el) => Number.parseFloat(getComputedStyle(el).fontSize))
    expect(fontSize).toBeGreaterThanOrEqual(16)
  })
})
