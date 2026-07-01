import { expect, test, type Page } from '@playwright/test'

/*
  Smoke del maestro de precios (cross-browser, incluye WebKit móvil por la config de Playwright).
  No depende del backend: mockea con page.route el refresh silencioso + identidad (perfil con
  permisos `pricing`) y los endpoints de listas/ítems/productos. Ejercita el flujo principal
  (listar listas, ver precios, alta de precio) y verifica que el input de precio mide ≥16px para
  que Safari iOS no haga zoom con los decimales.
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
    name: 'Gestor Precios',
    description: '',
    permissions: { pricing: ['read', 'create', 'update'] },
    visible_sensitive_fields: [],
    auto_approval: false,
  },
  must_change_password: false,
}

const PRICE_LIST = {
  id: '610e000d-c216-40b3-a80c-6abfc27bd201',
  name: 'Mayorista',
  type: 'NORMAL',
  created_at: '2026-06-25T20:00:00Z',
  updated_at: '2026-06-25T20:00:00Z',
}

const PRODUCT = {
  id: '33333333-3333-4333-8333-333333333333',
  name: 'Tomate riñón',
  category: '11111111-1111-4111-8111-111111111111',
  category_name: 'Verduras',
  unit_of_measure: '22222222-2222-4222-8222-222222222222',
  unit_of_measure_name: 'Libras',
  created_at: '2026-06-25T20:00:00Z',
  updated_at: '2026-06-25T20:00:00Z',
}

/** Mockea la sesión (refresh silencioso + identidad) y los endpoints de pricing/products. */
async function mockBackend(page: Page): Promise<void> {
  await page.route('**/auth/refresh', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ access: 'fake-access' }),
    }),
  )
  await page.route('**/auth/me', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(IDENTITY) }),
  )
  await page.route('**/products/products**', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([PRODUCT]) }),
  )
  // Se acota al origen de la API (localhost:8000) porque la RUTA del SPA es idéntica
  // (`/pricing/price-lists`); un glob genérico interceptaría también la navegación de la página.
  await page.route('**localhost:8000/pricing/price-lists/*/items', (route) => {
    if (route.request().method() === 'POST') {
      const created = {
        id: 'new-item-id',
        price_list: PRICE_LIST.id,
        product: PRODUCT.id,
        product_name: PRODUCT.name,
        price: '12.50',
        created_at: '2026-06-25T20:00:00Z',
        updated_at: '2026-06-25T20:00:00Z',
      }
      return route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify(created),
      })
    }
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) })
  })
  await page.route('**localhost:8000/pricing/price-lists**', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([PRICE_LIST]),
    }),
  )
}

test.describe('Listas de precios', () => {
  test.beforeEach(async ({ page }) => {
    await mockBackend(page)
  })

  test('carga la consola y lista las listas de precios', async ({ page }) => {
    await page.goto('/pricing/price-lists')

    await expect(page.getByRole('heading', { name: 'Listas de precios' })).toBeVisible()
    await expect(page.getByRole('cell', { name: 'Mayorista' })).toBeVisible()
  })

  test('agrega un precio a la lista', async ({ page }) => {
    await page.goto('/pricing/price-lists')

    await page.getByRole('button', { name: 'Ver precios' }).click()
    await page.getByLabel('Producto').selectOption(PRODUCT.id)
    await page.getByLabel('Precio (USD)').fill('12.50')
    await page.getByRole('button', { name: 'Agregar precio' }).click()

    await expect(page.getByText('Precio agregado.')).toBeVisible()
  })

  test('el input de precio mide ≥16px (sin zoom en iOS Safari)', async ({ page }) => {
    await page.goto('/pricing/price-lists')

    await page.getByRole('button', { name: 'Ver precios' }).click()
    const fontSize = await page
      .getByLabel('Precio (USD)')
      .evaluate((el) => Number.parseFloat(getComputedStyle(el).fontSize))
    expect(fontSize).toBeGreaterThanOrEqual(16)
  })
})
