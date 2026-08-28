# Decisiones: 10-consola-revision-humana-profesional

## Resumen

Implementación completa de la consola de revisión humana mobile-first con trazabilidad de motivos, integrada con el pipeline OCR existente (features 01, 09).

## Decisiones técnicas demostrables

### 1. Motivo obligatorio en backend (`review_service.py`) + frontend
**Evidencia**: `review_service.confirm_review()` lanza `ValueError` si `state ∈ {corrected, unresolved}` y `reason` vacío. `main.py` captura y devuelve `HTTP 400`. Frontend deshabilita botón confirmar hasta que todos los motivos requeridos estén presentes.
**Origen**: Spec criterio 1, 5; ADR trazabilidad auditoría.

### 2. Endpoint `/api/v1/jobs/{job_id}/image` separado
**Evidencia**: Nuevo endpoint en `main.py` que sirve `FileResponse` desde `output/uploads/` usando `source_document_reference` del job original. Fallback por prefijo `job_id[:8]`.
**Origen**: Spec criterio 4; decisión de diseño documentada en doc técnica §2.

### 3. `job_queue.py` pasa `file_path` como `source_ref`
**Evidencia**: Línea 138: `process_document(file_path, file_path)` (antes era `job["original_name"]`).
**Origen**: Necesario para que `source_document_reference` en structured_output sea path absoluto usable por endpoint imagen.

### 4. Mapeo decisión automática → acción por defecto en UI
**Evidencia**: `renderReady()` en `app.js` líneas ~280-290: `auto_accepted→confirmado`, `needs_review→corregido`, `blocked/missing→unresolved`.
**Origen**: Spec criterio 7; doc técnica §Decisiones #4.

### 5. Motivo prellenado desde `rejected_fields[field].reason`
**Evidencia**: `renderReady()` linea ~310: `prefillReason = rejectedInfo ? rejectedInfo.reason : ""`.
**Origen**: Spec criterio 4; doc técnica §Decisiones #5.

### 6. Labels de campos desde `/api/v1/services/{provider}`
**Evidencia**: `getFieldLabels(provider)` en `app.js` hace fetch y cachea; fallback a nombre de campo.
**Origen**: Spec criterio 5; `services.ini` ya tiene `Field.X.Label`.

### 7. Scores visibles (final_score)
**Evidencia**: Columna "Scores" en tabla muestra `final_score` con 2 decimales; tooltip con OCR/Extracción/Final.
**Origen**: Spec criterio 5; doc técnica §Decisiones #6.

### 8. Image viewer con zoom/pan touch-friendly
**Evidencia**: `setupImageViewer()` en `app.js`: wheel zoom (Ctrl+wheel), drag pan, pinch zoom, touch drag, toolbar botones.
**Origen**: Spec criterio 5, 6 (accesibilidad mobile).

### 9. Validación cliente + servidor
**Evidencia**: `setupFieldValidation()` deshabilita botón confirmar si falta motivo; backend valida de nuevo.
**Origen**: Spec criterio 1, 5; defensa en profundidad.

### 10. Persistencia `correction_reasons` en JSON confirmado
**Evidencia**: `review_service.py` guarda `correction_reasons` en `confirmation_metadata` y lo retorna en respuesta.
**Origen**: Spec criterio 2; trazabilidad auditoría (feature 11 futura).

## Archivos modificados

### Backend
- `backend/app/review_service.py` — validación y persistencia `reason`
- `backend/app/main.py` — `FieldCorrection.reason`, endpoint `/image`, manejo `ValueError`
- `backend/app/job_queue.py` — pasa `file_path` como `source_ref`

### Frontend
- `frontend/src/app.js` — `renderReady()` completa reescrita, `getFieldLabels`, `setupFieldValidation`, `setupImageViewer`, `confirmJob` con `reason`
- `frontend/src/style.css` — estilos para image viewer, fields table, decision badges, reason inputs, mobile ≤700px

### Documentación
- `docs/tecnica/consola-revision-humana-profesional.md`
- `docs/usuario/consola-revision-humana-profesional.md`
- `docs/tecnica/index.md` + `docs/usuario/index.md` (enlaces agregados)

## Tests

- `backend/tests/test_review_confirmation.py` (por crear en QA): reason obligatorio, persistencia, endpoint imagen
- Manual: fixture GAS → flujo completo → verificar JSON confirmado con `correction_reasons`

## Riesgos mitigados

| Riesgo | Mitigación |
|--------|------------|
| Imagen no encontrada | Endpoint 404 claro; fallback búsqueda en uploads |
| Servicio sin labels | Fallback a nombre de campo técnico |
| PDF nativo | Endpoint sirve PDF con media_type correcto |
| Motivo vacío en API directa | Backend valida y rechaza 400 |

## Próximos pasos (fuera de alcance esta feature)

- Tests automatizados frontend (Playwright) — feature 17
- Auditoría por operador (quién corrigió qué) — feature 11
- Historial de revisiones por documento — feature 20
- Thumbnail + lazy load imagen grande — optimización futura