import { Authenticated, Refine } from '@refinedev/core'
import routerProvider from '@refinedev/react-router'
import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router'

import { Toaster } from '@/components/custom/Toaster'
import { authDataProvider, authProvider, ForcePasswordChangeGuard } from '@/features/auth'
import { HomePage } from '@/pages/HomePage'
import { dataProvider } from '@/shared/providers/data-provider'
import { notificationProvider } from '@/shared/providers/notification-provider'
import { ThemeProvider } from '@/shared/theme/ThemeProvider'

/*
  Composición raíz. Refine gobierna datos de servidor (React Query VIVE dentro de Refine)
  y la sesión (authProvider). Dos dataProviders: `default` (negocio) y `auth` (cliente con
  Authorization + refresh silencioso). Las páginas se cargan con lazy() para no inflar el
  bundle inicial.
*/

const LoginPage = lazy(() =>
  import('@/pages/LoginPage').then((m) => ({ default: m.LoginPage })),
)
const ChangePasswordPage = lazy(() =>
  import('@/pages/ChangePasswordPage').then((m) => ({ default: m.ChangePasswordPage })),
)
const UsersAdminPage = lazy(() =>
  import('@/pages/UsersAdminPage').then((m) => ({ default: m.UsersAdminPage })),
)
const ProfilesAdminPage = lazy(() =>
  import('@/pages/ProfilesAdminPage').then((m) => ({ default: m.ProfilesAdminPage })),
)

function RouteFallback() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex min-h-screen items-center justify-center text-muted-foreground"
    >
      Cargando…
    </div>
  )
}

function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Refine
          dataProvider={{ default: dataProvider, auth: authDataProvider }}
          authProvider={authProvider}
          routerProvider={routerProvider}
          notificationProvider={notificationProvider}
          options={{
            syncWithLocation: true,
            warnWhenUnsavedChanges: true,
            disableTelemetry: true,
          }}
        >
          <Suspense fallback={<RouteFallback />}>
            <Routes>
              <Route
                index
                element={
                  <ForcePasswordChangeGuard>
                    <HomePage />
                  </ForcePasswordChangeGuard>
                }
              />
              <Route path="/login" element={<LoginPage />} />
              <Route
                path="/account/change-password"
                element={
                  <Authenticated
                    key="change-password"
                    redirectOnFail="/login"
                    loading={<RouteFallback />}
                  >
                    <ChangePasswordPage />
                  </Authenticated>
                }
              />
              <Route
                path="/admin/users"
                element={
                  <Authenticated key="admin-users" redirectOnFail="/login" loading={<RouteFallback />}>
                    <ForcePasswordChangeGuard>
                      <UsersAdminPage />
                    </ForcePasswordChangeGuard>
                  </Authenticated>
                }
              />
              <Route
                path="/admin/profiles"
                element={
                  <Authenticated key="admin-profiles" redirectOnFail="/login" loading={<RouteFallback />}>
                    <ForcePasswordChangeGuard>
                      <ProfilesAdminPage />
                    </ForcePasswordChangeGuard>
                  </Authenticated>
                }
              />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
          <Toaster />
        </Refine>
      </BrowserRouter>
    </ThemeProvider>
  )
}

export default App
