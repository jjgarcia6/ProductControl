import { create } from 'zustand'

import type { UserIdentity } from '../types/auth.types'

/*
  Estado de sesión (Zustand). El access token vive SOLO en memoria: NO se persiste en
  localStorage/sessionStorage (mitiga XSS robando el token). Al recargar la página el
  access se pierde y se repone con el refresh silencioso (cookie httpOnly) desde el
  authProvider.check. El refresh token NUNCA toca este store: vive en la cookie httpOnly.
*/
interface SessionState {
  accessToken: string | null
  user: UserIdentity | null
  setSession: (accessToken: string, user: UserIdentity) => void
  setAccessToken: (accessToken: string) => void
  clear: () => void
}

export const useSessionStore = create<SessionState>((set) => ({
  accessToken: null,
  user: null,
  setSession: (accessToken, user) => set({ accessToken, user }),
  setAccessToken: (accessToken) => set({ accessToken }),
  clear: () => set({ accessToken: null, user: null }),
}))
