import { create } from 'zustand'
import { persist } from 'zustand/middleware'

/*
  Estado de TEMA (UI/sesión). Zustand SOLO para estado de UI/sesión, NUNCA para datos
  de servidor (eso lo gestiona Refine). Persiste la elección del usuario.
*/

export type Theme = 'light' | 'dark' | 'system'

const STORAGE_KEY = 'ui-theme'

interface ThemeState {
  theme: Theme
  setTheme: (theme: Theme) => void
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      theme: 'system',
      setTheme: (theme) => set({ theme }),
    }),
    { name: STORAGE_KEY },
  ),
)

/** Resuelve el tema efectivo (light/dark) considerando la preferencia del sistema. */
export function resolveTheme(theme: Theme): 'light' | 'dark' {
  if (theme === 'system') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  return theme
}
