import { describe, expect, it } from 'vitest'

import { normalizeError } from './errors'

describe('normalizeError (contrato de errores §6)', () => {
  it('mapea un 400 a errores por campo y usa non_field_errors como mensaje global', () => {
    const result = normalizeError(400, {
      ruc: ['El RUC ingresado no es válido.'],
      non_field_errors: ['La fecha pertenece a un período cerrado.'],
    })

    expect(result.statusCode).toBe(400)
    expect(result.errors).toEqual({
      ruc: ['El RUC ingresado no es válido.'],
      non_field_errors: ['La fecha pertenece a un período cerrado.'],
    })
    expect(result.message).toBe('La fecha pertenece a un período cerrado.')
  })

  it('mapea un error general { detail } a message', () => {
    const result = normalizeError(403, {
      detail: 'No tiene permiso para realizar esta acción.',
    })

    expect(result.statusCode).toBe(403)
    expect(result.message).toBe('No tiene permiso para realizar esta acción.')
    expect(result.errors).toBeUndefined()
  })

  it('no filtra el cuerpo crudo ante una forma inesperada', () => {
    const result = normalizeError(500, '<html>Traceback en db.py:42</html>')

    expect(result.statusCode).toBe(500)
    expect(result.message).toBe('Ocurrió un error. Intente nuevamente.')
    expect(JSON.stringify(result)).not.toContain('db.py')
  })
})
