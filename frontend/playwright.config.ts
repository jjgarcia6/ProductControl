import { defineConfig, devices } from '@playwright/test'

/*
  E2E + cross-browser. WebKit es OBLIGATORIO para el QA de Safari iOS (inputs numéricos
  decimales y fechas). Levanta el dev server de Vite para las pruebas.
*/
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    // Safari iOS: motor WebKit en viewport móvil.
    { name: 'webkit-mobile', use: { ...devices['iPhone 13'] } },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
})
