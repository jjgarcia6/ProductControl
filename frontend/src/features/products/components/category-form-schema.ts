import { z } from 'zod'

/*
  Schema del FORMULARIO de categoría (validación en cliente). No sustituye al schema Zod
  generado del OpenAPI (fuente de verdad del contrato): valida la entrada del usuario antes de
  enviar. Los pesos se capturan como string decimal (nunca float). merma_min/merma_max son
  opcionales hasta que el cliente defina los valores.
*/

const DECIMAL_RE = /^-?\d{0,9}(?:\.\d{0,3})?$/
const optionalDecimal = z
  .string()
  .trim()
  .refine((value) => value === '' || DECIMAL_RE.test(value), 'Ingrese un número válido (máx. 3 decimales).')

export const categoryFormSchema = z.object({
  name: z.string().trim().min(1, 'El nombre es obligatorio.').max(128),
  shelf_life_days: z
    .number({ error: 'Ingrese los días de caducidad.' })
    .int('Debe ser un número entero.')
    .gte(0, 'No puede ser negativo.'),
  intake_type: z.enum(['GAVETA', 'PESO']),
  merma_min: optionalDecimal,
  merma_max: optionalDecimal,
  reference_qty: optionalDecimal,
})

export type CategoryFormValues = z.infer<typeof categoryFormSchema>
