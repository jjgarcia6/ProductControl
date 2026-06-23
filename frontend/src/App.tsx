import { Refine } from '@refinedev/core'
import routerProvider from '@refinedev/react-router'
import { BrowserRouter, Route, Routes } from 'react-router'

import { Toaster } from '@/components/custom/Toaster'
import { HomePage } from '@/pages/HomePage'
import { dataProvider } from '@/shared/providers/data-provider'
import { notificationProvider } from '@/shared/providers/notification-provider'
import { ThemeProvider } from '@/shared/theme/ThemeProvider'

/*
  Composición raíz. Refine gobierna datos de servidor (React Query VIVE dentro de Refine;
  sin TanStack en paralelo). El ThemeProvider aplica light/dark. Los resources de negocio
  se registran en sus changes; el bootstrap arranca con una dumb page.
*/
function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Refine
          dataProvider={dataProvider}
          routerProvider={routerProvider}
          notificationProvider={notificationProvider}
          options={{ syncWithLocation: true, warnWhenUnsavedChanges: true }}
        >
          <Routes>
            <Route index element={<HomePage />} />
          </Routes>
          <Toaster />
        </Refine>
      </BrowserRouter>
    </ThemeProvider>
  )
}

export default App
