import { zodResolver } from '@hookform/resolvers/zod'
import { type HttpError } from '@refinedev/core'
import { useState } from 'react'
import { useForm } from 'react-hook-form'

import { useCreditTerms } from '../hooks/useCreditTerms'
import { useFichaMutation } from '../hooks/useFichaMutation'
import type { Ficha, FichaWriteInput } from '../types/directory.types'
import { CreditTermsSubform, type CreditTermsSubformValues } from './CreditTermsSubform'
import { fichaFormSchema, type FichaFormValues } from './ficha-form-schema'
import { FichaFormFields } from './FichaFormFields'

/*
  Formulario de ficha (F4). Contenedor: orquesta RHF + la mutación de alta/edición y, en modo
  edición, el sub-formulario de términos de crédito por faceta. Mapea los errores 400 del
  backend (dígito verificador, email, faceta↔rol) a los campos. Tokens del theme; cero hex.
*/

const SERVER_FIELDS: ReadonlyArray<keyof FichaFormValues> = [
  'name',
  'identification_number',
  'email',
  'roles',
]

interface Props {
  ficha?: Ficha
  onSaved?: () => void
}

function toFormValues(ficha?: Ficha): FichaFormValues {
  return {
    name: ficha?.name ?? '',
    identification_type: ficha?.identification_type ?? 'CEDULA',
    identification_number: ficha?.identification_number ?? '',
    email: ficha?.email ?? '',
    phone: ficha?.phone ?? '',
    roles: ficha?.roles ?? [],
  }
}

export function FichaForm({ ficha, onSaved }: Props) {
  const isEdit = Boolean(ficha)
  const { createFicha, updateFicha, isPending } = useFichaMutation()
  const { createTerms, isPending: isSavingTerms } = useCreditTerms()

  const [serverErrors, setServerErrors] = useState<Partial<Record<keyof FichaFormValues, string>>>(
    {},
  )
  const [termsError, setTermsError] = useState<string | undefined>(undefined)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FichaFormValues>({
    resolver: zodResolver(fichaFormSchema),
    defaultValues: toFormValues(ficha),
  })

  const errorFor = (field: keyof FichaFormValues) =>
    errors[field]?.message ?? serverErrors[field]

  const mapServerErrors = (error: HttpError) => {
    const next: Partial<Record<keyof FichaFormValues, string>> = {}
    for (const field of SERVER_FIELDS) {
      const messages = error.errors?.[field]
      if (messages) next[field] = Array.isArray(messages) ? messages[0] : String(messages)
    }
    // El 409 (número duplicado) llega como mensaje general: mostrarlo en el número.
    if (Object.keys(next).length === 0 && error.message) {
      next.identification_number = error.message
    }
    setServerErrors(next)
  }

  const onSubmit = (values: FichaFormValues) => {
    setServerErrors({})
    const payload: FichaWriteInput = {
      name: values.name,
      identification_type: values.identification_type,
      identification_number: values.identification_number,
      email: values.email || undefined,
      phone: values.phone || undefined,
      roles: values.roles,
    }
    const callbacks = { onSuccess: () => onSaved?.(), onError: mapServerErrors }
    if (ficha) updateFicha(ficha.id, payload, callbacks)
    else createFicha(payload, callbacks)
  }

  const onSaveTerms = (values: CreditTermsSubformValues) => {
    if (!ficha) return
    setTermsError(undefined)
    createTerms(
      { ficha: ficha.id, ...values },
      {
        onError: (error) => {
          const facetError = error.errors?.facet
          setTermsError(
            facetError
              ? Array.isArray(facetError)
                ? facetError[0]
                : String(facetError)
              : error.message,
          )
        },
      },
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
        <FichaFormFields register={register} errors={errors} errorFor={errorFor} />
        <button
          type="submit"
          disabled={isPending}
          className="h-11 rounded-md bg-primary px-4 text-base font-medium text-primary-foreground transition-opacity hover:opacity-90 active:opacity-80 focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-60"
        >
          {isPending ? 'Guardando…' : isEdit ? 'Guardar cambios' : 'Crear ficha'}
        </button>
      </form>

      {ficha ? (
        <section aria-label="Términos de crédito" className="border-t pt-4">
          <h3 className="mb-3 text-base font-semibold text-foreground">Términos de crédito</h3>
          <CreditTermsSubform
            fichaRoles={ficha.roles}
            isPending={isSavingTerms}
            serverError={termsError}
            onSubmit={onSaveTerms}
          />
        </section>
      ) : null}
    </div>
  )
}
