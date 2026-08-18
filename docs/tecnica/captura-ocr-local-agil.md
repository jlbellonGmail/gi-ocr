# Captura OCR Local Ágil — documentación técnica

Reemplaza EasyOCR por **RapidOCR (PP-OCRv3) + ONNX Runtime** como motor
OCR principal y reconstruye el flujo de captura alrededor de una cola de
jobs asíncrona, multi-proveedor y multi-documento (imagen o PDF).

## Decisión de motor OCR (resuelve ADR-006)

| Motor | Estado | Evidencia |
|---|---|---|
| PaddleOCR PP-OCR Mobile | Descartado | Sin wheel para Python 3.14 (`pip install paddlepaddle` → `No matching distribution found`) |
| EasyOCR | Conservado como fallback opcional, deshabilitado por defecto | ~30 s/documento medido en uso previo (T3.x/T4) |
| **RapidOCR-onnxruntime 1.2.3 + onnxruntime** | **Elegido, motor principal** | **2.35–2.57 s en caliente** (two-pass ROI), ver abajo. Licencia Apache-2.0 (RapidOCR) / MIT (onnxruntime) |

La mejora es de un orden de magnitud sobre EasyOCR, medida, no estimada.

## Arquitectura two-pass ROI-focalizada

`backend/app/ocr_engine.py` mantiene el motor RapidOCR como **singleton**
(`get_engine()`, cargado una sola vez al arranque vía `_startup` en
`main.py`, medible aparte como "arranque en frío"). El flujo de
extracción (`capture_pipeline.py`) hace:

1. **Detección full-page**: localiza todas las cajas de texto del
   documento (~1.1–1.4 s).
2. **Reconocimiento selectivo**: en vez de reconocer las ~130–190 cajas
   completas del documento (~100–130 ms/caja → 13–25 s, medido como
   inaceptable), reconoce solo las cajas que caen dentro de las bandas
   ROI declaradas por la plantilla del proveedor detectado (~1.45–1.6 s).
3. Reconocimiento full-page completo queda como **fallback** únicamente
   para documentos de proveedor desconocido o bandas sin ancla.

Total en caliente: **2.35–2.57 s** por documento.

### Control de concurrencia (onnxruntime)

`ocr_engine.py` capea `intra_op_num_threads` de cada sesión de
`onnxruntime` (`GI_OCR_ORT_THREADS`, default `3`) e `inter_op_num_threads=1`
**antes** de que RapidOCR cree sus sesiones. Sin este cap, cada inferencia
usa todos los núcleos físicos y varios workers concurrentes generan
oversubscription. La cola (`backend/app/job_queue.py`, clase `JobQueue`)
usa por defecto **2 workers** (`JobQueue(store, workers=2)`) sobre el
mismo motor compartido — medido como superior a un motor por-worker en
este perfil de carga.

## Plantillas y clasificación de proveedor

`backend/app/templates/providers.py` define, por proveedor
(`LITORAL_GAS`/servicio `GAS`, `CEVT`/servicio `ELECTRICITY`), las ROI en
coordenadas normalizadas `[0,1]` (ancla de texto, banda `y`, banda `x`,
regex, validador tipado, score mínimo). `backend/app/classifier.py`
decide el proveedor **antes** de aplicar ROI; regla dura verificada por
test: nunca asigna `GAS` por defecto a un documento no reconocido.

## PDF

`backend/app/pdf_util.py` extrae primero **texto nativo** con
`pypdfium2`; solo aplica OCR a páginas sin texto utilizable. Soporta
documentos multipágina evaluando cada página de forma independiente.

## Cola, jobs y watcher

- `backend/app/job_store.py` / `job_queue.py`: persistencia y cola
  asíncrona no bloqueante — se puede seguir cargando documentos mientras
  otros se procesan. Estados: `queued`, `processing`, `ready`,
  `confirmed`, `failed`, con reintento individual
  (`POST /api/v1/jobs/{id}/retry`).
- `backend/app/inbound_watcher.py`: observa la carpeta `inbound/`
  (gitignored) con detección segura de archivos completos y dedupe, sin
  procesar archivos a medio escribir. Estado vía `GET /api/v1/inbound/status`.
- `backend/app/review_service.py`: confirmación de revisión humana,
  análogo en propósito al de T4 pero adaptado al modelo de jobs
  (preserva originales, traza correcciones).

## Seguridad

`backend/app/validators.py` (+ `backend/tests/test_security.py`):
validación de extensión/MIME/tamaño de archivo, sanitización de nombres,
rechazo de secuencias de path traversal. Sin egress de documentos a
servicios externos — todo el procesamiento es local.

## Cambio de superficie de API respecto de `develop`

Esta feature **reemplaza** `backend/app/main.py` por una API de jobs
nueva (`/api/v1/jobs*`, ver [docs/usuario/captura-ocr-local-agil.md](../usuario/captura-ocr-local-agil.md)).
El único endpoint que existía en `develop`, `/api/v1/capture` (extracción
legacy por zonas), **no está presente** en esta versión. No es una
regresión de tests (`backend/tests/test_ocr_gas.py` prueba la extracción
a nivel de función, no el endpoint, y sigue en verde), pero sí es un
cambio de contrato HTTP deliberado, reemplazado funcionalmente por el
flujo de jobs (con más capacidad: cola, multi-documento, confirmación).

## Casos borde verificados por test

- Proveedor desconocido no se clasifica como GAS por defecto
  (`test_classifier.py`).
- Campo ilegible por el motor (período de Litoral Gas, caso real: OCR
  devuelve `"DL73026"` en vez de `"01/2026"`) queda pendiente de
  corrección humana, sin heurística de reparación de caracteres.
- PDF sin texto nativo dispara OCR; PDF con texto nativo no
  (`test_pdf_util.py`).
- Archivo con extensión válida pero contenido no correspondiente se
  rechaza en validación (`test_validators.py`, `test_security.py`).
- Path traversal en nombre de archivo se sanitiza antes de escribir a
  disco (`test_security.py`).
- Detección de archivos nuevos en `inbound/` sin duplicar ni procesar
  archivos incompletos (`test_inbound_watcher.py`).

## Pendiente, no verificado en esta ronda (declarado, no omitido)

- Benchmark de lote de 400 documentos y comportamiento de la cola bajo
  carga sostenida: requiere datos sintéticos locales no versionados
  (`scripts/benchmark_captura.py` existe y es reproducible, pero no se
  corrió en esta verificación).
- E2E real con Playwright (`tests/e2e/test_e2e_playwright.py`): se salta
  automáticamente si no están las muestras privadas
  (`backend/tests/fixtures/_local_samples/real/{GAS,cevt}.jpeg`,
  gitignored) — no disponibles en este entorno de verificación.
