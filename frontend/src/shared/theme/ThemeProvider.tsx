import { useEffect, type ReactNode } from 'react'

import { resolveTheme, useThemeStore } from './theme-store'

/*
  Aplica la clase .dark en <html> según el tema elegido. Arranca con la preferencia del
  sistema (prefers-color-scheme) cuando el tema es 'system' y reacciona a sus cambios.
  Light/dark es OBLIGATORIO (config.yaml).
*/
export function ThemeProvider({ children }: { children: ReactNode }) {
  const theme = useThemeStore((state) => state.theme)

  useEffect(() => {
    const root = document.documentElement

    const apply = () => {
      const effective = resolveTheme(theme)
      root.classList.toggle('dark', effective === 'dark')
    }

    apply()

    // Si el tema sigue al sistema, reaccionar a cambios del SO en vivo.
    if (theme === 'system') {
      const media = window.matchMedia('(prefers-color-scheme: dark)')
      media.addEventListener('change', apply)
      return () => media.removeEventListener('change', apply)
    }
  }, [theme])

  return <>{children}</>
}
