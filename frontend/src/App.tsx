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
const DirectoryPage = lazy(() =>
  import('@/pages/DirectoryPage').then((m) => ({ default: m.DirectoryPage })),
)
const CategoriesPage = lazy(() =>
  import('@/pages/products/CategoriesPage').then((m) => ({ default: m.CategoriesPage })),
)
const ProductsPage = lazy(() =>
  import('@/pages/products/ProductsPage').then((m) => ({ default: m.ProductsPage })),
)
const UnitsPage = lazy(() =>
  import('@/pages/products/UnitsPage').then((m) => ({ default: m.UnitsPage })),
)
const PriceListsPage = lazy(() =>
  import('@/pages/PriceListsPage').then((m) => ({ default: m.PriceListsPage })),
)
const BulkImportPage = lazy(() =>
  import('@/pages/BulkImportPage').then((m) => ({ default: m.BulkImportPage })),
)
const SystemSettingsPage = lazy(() =>
  import('@/pages/SystemSettingsPage').then((m) => ({ default: m.SystemSettingsPage })),
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
              <Route
                path="/directory"
                element={
                  <Authenticated key="directory" redirectOnFail="/login" loading={<RouteFallback />}>
                    <ForcePasswordChangeGuard>
                      <DirectoryPage />
                    </ForcePasswordChangeGuard>
                  </Authenticated>
                }
              />
              <Route
                path="/products/categories"
                element={
                  <Authenticated key="products-categories" redirectOnFail="/login" loading={<RouteFallback />}>
                    <ForcePasswordChangeGuard>
                      <CategoriesPage />
                    </ForcePasswordChangeGuard>
                  </Authenticated>
                }
              />
              <Route
                path="/products/products"
                element={
                  <Authenticated key="products-products" redirectOnFail="/login" loading={<RouteFallback />}>
                    <ForcePasswordChangeGuard>
                      <ProductsPage />
                    </ForcePasswordChangeGuard>
                  </Authenticated>
                }
              />
              <Route
                path="/products/units"
                element={
                  <Authenticated key="products-units" redirectOnFail="/login" loading={<RouteFallback />}>
                    <ForcePasswordChangeGuard>
                      <UnitsPage />
                    </ForcePasswordChangeGuard>
                  </Authenticated>
                }
              />
              <Route
                path="/pricing/price-lists"
                element={
                  <Authenticated key="pricing-price-lists" redirectOnFail="/login" loading={<RouteFallback />}>
                    <ForcePasswordChangeGuard>
                      <PriceListsPage />
                    </ForcePasswordChangeGuard>
                  </Authenticated>
                }
              />
              <Route
                path="/bulk-import"
                element={
                  <Authenticated key="bulk-import" redirectOnFail="/login" loading={<RouteFallback />}>
                    <ForcePasswordChangeGuard>
                      <BulkImportPage />
                    </ForcePasswordChangeGuard>
                  </Authenticated>
                }
              />
              <Route
                path="/system-settings"
                element={
                  <Authenticated key="system-settings" redirectOnFail="/login" loading={<RouteFallback />}>
                    <ForcePasswordChangeGuard>
                      <SystemSettingsPage />
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
