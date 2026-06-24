# Current Task

## ID

T2.1

## Nombre

Bridge de salida atomica DATA

## Objetivo

Implementar el bridge de salida controlado para archivos legacy DATA, escribiendo primero en un archivo temporal y moviendo luego de forma atomica hacia storage_bridge/ready.

La tarea convierte la salida plana existente en una salida operativa segura para integracion, evitando archivos parciales en ready.

## Rama requerida

feature/ocr-storage-bridge-atomic-output

## Alcance permitido

Pueden crearse/modificarse unicamente:

- backend/app/storage_bridge_writer.py
- backend/tests/test_storage_bridge_writer.py
- governance/current-task.md

## Alcance prohibido

No modificar:

- frontend/
- endpoints FastAPI
- motor OCR
- backend/app/gas_extractor.py
- backend/config/services.ini
- GitHub remoto sin aprobacion explicita
- tags
- imagenes reales
- reportes locales versionables

No crear:

- archivos JSON como salida legacy
- nuevos extractores Python por servicio
- archivos DATA versionables

## Contrato de salida bridge

El bridge debe:

1. Recibir service, fields, values y timestamp.
2. Generar nombre SERVICIO_YYYYMMDD_HHMMSS.DATA.
3. Generar contenido plano con linea de encabezado y linea de valores.
4. Usar punto y coma como separador obligatorio.
5. Escribir primero en storage_bridge/inbound/*.tmp.
6. Mover con os.replace hacia storage_bridge/ready/*.DATA.
7. No escribir directamente archivos finales en ready.
8. No dejar DATA parcial en ready ante error.
9. Preservar valores faltantes como columnas vacias.
10. Rechazar payload invalido antes de escribir.

## Tests requeridos

1. Construccion de nombre SERVICIO_YYYYMMDD_HHMMSS.DATA.
2. Contenido DATA con punto y coma y valores vacios preservados.
3. Escritura temporal y movimiento atomico con os.replace.
4. Ausencia de archivo parcial en ready ante error.
5. Rechazo de payload invalido antes de escribir.
6. No sobrescribir un DATA existente en ready.

## Validaciones requeridas

Ejecutar:

python -m py_compile backend\app\storage_bridge_writer.py
python -m py_compile backend\tests\test_storage_bridge_writer.py
python scripts\validate_project.py
pytest backend\tests\test_storage_bridge_writer.py -v
pytest backend\tests -v
python -m pytest backend\tests -v
git diff --check
git status --short

## Criterios de aceptacion

La tarea queda lista si:

- estas en rama feature/ocr-storage-bridge-atomic-output;
- existe writer atomico para storage_bridge;
- existe test especifico del bridge;
- no se escribe directo en ready;
- se usa os.replace;
- no quedan DATA generados como archivos versionables;
- todos los tests pasan;
- no se toca frontend, endpoints, motor OCR ni configuracion de servicios;
- se propone commit sin ejecutarlo hasta aprobacion explicita.
