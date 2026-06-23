/// <reference types="vitest/config" />
import { fileURLToPath, URL } from 'node:url'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
    // Una sola instancia de estos paquetes: Refine y la app deben compartir el
    // contexto de React Router (si no, useLocation falla por provider/consumer distintos).
    dedupe: ['react', 'react-dom', 'react-router', '@refinedev/core'],
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: true,
    // Los specs de Playwright (e2e/) los corre Playwright, no Vitest.
    exclude: ['**/node_modules/**', '**/dist/**', 'e2e/**'],
    // Refine carga react-router desde su fuente; inlinearlos evita que Vitest
    // duplique la instancia de react-router y rompa el contexto del Router en jsdom.
    server: {
      deps: {
        inline: [/@refinedev\//, 'react-router'],
      },
    },
  },
})
