/*
  Contrato público de la feature directory. Lo de afuera SOLO importa desde aquí.
*/
export { DirectoryList } from './components/DirectoryList'
export { FichaForm } from './components/FichaForm'
export { useFichas } from './hooks/useFichas'
export { useFichaMutation } from './hooks/useFichaMutation'
export { useFichaStatus } from './hooks/useFichaStatus'
export { useCreditTerms } from './hooks/useCreditTerms'
export { useAssignPriceList } from './hooks/useAssignPriceList'
export { PriceListSelect } from './components/PriceListSelect'
export type {
  Ficha,
  FichaWriteInput,
  CreditTerms,
  CreditTermsWriteInput,
} from './types/directory.types'
