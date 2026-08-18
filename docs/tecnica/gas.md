# GAS — documentación técnica

Pipeline: `backend/app/document_processing_service.py`
(orquestación T3.2+T3.3) sobre imagen del comprobante GAS.

## Configuración del servicio

`backend/config/services.ini`, sección `[GAS]`. Texto plano, no JSON (ver
[docs/tecnica/arquitectura.md](arquitectura.md), ADR-007). Campos:

| Campo | Tipo | Requerido | Ejemplo |
|---|---|---|---|
| `importe` | `amount` | sí | `$ 23.345,56` |
| `cliente` | `text` | sí | `045-987654` |
| `nro_medidor` | `text` | no | `34572` |
| `a_pagar_hasta` | `date` | no | `20/06/2026` |
| `periodo` | `text` | no | `01/2026` |

Cada campo declara `Label`, `Example`, `Type`, `Required`, `Patterns`
(palabras clave de anclaje) y `Regex` (patrón de extracción sobre el
texto OCR normalizado).

## Algoritmo de extracción

`backend/app/gas_extractor.py` implementa el extractor específico del
servicio GAS (motor genérico + reglas declarativas, no un extractor por
servicio duplicado — ver ADR-007):

1. `normalize_text`: colapsa saltos de línea y espacios múltiples del
   texto OCR crudo, para que las regex ancladas en palabras clave
   (`importe`, `vencimiento`, `cliente`, ...) funcionen sobre una sola
   línea lógica.
2. Por campo, `_extract_first` prueba los patrones regex en orden y
   devuelve el primer match, limpiado de separadores/símbolos monetarios
   sobrantes (`_clean_value`).
3. Campos soportados: `importe` (monto), `a_pagar_hasta` (fecha),
   `cliente`, `periodo`, `nro_medidor`.

## Validación semántica

`backend/app/service_data_validation.py` valida el **tipo** de cada
candidato antes de aceptarlo:

- `importe`/`total`/`saldo`/`a_pagar` → debe contener dígitos (monto).
- `a_pagar_hasta`/`vencimiento`/`fecha` → debe matchear un formato de
  fecha (`DD/MM/YYYY`, `DD-MM-YYYY`, etc.).
- `periodo` → formato `MM/YYYY`.
- `cliente`/`nro_medidor`/`codigo` → cualquier código/identificador no
  vacío.

Un candidato que no matchea su tipo queda como campo rechazado o no
encontrado, nunca se acepta "a ciegas".

## Estado actual del pipeline (T3.2/T3.3)

El orquestador `backend/app/t3_2_orchestrator.py` hoy hardcodea
`rejected_fields = {}` para GAS: ningún campo se rechaza semánticamente
todavía (la rama de rechazo existe y se testea sintéticamente, ver
`backend/tests/test_web_process_api.py::TestConfirmServiceSynthetic`).
En la práctica, con el fixture actual (`backend/tests/fixtures/gas_sample.jpg`)
los campos quedan en `accepted` (con valor) o `missing` (sin valor).

## Salida legacy `.DATA`

`backend/app/storage_bridge_writer.py` + `document_result_exporter.py`
escriben el resultado validado como archivo plano `.DATA`
(`GAS_YYYYMMDD_HHMMSS.DATA`, separador `;`, cabecera en la línea 1,
valores desde la línea 2) en `storage_bridge/ready/`, con escritura
atómica (archivo temporal + rename, ver ADR-005).

## Casos borde cubiertos por tests

- Texto OCR vacío o solo espacios (`backend/tests/test_empty_text.py`).
- Archivo `.DATA` sin datos reales (`test_data_file_emptiness.py`).
- Fecha/monto con formato inválido en la corrección humana (T4,
  `backend/tests/test_web_process_api.py::TestConfirm`).
- Reemplazo atómico sin dejar archivo `.ready` parcial ante fallo
  (`test_storage_bridge_writer.py`).
