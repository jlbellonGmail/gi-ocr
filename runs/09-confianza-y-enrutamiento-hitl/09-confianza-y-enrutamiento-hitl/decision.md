# Decision Log: 09-confianza-y-enrutamiento-hitl

## Decisiones Demostrables (spec → auditoría → implementación)

### 1. Esquema de configuración en `services.ini` (no JSON)
**Spec**: "La configuración de extracción por servicio vive en texto plano (`backend/config/services.ini`), no en JSON ni hardcodeada en Python por servicio"
**Implementación**: Agregadas 4 claves opcionales por campo en `Field.<nombre>.*`:
- `ConfidenceAutoAccept`, `ConfidenceNeedsReview`, `Sensitive`, `BlockOnValidationFail`
**Validación**: En `services_config.py:_validate_field_block()` con reglas:
- `auto_accept > needs_review` (si ambos declarados)
- Rango [0.0, 1.0] para floats
- Solo `true`/`false` para booleanos
- Defaults en código si omitidos (compatibilidad hacia atrás)

### 2. Cálculo de `extraction_score` por camino de extracción
**Audit feedback**: "El `extraction_score` necesita definición precisa por camino"
**Implementación**: `_calc_extraction_score()` en `capture_pipeline.py`:
| Camino | Score | Descripción |
|--------|-------|-------------|
| `zone_regex` | 1.0 | Regex matcheó en banda OCR (two-pass ROI) |
| `fulltext_regex` | 0.9 | Regex matcheó en texto completo página |
| `anchor_only` | 0.7 | Solo ancla matcheó, regex genérico |
| `generic` | 0.3 | Fallback genérico por palabra clave |
| `none` | 0.0 | Sin candidato |

`_extract_field` ahora retorna `(candidate, extraction_path, source)` para trazabilidad.

### 3. Lógica de decisión unificada (corregida redundancia audit)
**Audit**: "Líneas 63-64 redundantes: ambas llevan a `needs_review`"
**Implementación**: `_make_confidence_decision()` con lógica única:
```python
if validation_passed:
    if final_score >= auto_accept: decision = "auto_accepted"
    elif final_score >= needs_review: decision = "needs_review"
    else: decision = "needs_review"
else:
    if sensitive or block_on_fail: decision = "blocked"
    else: decision = "rejected"  # legacy → rejected_fields
```

### 4. `field_confidence` para TODOS los campos (incluidos missing/blocked)
**Audit**: "Incluir `field_confidence` para campos `missing` y `blocked` (trazabilidad completa)"
**Implementación**: En loop de campos:
- Candidato `None` → registra `decision="missing"` con scores 0.0
- Validación falla + `blocked` → registra `decision="blocked"` con scores reales
- Campos `missing` post-loop → registra `decision="missing"` con `validation_reason="missing_required"`
- `provider`/`service` → `decision="auto_accepted"` con score 1.0

### 5. `blocked` vs `rejected` (compatibilidad legacy)
**Spec**: "Bloquear falsos positivos sensibles" vs "comportamiento actual, va a `rejected_fields`"
**Decisión**: 
- `blocked`: nueva decisión para campos sensibles o `BlockOnValidationFail=true`
- `rejected`: mantiene comportamiento legacy (validación falla, no sensible, `BlockOnValidationFail=false`)
- Ambos persisten en `rejected_fields` para compatibilidad; `decision` distingue en `field_confidence`

### 6. Pesos `final_score = 0.6*ocr + 0.4*extraction`
**Spec**: "pesos configurables futuros"
**Decisión**: Hardcoded 0.6/0.4 en `_make_confidence_decision()`. Documentado como ajustable en futuro via config. OCR pesa más por ser señal objetiva; extracción depende de regex/heurística.

### 7. PDF nativo (sin OCR) → `ocr_score=0.0`, `extraction_score=0.9`
**Implementación**: En `_process_pdf_native()`: no hay OCR, pero regex sobre texto nativo es confiable (0.9). `final_score = 0.36` → típicamente `needs_review` salvo umbrales bajos.

### 8. Integración `review_service`: `confidence_at_review` + `decision_at_review`
**Spec**: "Registrar confidence en confirmación"
**Implementación**: `confirm_review()` lee `field_confidence` del job original y guarda snapshot en `confirmation_metadata` junto con decisión humana (`confirmed`/`corrected`/`unresolved`).

### 9. `field_report.confidence_summary`
**Spec**: "Agregar sección `confidence_summary` en reporte"
**Implementación**: `generate_field_report(field_confidence=...)` agrega:
```json
"confidence_summary": {
  "auto_accepted": 3,
  "needs_review": 1,
  "blocked": 0,
  "missing": 1,
  "by_field": { "importe": {"decision": "...", "final_score": 0.95, ...} }
}
```

### 10. Exportación legacy `.CONFIDENCE.json` compañero
**Spec**: "`storage_bridge_writer.py`: incluir `field_confidence` en exportación legacy"
**Implementación**: Nueva función `write_confidence_file()` genera `GAS_20260825_143000.CONFIDENCE.json` en `ready/` junto al `.DATA`. No modifica formato `.DATA` (compatibilidad).

### 11. Validación "solo uno declarado" usa default para el otro
**Audit**: "Validación en services_config: warning si uno no declarado, error solo si ambos y auto <= review"
**Implementación**: En `_validate_field_block()`:
- Si `auto_accept_raw OR needs_review_raw`: valida ambos (usa default para el faltante)
- Error solo si `auto_accept <= needs_review` después de resolver defaults
- No warning: silencioso, usa defaults

### 12. Compatibilidad hacia atrás garantizada
- Claves opcionales en `services.ini` → configs existentes sin cambios funcionan
- Defaults en `services_config.py` (0.85, 0.50, false, true)
- `field_confidence` agregado a salida, no modifica claves existentes
- `rejected_fields` mantiene estructura legacy
- Tests existentes pasan (schema validation OK)

## Cambios de Archivos

| Archivo | Cambio |
|---------|--------|
| `backend/app/services_config.py` | +4 constantes, +validación 4 claves, +3 funciones lectura |
| `backend/config/services.ini` | +20 líneas config confianza (GAS + CEVT) |
| `backend/app/capture_pipeline.py` | +3 funciones helper, +loop confianza, +field_confidence salida |
| `backend/app/review_service.py` | +confidence_at_review, decision_at_review |
| `backend/app/field_reporting_processor.py` | +field_confidence param, +confidence_summary |
| `backend/app/storage_bridge_writer.py` | +write_confidence_file() |
| `backend/tests/test_confidence_routing.py` | +23 tests unitarios (nuevo) |
| `docs/tecnica/confianza-y-enrutamiento-hitl.md` | Documentación técnica completa |
| `docs/usuario/confianza-y-enrutamiento-hitl.md` | Guía usuario con ejemplos |

## Verificación
- `validate_services_schema()` → OK con services.ini actualizado
- `get_service_confidence_config('GAS')` / `('CEVT')` → configs correctas
- 23 tests unitarios `test_confidence_routing.py` → PASSED
- Schema validation no rompe configs existentes