# Mejora Precision OCR

## Proposito

Esta feature agrega evidencia reproducible de precision y rendimiento para la
captura OCR local vigente. No cambia ADR-006: RapidOCR con ONNX Runtime y el
flujo two-pass ROI siguen siendo el motor principal para imagenes y PDFs
escaneados.

El foco es medir, por lote, proveedor y campo, que ocurre entre:

- texto bruto OCR;
- campos candidatos;
- campos validados;
- campos rechazados;
- campos no encontrados.

## Benchmark

El punto de entrada es `scripts/benchmark_captura.py`.

Parametros principales:

- `--docs`: cantidad objetivo de documentos o variantes. El lote operativo
  objetivo es 400, pero el valor por defecto es chico para desarrollo.
- `--dataset`: `synthetic`, `local` o `auto`.
- `--out`: JSON estructurado.
- `--report-md`: resumen Markdown.
- `--private-dir`: directorio privado opcional para muestras reales locales.
- `--synthetic-mode`: `controlled` por defecto para no requerir OCR real en CI,
  u `ocr` para procesar las imagenes sinteticas generadas con RapidOCR/ONNX.

El modo `auto` intenta usar muestras privadas locales desde
`backend/tests/fixtures/_local_samples/real/expected.local.json`. Si no existen,
usa el dataset sintetico/controlado versionable generado en `_bench/`, que esta
gitignored.

## Dataset

El dataset sintetico/controlado genera imagenes sin datos sensibles para:

- `LITORAL_GAS` / `GAS` con campos validados;
- `CEVT` / `ELECTRICITY` con campos validados;
- `LITORAL_GAS` con periodo invalido para verificar rechazo semantico;
- documento blanco/desconocido, que debe permanecer como `UNKNOWN`.

Las variantes aplican rotacion leve, escala, brillo/contraste y compresion. En
modo `controlled`, el benchmark valida el contrato de parser/agregacion sin
invocar OCR real. En modo `ocr`, esas imagenes se procesan por el pipeline
RapidOCR/ONNX. Las muestras privadas locales son opcionales y nunca se versionan.

## Salida JSON

La salida contiene:

- `summary.docs`;
- `summary.cold_start_s`;
- `summary.hot_p50_s`, `summary.hot_p95_s`, `summary.hot_mean_s`,
  `summary.hot_max_s`;
- `summary.docs_per_minute`;
- `summary.process_rss_mb`, si la plataforma permite medirlo;
- `summary.timings_by_stage`, con las etapas expuestas por el pipeline;
- `summary.provider_service`, agrupado por proveedor/servicio esperado;
- `summary.fields`, agregado global por campo;
- `summary.false_positives_avoided_count`;
- `documents[]`, con detalle por documento.

Cada documento conserva `raw_ocr_text`, `candidate_fields`, `validated_fields`,
`rejected_fields`, `missing_fields`, `field_results` y
`false_positives_avoided`.

## Falsos Positivos Evitados

Un falso positivo evitado es un candidato que no llega a campo validado. El
benchmark registra:

- campo;
- valor candidato;
- motivo de rechazo o condicion de no coincidencia;
- validacion aplicada.

El caso sintetico `synthetic-gas-invalid-period` fuerza un periodo `13/2026`.
Debe aparecer como candidato rechazado por validacion semantica, no como campo
validado ni como missing.

## Umbrales

Para esta ronda, el umbral operativo declarado es `hot_p95_s <= 5.0`. Si el p95
caliente supera 5 segundos por documento, el JSON y el Markdown lo marcan como
`risk`. La decision de bloquear o aceptar ese riesgo queda para QA/PR segun el
lote usado y la maquina donde se corrio.

## Casos Borde

- Documento blanco o desconocido: se reporta como `UNKNOWN`.
- Campo visible pero semanticamente invalido: queda en `rejected_fields`.
- Campo esperado ausente: queda en `missing_fields` y se cuenta como
  `missing_unexpected`, salvo que el contrato local lo declare permitido.
- PDF con texto nativo: el pipeline puede reportar motor `PDF-NATIVE-TEXT`; el
  benchmark conserva ese motor por documento para no mezclar rutas.
- Error por documento: el lote sigue y el documento queda con `error`.

## Decisiones de Diseno

- El benchmark vive en `scripts/benchmark_captura.py` para reemplazar el medidor
  previo de tiempos sin crear otro comando paralelo.
- Las funciones de agregacion son testeables sin OCR ni muestras privadas.
- No se agregaron proveedores, extractores Python por proveedor ni valores
  privados hardcodeados.
- `psutil` es opcional; si no esta disponible, la memoria se mide con fallback o
  queda como `null`.
