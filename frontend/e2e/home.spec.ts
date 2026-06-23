import { expect, test } from '@playwright/test'

test('la home del andamiaje carga con su título', async ({ page }) => {
  await page.goto('/')
  await expect(
    page.getByRole('heading', { name: 'Sistema de gestión operativa' }),
  ).toBeVisible()
})
