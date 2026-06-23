import type { HttpError } from '@refinedev/core'

/*
  Normalización del contrato de errores del backend (§6) a la forma que Refine espera.

  Contrato del backend:
  - Validación (400): { campo: [mensajes], non_field_errors: [...] }
  - General (401/403/404/409/5xx): { detail: "mensaje" }

  Refine HttpError: { message, statusCode, errors? }
  - `errors[campo]` alimenta los errores de campo del formulario (useForm).
  - `message` es el aviso global limpio (lo muestra el notificationProvider).

  Regla dura: a la UI solo llega el mensaje redactado. Nunca status crudo, URL, JSON ni stack.
*/

const GENERIC_MESSAGE = 'Ocurrió un error. Intente nuevamente.'

type ValidationPayload = Record<string, string[] | string>

function isValidationPayload(data: unknown): data is ValidationPayload {
  return (
    typeof data === 'object' &&
    data !== null &&
    !('detail' in data) &&
    Object.values(data).every(
      (value) =>
        typeof value === 'string' ||
        (Array.isArray(value) && value.every((item) => typeof item === 'string')),
    )
  )
}

function toMessages(value: string[] | string): string[] {
  return Array.isArray(value) ? value : [value]
}

/** Convierte la respuesta de error del backend en un HttpError de Refine. */
export function normalizeError(statusCode: number, data: unknown): HttpError {
  // Errores generales: { detail }.
  if (typeof data === 'object' && data !== null && 'detail' in data) {
    const detail = (data as { detail: unknown }).detail
    return {
      message: typeof detail === 'string' ? detail : GENERIC_MESSAGE,
      statusCode,
    }
  }

  // Validación (400): { campo: [mensajes] }.
  if (statusCode === 400 && isValidationPayload(data)) {
    const errors: NonNullable<HttpError['errors']> = {}
    let globalMessage = GENERIC_MESSAGE

    for (const [field, value] of Object.entries(data)) {
      const messages = toMessages(value)
      errors[field] = messages
      if (field === 'non_field_errors' && messages[0]) {
        globalMessage = messages[0]
      }
    }

    return { message: globalMessage, statusCode, errors }
  }

  // Cualquier otra forma inesperada: aviso genérico, sin filtrar el cuerpo.
  return { message: GENERIC_MESSAGE, statusCode }
}
