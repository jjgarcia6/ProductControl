import { useDataProvider } from '@refinedev/core'

import { type ImportEntity } from '../types/import.types'

/*
  Descarga de la plantilla CSV de una entidad (F7). Va por el dataProvider 'auth' (cliente
  con Authorization) porque el endpoint está protegido: un <a href> plano no adjuntaría el
  token. La respuesta CSV se entrega al navegador como una descarga vía Blob.
*/

export function useImportTemplate() {
  const getDataProvider = useDataProvider()

  const download = async (entity: ImportEntity): Promise<void> => {
    const provider = getDataProvider('auth')
    if (!provider.custom) return
    const response = await provider.custom({
      url: `/bulk-import/${entity}/template`,
      method: 'get',
    })
    // El endpoint devuelve texto CSV, no un objeto: se trata como string para el Blob.
    const csv = response.data as unknown as string
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
    const objectUrl = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = objectUrl
    anchor.download = `${entity}_template.csv`
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(objectUrl)
  }

  return { download }
}
