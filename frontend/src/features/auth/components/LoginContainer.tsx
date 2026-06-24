import { useLogin } from '@refinedev/core'

import { LoginForm } from './LoginForm'
import type { LoginInput } from '../types/auth.types'

/*
  Contenedor de login. Orquesta el authProvider vía useLogin de Refine: la navegación al
  éxito la hace Refine con el `redirectTo` del authProvider. Mapea los estados de la
  mutación (carga/error) a props del formulario presentacional.
*/
export function LoginContainer() {
  const { mutate: login, isPending, error } = useLogin<LoginInput>()

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-sm flex-col justify-center gap-8 px-6 py-12">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold text-foreground">Iniciar sesión</h1>
        <p className="text-sm text-muted-foreground">
          Sistema de gestión operativa.
        </p>
      </header>

      <LoginForm
        onSubmit={(values) => login(values)}
        isSubmitting={isPending}
        errorMessage={error?.message}
      />
    </main>
  )
}
