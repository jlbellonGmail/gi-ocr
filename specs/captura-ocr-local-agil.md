# Captura OCR Local Ágil — Especificación

## Objetivo
Experiencia operable, rápida y 100% local para capturar facturas (imagen/PDF),
procesarlas con OCR local, extraer/validar campos, editar y exportar — sin nube ni APIs pagas.

## Estado asumido
- Backend FastAPI existente (T3.1–T3.5) con EasyOCR como motor.
- Worktree `captura-ocr-local-agil` desde develop `70a912d`.
- Python 3.14.7 (única 3.x disponible). PaddlePaddle no posee wheel cp314.

## Alcance
- Motor OCR local: **RapidOCR (PP-OCRv3) + ONNX Runtime** reemplazando EasyOCR.
- Arquitectura two-pass ROI-focalizada: detección full + rec selectivo sobre bandas del template.
- Plantillas: Litoral Gas (GAS) y CEVT (ELECTRICITY) con ROI normalizadas + anclas + regex + validación tipada.
- Multi-entrada web: imagen, PDF, cámara, múltiple, drag&drop, selector de directorio (donde el navegador lo permita).
- Cola asíncrona no bloqueante con procesamiento concurrente (workers).
- Watcher de carpeta inbound (detección segura, dedupe, estados ready/failed).
- PDF: texto nativo primero (pypdfium2); OCR solo en páginas sin texto utilizable; multipágina.
- Interfaz profesional responsive: cola, progreso, proveedor detectado, campos+confianza, accepted/rejected/missing, edición, confirmación, descarga individual y export de lote.
- Seguridad: validación extensión/MIME/tamaño, sanitización de nombres, anti path traversal, sin egress de documentos.
- Tests: unitarios, integración, facturas privadas (gated), variantes transformadas, E2E real con Playwright + capturas.
- Benchmark reproducible: frío, caliente, p50/p95, lote 400 variantes, memoria.

## Fuera de alcance
- Multiusuario, auth, SaaS, integraciones ERP productivas.
- Eliminar legacy EasyOCR sin reemplazo probado (se conserva como fallback interno opcional deshabilitado por defecto).
- Otros proveedores además de Litoral Gas y CEVT (arquitectura extensible).
- Servicio cloud pago.

## Motor OCR — decisión con evidencia
- Candidato inicial PaddleOCR PP-OCR Mobile: **descartado** por ausencia de wheel para Python 3.14
  (`pip install paddlepaddle` → `No matching distribution found`).
- **Elegido: RapidOCR-onnxruntime 1.2.3 + onnxruntime 1.28.0** (PP-OCRv3, modelos ONNX bundled,
  licencia Apache-2.0 / onnxruntime MIT). Open source, local, sin costo por página, sin egress.
- Modelos cargados **una sola vez** al iniciar el servicio (singleton).
- Optimización de rendimiento medida: dos médicos (det+rec) por separado.
  Full-page rec ~100–130 ms/caja × 130–190 cajas ≈ 13–25 s → **inaceptable**.
  Two-pass ROI: detección full-res (~1.1–1.4 s) + rec selectivo sobre boxes en bandas del template
  (~1.45–1.6 s) ≈ **2.35–2.57 s hot**. OCR completo únicamente como fallback para desconocidos.
- Reconocedor nunca asigna GAS por defecto a un documento desconocido.

## Campos y valores esperados (contrato expected.local.json, NO hardcoded en extractor)
Litoral Gas: provider=LITORAL_GAS, service=GAS, cliente=0045630002, periodo=01/2026,
  comprobante=0081-57501806, fecha_emision=12/03/2026, vencimiento=01/04/2026, total=13429.89.
  Nota: el periodo "01/2026" es ilegible para PP-OCRv3 (OCR→"DL73026"); queda missing y se
  corrige por HITL (demostrado en E2E). No se mapea D→0 (sería hardcodear reglas de negocio).
CEVT: provider=CEVT, service=ELECTRICITY, cliente=0515440001, medidor=0006071353,
  periodo=06/2026, comprobante=0009-03883672, fecha_emision=09/06/2026,
  vencimiento=19/06/2026, codigo_pago_electronico=0515440001, total=47061.59.

## ROI normalizadas (ancla + banda y/x con tolerancia)
Las ROI usan coordenadas normalizadas [0,1] relativas al tamaño del documento (no píxeles
absolutos) y son tolerantes a desplazamiento/escala. Se aplica corrección de orientación y
perspectiva antes del OCR. Cada campo define: anchor (texto/posición esperada), banda y-range,
banda x-range, regex, validador tipado, score mínimo.

## Flujo canónico
entrada → validación archivo → corrección orientación/perspectiva/escala → clasificación
proveedor → selección plantilla → ROI ancladas → detección OCR → rec selectivo → regex +
normalización + validación tipada → accepted/rejected/missing → corrección humana →
confirmación → persistencia/exportación.

## API (superconjunto del T4 existente, sin romper endpoints previos salvo reemplazo de motor)
- POST /api/v1/jobs (upload uno o varios) → crea jobs en cola.
- GET /api/v1/jobs → estado de la cola.
- GET /api/v1/jobs/{id} → resultado (campos, confianza, estados).
- POST /api/v1/jobs/{id}/retry → reintento individual.
- POST /api/v1/jobs/{id}/confirm → confirmación de revisión humana.
- GET /api/v1/jobs/{id}/download → JSON confirmado.
- GET /api/v1/jobs/{id}/preview → imagen/preview.
- GET /api/v1/export → export del lote (JSON/CSV).
- GET /api/v1/inbound/status → estado del watcher de carpeta.
- POST /api/v1/inbound/config → configurar carpeta inbound.
- GET /api/v1/stream → SSE de progreso de la cola.

## Criterios de aceptación (Completion Gate de rendimiento)
- doc individual caliente objetivo ≤ 3 s (medido 2.35–2.57 s).
- p95 ≤ 5 s.
- lote 400 docs ≤ 10 min (vía concurrencia de workers; medir).
- interfaz permite seguir cargando durante el procesamiento.
- validate_project PASS, pytest PASS, git diff --check sin errores.
- E2E real (Playwright) con capturas: Litoral Gas (final confirmado con todos los valores
  vía corrección del periodo) y CEVT (todos los valores auto), sin confundir CEVT con GAS.
- sin tráfico a servicios externos (verificable).
- licencias open source verificadas.

## Riesgos
- Periodo Litoral Gas no extraíble por OCR → requiere HITL (aceptado, demostrado en E2E).
- PPC/variantes sintéticas miden robustez técnica, no diversidad documental real.
- Concurrencia puede degradear por contención de onnxruntime; ajustar workers según benchmark.

## Resultado esperado
READY_FOR_PRODUCT_HITL con evidencia completa (rama/worktree, hashes, arquitectura, dependencias
y licencias, archivos, tests, valores extraídos, benchmark, E2E visual, informe Inspector,
riesgos, commit local, confirmación main/develop sin modificar / sin merge / sin push).