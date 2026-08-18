# Spec: Captura OCR Local Ágil

> Producida por `analyst-agent` a partir del spec original
> `specs/captura-ocr-local-agil.md` (ya existente en la rama, escrito antes
> de que este repo adoptara el circuito de `AGENTS.md`). Se reformatea al
> template vigente y se completan los dos criterios de documentación
> obligatorios que el spec original no traía explícitos.

## Alcance

Reemplazar EasyOCR por **RapidOCR (PP-OCRv3) + ONNX Runtime** como motor
OCR principal, y construir alrededor de él un flujo de captura operable
completo:

- Arquitectura two-pass ROI-focalizada (detección full-page + reconocimiento
  selectivo sobre bandas ancladas del template) en vez de reconocimiento
  full-page, por rendimiento.
- Plantillas multi-proveedor: `LITORAL_GAS` (GAS) y `CEVT` (ELECTRICITY),
  con ROI normalizadas [0,1], anclas de texto, regex y validación tipada
  por campo (`backend/app/templates/providers.py`).
- Entrada multi-documento: imagen o PDF (texto nativo primero vía
  `pypdfium2`, OCR solo si la página no tiene texto utilizable).
- Cola asíncrona de jobs con workers concurrentes (`backend/app/job_queue.py`,
  `job_store.py`) — reemplaza el modelo síncrono de un documento por
  request.
- Watcher de carpeta `inbound/` con detección segura y dedupe
  (`backend/app/inbound_watcher.py`).
- Nueva API `/api/v1/jobs*` (crear, listar, consultar, reintentar,
  confirmar, descargar, exportar lote, estado/config de inbound, stream
  SSE de progreso) — ver `backend/app/main.py`.
- Frontend nuevo (`frontend/index.html`, `frontend/src/app.js`,
  `frontend/src/style.css`): cola visual, progreso, campos con confianza,
  edición/confirmación, descarga individual y export de lote.
- Seguridad: validación de extensión/MIME/tamaño, sanitización de nombres,
  prevención de path traversal, sin egress de documentos a servicios
  externos.
- Motor EasyOCR se conserva declarado en `backend/requirements.txt` como
  fallback interno opcional, deshabilitado por defecto (no se elimina).

**Explícitamente fuera de alcance de esta feature:**
- Multiusuario, autenticación, SaaS, integraciones ERP productivas.
- Proveedores/plantillas más allá de `LITORAL_GAS` y `CEVT` (la
  arquitectura de plantillas queda extensible, pero agregar un tercer
  proveedor es una feature aparte).
- Cualquier servicio OCR cloud pago.
- Benchmark de lote de 400 documentos con muestras sintéticas (requiere
  datos locales no versionados; queda como validación pendiente, no como
  criterio de cierre de esta feature).

**Cambio de comportamiento a declarar explícitamente (no es un descarte
silencioso):** esta rama reescribe `backend/app/main.py` sobre una API de
jobs nueva. Los endpoints anteriores `/api/v1/capture` (legacy original) y
`/api/v1/process` + `/api/v1/process/{job_id}/*` (de T4, nunca mergeados a
`develop`) **no existen** en esta versión de `main.py`. No es una
regresión respecto de `develop` (que nunca tuvo los endpoints de T4), pero
sí reemplaza el único endpoint legacy que si estaba en `develop`
(`/api/v1/capture`). Se acepta como parte del alcance porque el flujo de
jobs lo reemplaza funcionalmente con más capacidad (cola, multi-doc,
confirmación), y `backend/tests/test_ocr_gas.py` (que sigue en verde)
prueba la extracción a nivel de función, no el endpoint HTTP, por lo que
no hay cobertura de test dependiente del endpoint viejo.

## Contexto

`develop` (post-adopción del circuito AI-Native, PR #1) tenía como
`ocr` únicamente EasyOCR — motor declarado "experimental" en
`docs/tecnica/arquitectura.md` (ADR-006), con precisión y velocidad
pendientes de medir contra alternativas. Esta feature es la primera
evaluación real con evidencia: mide EasyOCR (~30 s/documento, ya conocido
por uso previo del equipo) contra RapidOCR/ONNX con arquitectura two-pass
ROI (~2.35–2.57 s en caliente, medido y documentado en el spec original).
La mejora es de un orden de magnitud, justifica el reemplazo del motor
principal y resuelve ADR-006.

Existía en paralelo una rama distinta (`feature/t4-mvp-web-operable`,
EasyOCR, alcance GAS único, endpoint único síncrono) que llegó a estar
implementada y testeada (154 tests) pero nunca se mergeó. El 2026-08-18 se
decidió explícitamente priorizar esta rama (`captura-ocr-local-agil`)
como la línea real hacia el MVP operable, por la mejora de rendimiento
medida. T4 queda archivada en el tag `archive/t4-mvp-web-operable`
(referencia histórica, no se descarta el commit).

## Criterios de aceptación

1. RapidOCR-onnxruntime + onnxruntime instalados y usados como motor
   principal (`backend/app/ocr_engine.py`); EasyOCR permanece declarado
   pero no es el motor activo por defecto.
2. Extracción two-pass ROI para los dos proveedores soportados
   (`LITORAL_GAS`/GAS, `CEVT`/ELECTRICITY), con clasificación de
   proveedor que **nunca** asigna GAS por defecto a un documento
   desconocido (`backend/app/classifier.py`).
3. Endpoint `POST /api/v1/jobs` acepta imagen o PDF; PDF usa texto nativo
   primero (`pdf_util.py`), OCR solo si no hay texto utilizable.
4. Ciclo completo de job vía API: crear → consultar estado/resultado →
   corregir/confirmar → descargar JSON confirmado → exportar lote.
5. Validación de seguridad: extensión/MIME/tamaño, sanitización de
   nombre de archivo, rechazo de path traversal (`backend/app/validators.py`,
   `backend/tests/test_security.py`).
6. Watcher de `inbound/` detecta archivos nuevos de forma segura (sin
   procesar archivos a medio escribir) y expone su estado vía
   `GET /api/v1/inbound/status`.
7. Suite de tests existente de `develop` (OCR/extracción/validación/T3.x)
   sigue en verde sin modificaciones — no hay regresión funcional en lo
   que el pipeline anterior ya cubría a nivel de función (no de endpoint
   HTTP, ver nota de alcance).
8. Tests nuevos de esta feature (`backend/tests/test_{api_jobs,classifier,
   image_prep,inbound_watcher,pdf_util,security,templates,validators}.py`,
   más `tests/e2e/test_e2e_playwright.py` gateado) pasan o se saltan con
   motivo explícito y verificable (no ausente en silencio).
9. Debe existir `docs/tecnica/captura-ocr-local-agil.md`, no vacío, con la
   arquitectura two-pass ROI, la decisión de motor (con evidencia de
   rendimiento) y las decisiones de diseño relevantes.
10. Debe existir `docs/usuario/captura-ocr-local-agil.md`, no vacío, con
    el propósito del flujo y al menos un ejemplo de uso HTTP real
    (request + response) para el ciclo crear job → confirmar → descargar.
11. Debe existir `runs/01-captura-ocr-local-agil/decision.md`, y enlaces
    exactos en `docs/tecnica/index.md` y `docs/usuario/index.md`.

## Casos borde a contemplar

- Documento de proveedor desconocido: no debe clasificarse como GAS por
  defecto (criterio de aceptación 2); debe quedar sin plantilla asignada
  o marcado como no reconocido.
- Campo ilegible por el motor OCR (caso real documentado: período de
  Litoral Gas, OCR devuelve `"DL73026"` en vez de `"01/2026"`): debe
  quedar `missing`/pendiente de corrección humana, **no** debe intentarse
  reparar con heurísticas de mapeo de caracteres (sería hardcodear una
  regla de negocio no declarada).
- PDF multipágina con páginas mixtas (algunas con texto nativo, otras
  escaneadas): cada página se evalúa independientemente antes de decidir
  si necesita OCR.
- Archivo con extensión válida pero contenido/MIME no correspondiente:
  debe rechazarse en validación, no en el motor OCR.
- Nombre de archivo con secuencias de path traversal (`../`, rutas
  absolutas): debe sanitizarse antes de cualquier escritura a disco.
- Cola con más jobs que workers disponibles: los jobs en espera deben
  quedar visibles en `GET /api/v1/jobs` con su estado real, no
  perderse ni bloquear la cola.
- Muestras privadas de facturas reales no presentes en el entorno (CI,
  otra máquina): los tests que las requieren deben saltarse con motivo
  explícito (`Muestras privadas locales no disponibles (gitignored)`),
  nunca fallar de forma opaca ni declararse `PASS` sin haber corrido.

## Riesgos / supuestos

- **Riesgo aceptado (declarado en el spec original, no descubierto
  tarde):** el período de Litoral Gas no es extraíble de forma fiable por
  PP-OCRv3 en el fixture usado; requiere corrección humana. No se
  considera bloqueante porque el flujo de confirmación humana existe
  para exactamente este caso.
- **Supuesto:** Python 3.14.7 es el único intérprete 3.x disponible en el
  entorno de desarrollo; PaddleOCR se descartó por no tener wheel para
  cp314 (documentado con evidencia en el spec original). Si el entorno de
  CI/producción usa una versión de Python distinta, debe revalidarse esa
  restricción antes de asumir que sigue aplicando.
- **Riesgo de concurrencia no verificado en esta ronda:** el spec original
  menciona que la concurrencia de workers puede degradar por contención
  de `onnxruntime`; el benchmark de lote (400 documentos) no se corrió en
  esta verificación (requiere las muestras privadas/sintéticas locales,
  no presentes en este entorno) — queda como `NOT_RUN`, no como `PASS`
  inventado.
- **Cambio de API aceptado, no accidental:** ver nota en "Alcance" sobre
  el retiro de `/api/v1/capture` y `/api/v1/process`.
