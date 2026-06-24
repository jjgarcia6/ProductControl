import { UsersAdminConsole } from '@/features/users'

/*
  Dumb page: layout + la consola (que encapsula sus hooks). Sin estado ni fetch directos.
*/
export function UsersAdminPage() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 py-10">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold text-foreground">Usuarios</h1>
        <p className="text-sm text-muted-foreground">
          Alta, edición, perfil, reset de contraseña y activación de usuarios.
        </p>
      </header>
      <UsersAdminConsole />
    </main>
  )
}
