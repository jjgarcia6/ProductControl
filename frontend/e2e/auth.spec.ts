import { expect, test } from '@playwright/test'

/*
  Smoke del login (cross-browser, incluye WebKit móvil por la config de Playwright).
  No depende del backend: ejercita el render y la validación de cliente, y verifica que
  los inputs miden ≥16px para que Safari iOS no haga zoom al enfocarlos.
*/

test.describe('Login', () => {
  test('carga la pantalla y valida en el cliente', async ({ page }) => {
    await page.goto('/login')

    await expect(page.getByRole('heading', { name: 'Iniciar sesión' })).toBeVisible()

    // Enviar el formulario vacío muestra los errores por campo (Zod).
    await page.getByRole('button', { name: 'Ingresar' }).click()
    await expect(page.getByText('Ingrese su usuario.')).toBeVisible()
    await expect(page.getByText('Ingrese su contraseña.')).toBeVisible()
  })

  test('los inputs miden ≥16px (sin zoom en iOS Safari)', async ({ page }) => {
    await page.goto('/login')

    for (const selector of ['#username', '#password']) {
      const fontSize = await page
        .locator(selector)
        .evaluate((el) => Number.parseFloat(getComputedStyle(el).fontSize))
      expect(fontSize).toBeGreaterThanOrEqual(16)
    }
  })
})
