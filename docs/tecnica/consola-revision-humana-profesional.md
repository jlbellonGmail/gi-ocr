# Consola de Revisión Humana Profesional

## Propósito

Interfaz mobile-first para que un operador valide, corrija o rechace los campos extraídos por OCR con trazabilidad completa antes de exportar el JSON confirmado a `storage_bridge/`.

## Arquitectura

### Flujo de datos

```
Imagen → OCR (RapidOCR/ONNX) → Extracción regex por banda → Validación semántica
  → candidate_fields / validated_fields / rejected_fields / missing_fields
  → field_confidence.decision (auto_accepted/needs_review/blocked/missing)
  → Frontend: renderReady() muestra tabla editable con:
      - Label (desde services.ini)
      - Candidato (OCR bruto)
      - Valor validado (editable)
      - Decisión automática (badge)
      - Acción operador (select: confirmado/corregido/sin resolver)
      - Motivo (input, obligatorio si acción ≠ confirmado)
      - Scores (OCR/Extracción/Final)
  → POST /api/v1/jobs/{id}/confirm con {field, state, final_value, reason}
  → review_service.confirm_review() valida, persiste correction_reasons
  → JSON confirmado en output/confirmed/{job_id}.confirmed.json
```

### Componentes backend

1. **`review_service.py`** (`confirm_review`):
   - Acepta `reason` en cada corrección
   - Valida: `reason` obligatorio si `state ∈ {corrected, unresolved}`
   - Persiste `correction_reasons: Dict[str, str]` en `confirmation_metadata`
   - Retorna `correction_reasons` en respuesta

2. **`main.py`**:
   - `FieldCorrection` model extendido con `reason: Optional[str]`
   - `POST /api/v1/jobs/{job_id}/confirm`: captura `ValueError` → `HTTP 400`
   - `GET /api/v1/jobs/{job_id}/image`: sirve imagen original desde `output/uploads/`
     - Usa `source_document_reference` guardado en `structured_output`
     - Fallback: busca en `output/uploads/` por prefijo `job_id[:8]`
     - Devuelve `FileResponse` con `media_type` según extensión

3. **`job_queue.py`**:
   - `enqueue` pasa `file_path` como `source_ref` a `process_document`
   - Así `source_document_reference` = path absoluto al upload

### Componentes frontend

1. **`app.js`** - `renderReady()` reescrita:
   - **Image viewer**: `<img>` con zoom (wheel/pinch), pan (drag), toolbar (+/−/reset)
   - **OCR text panel**: `<details>` colapsable con texto bruto monoespaciado
   - **Fields table** (scroll horizontal en mobile):
     - Columnas: Label, Candidato, Valor validado (input), Decisión (badge), Acción (select), Motivo (input), Scores
     - Filas generadas dinámicamente desde `structured_output` + `field_confidence`
     - Labels desde `GET /api/v1/services/{provider}` (cacheado)
   - **Validación en cliente**: botón "Confirmar revisión" deshabilitado hasta que todos los campos con acción ≠ confirmed tengan motivo
   - **Confirmación**: envía array `confirmed_fields` con `reason`

2. **`style.css`** - nuevos estilos:
   - `.image-viewer`, `.image-toolbar`, zoom/pan touch-friendly
   - `.fields-table` responsive con `min-width` y `overflow-x: auto`
   - `.decision-badge` para 4 estados (auto/review/blocked/missing)
   - `.reason-input` con estados visuales (required/optional/invalid)
   - Breakpoints mobile ≤700px

### Estructura de datos confirmada

```json
{
  "job_id": "...",
  "document_type": "GAS",
  "confirmed_fields": { "importe": "23.345,56", ... },
  "validated_fields": { ... },
  "corrections": ["importe"],
  "summary": { "confirmed_count": 3, "corrected_count": 2, "unresolved_count": 0 },
  "confirmation_metadata": {
    "final_filename": "GAS_a1b2c3d4.json",
    "confirmed_at": "2026-08-25T...",
    "original_source": "output/uploads/...",
    "confidence_at_review": { "importe": { "decision": "needs_review", "final_score": 0.72, ... } },
    "decision_at_review": { "importe": "corrected", ... },
    "correction_reasons": { "importe": "OCR leyó 23.345,66; corregido a 23.345,56 según total visible" }
  },
  "original_result_ref": "..."
}
```

## Decisiones de diseño

### 1. Motivo obligatorio en backend y frontend
**Por qué**: defensa en profundidad. El frontend valida UX (botón deshabilitado), el backend valida integridad (400 si falta). Evita datos incompletos si se llama API directamente.

### 2. Endpoint de imagen separado (`/image`)
**Por qué**: 
- Separación de responsabilidades: `/original` = JSON, `/image` = binario
- CORS/cache headers independientes
- El frontend puede cargar imagen con `<img src="...">` nativo (sin JS fetch + blob)
- Permite CDN/proxy futuro solo para imágenes

### 3. `source_document_reference` = path absoluto al upload
**Por qué**: `job_queue.enqueue` ya tiene el path; pasarlo a `process_document` evita reconstruirlo. El path es estable (nombre aleatorio en `output/uploads/`).

### 4. Mapeo decisión automática → acción por defecto
| Decisión (field_confidence.decision) | Acción por defecto | Motivo requerido |
|---|---|---|
| `auto_accepted` | confirmado | No |
| `needs_review` | corregido | Sí |
| `blocked` | sin resolver | Sí |
| `missing` | sin resolver | Sí |

**Razonamiento**: `auto_accepted` supera umbral alto → confianza para confirmar sin fricción. `needs_review` supera umbral bajo pero no alto → probable corrección. `blocked` = validación falló en campo sensible → operador decide si anular. `missing` = no hay candidato → operador anota por qué.

### 5. Motivo prellenado desde `rejected_fields[field].reason`
**Por qué**: el validador semántico ya produjo una razón técnica (ej. "fecha inválida", "formato importe incorrecto"). Reutilizarla evita retrabajo y da contexto al operador.

### 6. Scores visibles (final_score)
**Por qué**: trazabilidad. El operador ve `final_score = 0.6*ocr + 0.4*extraction` y entiende por qué la decisión automática fue `needs_review` vs `auto_accepted`.

## Casos borde

- **Imagen no encontrada**: endpoint `/image` devuelve 404 con mensaje claro; frontend muestra placeholder
- **Job sin upload (inbound watcher)**: `source_document_reference` puede ser path en `inbound/`; endpoint busca en `output/uploads/` por fallback
- **Servicio desconocido**: labels vacíos → usa nombre de campo como fallback
- **Campo `provider`/`service`**: excluidos de tabla (son metadatos, no datos del comprobante)
- **PDF nativo**: `source_document_reference` = path al PDF; endpoint sirve PDF (media_type application/pdf)

## Testing

- `backend/tests/test_review_confirmation.py`: reason obligatorio, persistencia, endpoint imagen
- Manual: fixture GAS → verificar contadores, descarga JSON con `correction_reasons`

## Referencias

- ADR: `docs/tecnica/arquitectura.md` (config en `services.ini`, no JSON)
- Feature 09: `confianza-y-enrutamiento-hitl` (field_confidence.decision)
- Feature 01: `captura-ocr-local-agil` (upload en output/uploads/)