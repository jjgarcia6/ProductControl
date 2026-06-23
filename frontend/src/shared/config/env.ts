/*
  Configuración expuesta al cliente. SOLO variables VITE_* (Vite las inyecta en build).
  NUNCA secretos aquí: todo lo VITE_* termina en el bundle público.
*/

/** URL base de la API del backend. */
export const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
