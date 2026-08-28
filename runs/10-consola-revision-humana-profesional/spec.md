# Spec: 10-consola-revision-humana-profesional

## Resumen

Completar la consola de revisión humana mobile-first para que el operador pueda validar, corregir y rechazar campos extraídos por OCR con trazabilidad completa antes de exportar. La UI debe mostrar: imagen del documento, texto OCR bruto, candidatos por campo, campos validados, rechazados (con motivo), no encontrados; permitir edición manual de valores; requerir motivo al corregir/rechazar; y confirmación final que genere JSON confirmado listo para `storage_bridge/`.

## Contexto técnico

**Backend existente:**
- `capture_pipeline.py` → genera `structured_output` con:
  - `candidate_fields`: Dict[str, Optional[str]] — valor extraído por regex en banda
  - `validated_fields`: Dict[str, str] — pasó validación semántica
  - `rejected_fields`: Dict[str, Dict[str, str]] — `{value, reason}` donde `reason` viene del validador
  - `missing_fields`: Dict[str, None] — campos requeridos sin candidato
  - `field_confidence`: Dict[str, FieldConfidence] — `decision` ∈ {auto_accepted, needs_review, blocked, missing}, scores OCR/extracción/final, umbrales, flags sensitive/block_on_fail
- `review_service.py` → `confirm_review()` persiste `confirmed_doc` con `confirmed_fields`, `corrections[]`, `summary`, `confirmation_metadata.confidence_at_review`, `decision_at_review`
- API `/api/v1/jobs/{job_id}/confirm` recibe `confirmed_fields[]` con `{field, state, final_value}` donde `state` ∈ {confirmed, corrected, unresolved}

**Frontend existente (`app.js:renderReady`):**
- Muestra campos en grid con input editable, selector de estado (confirmed/corrected/unresolved), tag visual (accepted/rejected/missing), score
- NO muestra: imagen del documento, texto OCR bruto (solo en `<details>`), candidatos explícitos separados de validados, motivo de rechazo, campo para motivo de corrección/rechazo
- Confirmación envía solo `final_value` y `state` — no envía `reason`

**Gap a cubrir:**
1. **Imagen**: servir y mostrar imagen original/preparada en detail
2. **Texto OCR**: ya existe en `raw_ocr_text` pero solo en `<details>` — mejorar visibilidad
3. **Candidatos vs Validados**: mostrar ambos; candidato = lo que OCR+regex encontró; validado = tras validación semántica
4. **Motivo de rechazo**: `rejected_fields[field].reason` ya existe en backend — exponerlo en UI
5. **Motivo de corrección/rechazo manual**: nuevo campo obligatorio cuando `state` ≠ confirmed
6. **Confirmación final**: validar que todos los campos tengan estado y motivo si aplica; generar JSON confirmado con trazabilidad completa

## Criterios de aceptación

### Backend

1. **API confirm extendida**: `/api/v1/jobs/{job_id}/confirm` acepta `reason` opcional en cada `FieldCorrection`. Si `state` ∈ {corrected, unresolved}, `reason` es **obligatorio** (400 si falta).
2. **Persistencia de motivos**: `review_service.confirm_review` guarda `correction_reasons: Dict[str, str]` en `confirmed_doc.confirmation_metadata` y en cada campo corregido/rechazado.
3. **Validación de completitud**: antes de confirmar, verificar que no queden campos `needs_review`/`blocked` sin decisión explícita del operador (UI lo enforza, backend valida defensivamente).
4. **Imagen servible**: endpoint `GET /api/v1/jobs/{job_id}/image` devuelve la imagen original subida (desde `output/uploads/`) con headers de cache y CORS.

### Frontend

5. **Vista detail completa** (`renderReady` reescrita):
   - **Header**: nombre, estado, proveedor, botones acción
   - **Imagen**: visor con zoom/pan (touch-friendly), ocupa ancho completo en mobile
   - **Texto OCR**: panel colapsable con texto bruto monoespaciado
   - **Tabla de campos** (una fila por campo esperado según servicio):
     - Columna: Label del campo (desde `services.ini`)
     - Columna: Candidato (lo que OCR encontró, vacío si none)
     - Columna: Validado (valor final tras validación, editable)
     - Columna: Estado actual (badge: auto_accepted/needs_review/blocked/missing — desde `field_confidence.decision`)
     - Columna: Acción del operador (select: confirmado / corregido / sin resolver)
     - Columna: **Motivo** (input text, **obligatorio** si acción ≠ confirmado; prellenado con `rejected_fields[field].reason` si existe)
     - Columna: Scores (ocr/extraction/final) como badge pequeño
   - **Resumen contadores**: aceptados / corregidos / rechazados / sin resolver / faltantes
   - **Botón "Confirmar revisión"**: deshabilitado hasta que todos los campos tengan acción válida y motivo si aplica
6. **Accesibilidad mobile**: targets táctiles ≥44px, contraste AA, foco visible, labels asociados, ARIA en selectores y inputs, orden de tabulación lógico.
7. **Estados visuales claros**:
   - `auto_accepted`: verde, acción por defecto "confirmado", motivo no requerido
   - `needs_review`: ámbar, acción por defecto "corregido", motivo requerido
   - `blocked`: rojo, acción por defecto "sin resolver", motivo requerido
   - `missing`: gris, acción por defecto "sin resolver", motivo requerido (ej. "no visible en imagen")

### Documentación (obligatoria per AGENTS.md)

8. **`docs/tecnica/consola-revision-humana-profesional.md`**: arquitectura de la consola, estructura de datos, contrato API confirm, decisiones de UX (por qué motivo obligatorio, mapping decisions→default actions), trazabilidad de motivos.
9. **`docs/usuario/consola-revision-humana-profesional.md`**: guía de uso del operador, capturas de flujo, ejemplos de confirmación/corrección/rechazo, descarga JSON final.
10. **Enlaces en índices**: entradas exactas en `docs/tecnica/index.md` y `docs/usuario/index.md`.
11. **`runs/10-consola-revision-humana-profesional/decision.md`**: decisiones demostrables (ej. por qué motivo en backend y no solo frontend, por qué endpoint de imagen separado, manejo de `blocked` vs `rejected`).

### Testing

12. **Tests backend** (`backend/tests/test_review_confirmation.py`): validación de reason obligatorio, persistencia, endpoint imagen.
13. **Tests frontend** (manuales documentados en doc usuario): flujo completo con fixture GAS, verificación de contadores, descarga JSON confirmado con `correction_reasons`.

## Fuera de alcance

- Autenticación/roles (feature 11-auditoria-permisos-operador)
- Edición de banda/ROI o re-OCR (feature 20-expediente-auditoria-documental)
- Notificaciones push/email
- Historial de revisiones por documento (solo última confirmación)

## Dependencias

- Requiere feature 09-confianza-y-enrutamiento-hitl (ya implementado: `field_confidence.decision` existe)
- Requiere feature 01-captura-ocr-local-agil (imagen en `output/uploads/`)
- Usa `services.ini` para labels/orden de campos

## Riesgos

- **Imagen no encontrada**: job sin upload (inbound watcher) → endpoint imagen 404 con mensaje claro
- **Campos dinámicos**: servicios con distinta cantidad de campos → UI generada desde `structured_output` + `services.ini` labels
- **Motivo vacío en corrección**: validación both-side (frontend + backend) para evitar datos incompletos
- **Performance mobile**: imagen grande → servir thumbnail + original bajo demanda (fase 2, no bloqueante)

## Entregables

- `runs/10-consola-revision-humana-profesional/spec.md` (este archivo)
- Código backend: `review_service.py`, `main.py` (confirm endpoint), nuevo endpoint imagen
- Código frontend: `app.js` (renderReady reescrito), `style.css` (nuevos estilos)
- Documentación: `docs/tecnica/consola-revision-humana-profesional.md`, `docs/usuario/consola-revision-humana-profesional.md`
- Tests: `backend/tests/test_review_confirmation.py`
- `runs/10-consola-revision-humana-profesional/decision.md`
- Actualización `docs/tecnica/index.md`, `docs/usuario/index.md`