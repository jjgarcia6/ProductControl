/*
  Post-proceso del codegen de Zod. openapi-zod-client@1.18.3 emite records al estilo
  Zod v3 (`z.record(value)`), pero el proyecto fija Zod v4, donde `z.record` exige
  clave y valor (`z.record(key, value)`). El OpenAPI siempre usa claves string
  (additionalProperties), y la herramienta solo emite records de un argumento, así que
  reescribir cada `z.record(` a `z.record(z.string(), ` es seguro y determinista.

  No es edición manual del artefacto: es un paso fijo del pipeline de generación.
*/
import { readFileSync, writeFileSync } from 'node:fs'

const target = process.argv[2]
if (!target) {
  console.error('Uso: node fix-zod-v4.mjs <ruta/zod.ts>')
  process.exit(1)
}

const source = readFileSync(target, 'utf8')
const fixed = source.replaceAll('z.record(', 'z.record(z.string(), ')

if (fixed !== source) {
  writeFileSync(target, fixed)
  console.log('fix-zod-v4: z.record adaptado a Zod v4 en', target)
}
