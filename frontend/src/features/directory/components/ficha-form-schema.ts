import { z } from 'zod'

/*
  Schema de cliente del formulario de ficha (RHF + zodResolver). Valida FORMATO: requeridos,
  longitud y email. El dígito verificador NO se duplica aquí: lo valida el backend (DRY) y su
  error se mapea al campo `identification_number`.
*/

export const fichaFormSchema = z.object({
  name: z.string().min(1, 'Ingrese un nombre o razón social.'),
  identification_type: z.enum(['CEDULA', 'RUC', 'PASAPORTE']),
  identification_number: z
    .string()
    .min(5, 'Ingrese el número de identificación.')
    .max(20, 'El número es demasiado largo.'),
  email: z.string().email('El email no tiene un formato válido.').or(z.literal('')),
  phone: z.string().max(20, 'El teléfono es demasiado largo.'),
  roles: z.array(z.enum(['CLIENTE', 'PROVEEDOR', 'RESPONSABLE_RUTA', 'CHOFER'])).min(
    1,
    'Seleccione al menos un rol.',
  ),
})

export type FichaFormValues = z.infer<typeof fichaFormSchema>
