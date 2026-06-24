import { ChangePasswordForm } from '@/features/auth'

/*
  Dumb page: layout mínimo + el formulario (que encapsula su hook). Sin estado ni fetch
  directos aquí.
*/
export function ChangePasswordPage() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-sm flex-col justify-center gap-8 px-6 py-12">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold text-foreground">Cambiar contraseña</h1>
        <p className="text-sm text-muted-foreground">
          Tras el cambio deberá iniciar sesión nuevamente.
        </p>
      </header>
      <ChangePasswordForm />
    </main>
  )
}
