"""Constantes centralizadas de la importación masiva (capability bulk-import, F7).

No son secretos (viven en el código, no en el entorno): son límites de proceso que
acotan la carga síncrona para no chocar con el timeout de Cloud Run y para procesar el
archivo en memoria sin persistirlo. Ajustables aquí en un único punto.
"""

from __future__ import annotations

# Límite de filas de datos por archivo (sin contar la cabecera). Un lote mayor MUST
# rechazarse con 400 pidiendo dividir el archivo (evita procesos síncronos largos).
MAX_ROWS = 1000

# Tamaño máximo del archivo subido (5 MiB). Se valida antes de leer el contenido.
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024

# Extensiones soportadas. El formato se resuelve por la extensión del nombre.
CSV_EXTENSIONS = (".csv",)
EXCEL_EXTENSIONS = (".xlsx",)

# Estados posibles de una fila del reporte (claves de contrato, en inglés).
STATUS_VALID = "valid"
STATUS_SKIPPED = "skipped"
STATUS_ERROR = "error"
