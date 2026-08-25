# Spec: 09-confianza-y-enrutamiento-hitl

## Objetivo
Definir scores y umbrales por campo para enrutamiento automático: autoaceptar alta confianza, enviar baja confianza a revisión humana, y bloquear falsos positivos sensibles. Registrar trazabilidad completa: confianza OCR, confianza de extracción, validación semántica y decisión final.

## Alcance
- Configuración de umbrales por campo en `services.ini` (sección `Field.<nombre>.*`)
- Lógica de decisión en `capture_pipeline.py` (etapa de extracción/validación)
- Nuevo campo `confidence` en salida estructurada por campo
- Nuevo campo `decision` por campo: `auto_accepted` | `needs_review` | `blocked` | `missing`
- Integración con `review_service.py` para campos `needs_review`
- Tests de regresión y casos borde

## Estado actual (baseline)
- `ocr_engine.py`: OCR two-pass devuelve `score` por caja (0.0-1.0)
- `capture_pipeline.py`: calcula `field_scores[field] = max(score de cajas en banda)` (línea 143-154)
- `validators.py`: validadores tipados devuelven `(valor_normalizado, reason)` o `(None, reason)`
- `review_service.py`: confirmación humana sobre `validated_fields` del job
- `services.ini`: configuración por servicio con `Field.<nombre>.Label`, `Type`, `Required`, `Example`, `Regex`, `Patterns` (opcional)

## Cambios requeridos

### 1. Extensión de `services.ini` (esquema Field.<nombre>.*)
Agregar claves opcionales por campo:
- `Field.<nombre>.ConfidenceAutoAccept` (float 0.0-1.0, default 0.85): umbral para autoaceptar
- `Field.<nombre>.ConfidenceNeedsReview` (float 0.0-1.0, default 0.50): umbral para enviar a revisión
- `Field.<nombre>.Sensitive` (true/false, default false): campos sensibles que bloquean falsos positivos
- `Field.<nombre>.BlockOnValidationFail` (true/false, default true): si validación semántica falla, bloquear vs solo rechazar

Reglas de validación del esquema (en `services_config.py`):
- `ConfidenceAutoAccept` > `ConfidenceNeedsReview` (si ambos declarados)
- Valores en rango [0.0, 1.0]
- `Sensitive` y `BlockOnValidationFail` solo `true`/`false`

### 2. Estructura de datos de confianza por campo
En `capture_pipeline.py`, extendida la salida estructurada:
```python
"structured_output": {
    ...
    "field_confidence": {
        "cliente": {
            "ocr_score": 0.92,           # max score OCR en banda
            "extraction_score": 0.88,    # score regex/extracción (heurística)
            "validation_passed": true,   # validator devolvió valor
            "validation_reason": None,   # reason si falló
            "final_score": 0.88,         # score combinado para decisión
            "decision": "auto_accepted", # auto_accepted | needs_review | blocked | missing
            "thresholds": {"auto": 0.85, "review": 0.50},
            "sensitive": false
        }
    }
}
```

### 3. Lógica de decisión (en `capture_pipeline.py`, dentro del loop de campos)
Para cada campo con candidato:
1. `ocr_score` = max score OCR en banda (ya existe en `field_scores`)
2. `extraction_score` = heurística: 1.0 si regex matcheó grupo 1, 0.7 si solo anchor, 0.3 si genérico
3. `final_score` = `(ocr_score * 0.6) + (extraction_score * 0.4)` (pesos configurables futuros)
4. `validation_passed`, `validation_reason` = resultado del validator
5. Decisión:
   - Si `validation_passed` y `final_score >= ConfidenceAutoAccept` → `auto_accepted`
   - Si `validation_passed` y `ConfidenceNeedsReview <= final_score < ConfidenceAutoAccept` → `needs_review`
   - Si `validation_passed` y `final_score < ConfidenceNeedsReview` → `needs_review`
   - Si NOT `validation_passed`:
     - Si `Sensitive == true` O `BlockOnValidationFail == true` → `blocked`
     - Sino → `rejected` (comportamiento actual, va a `rejected_fields`)
   - Si no hay candidato → `missing`

### 4. Integración con revisión humana
- Campos con `decision == "needs_review"` se incluyen en frontend para revisión
- `review_service.py`: al confirmar, registrar `confidence_at_review` y `decision_at_review` en `confirmation_metadata`
- Frontend: mostrar score y decisión automática, permitir override humano

### 5. Registro en auditoría / expediente
- `field_confidence` se persiste en JSON confirmado y `.DATA`
- `storage_bridge_writer.py`: incluir `field_confidence` en exportación legacy
- `field_reporting_processor.py`: agregar sección `confidence_summary` en reporte

## Criterios de aceptación

### Funcionales
1. ✅ Configuración de umbrales por campo en `services.ini` (claves nuevas validadas)
2. ✅ Cálculo de `ocr_score`, `extraction_score`, `final_score` por campo en pipeline
3. ✅ Decisión automática `auto_accepted` / `needs_review` / `blocked` / `missing`
4. ✅ Campo `sensitive` bloquea falsos positivos aunque pase regex
5. ✅ Campo `BlockOnValidationFail` controla comportamiento ante fallo semántico
6. ✅ Salida estructurada incluye `field_confidence` con trazabilidad completa
7. ✅ Integración con `review_service.py`: campos `needs_review` van a revisión humana
8. ✅ Persistencia en JSON confirmado y `.DATA`

### No funcionales
- No romper pipeline existente (compatibilidad hacia atrás: defaults si claves ausentes)
- Tests unitarios para lógica de decisión (cobertura > 90%)
- Tests de integración E2E con fixtures GAS/CEVT
- Documentación técnica y de usuario

### Documentación (obligatoria por contrato)
- ✅ `docs/tecnica/confianza-y-enrutamiento-hitl.md`: algoritmo, umbrales, casos borde, decisiones de diseño
- ✅ `docs/usuario/confianza-y-enrutamiento-hitl.md`: propósito, ejemplos HTTP, configuración
- ✅ Enlaces exactos en `docs/tecnica/index.md` y `docs/usuario/index.md`
- ✅ `runs/09-confianza-y-enrutamiento-hitl/decision.md` con decisiones demostrables

## Archivos a modificar
- `backend/app/capture_pipeline.py`: lógica de decisión, salida `field_confidence`
- `backend/app/services_config.py`: validación esquema nuevas claves, lectura
- `backend/config/services.ini`: ejemplos de configuración por campo
- `backend/app/review_service.py`: registrar confidence en confirmación
- `backend/app/field_reporting_processor.py`: agregar `confidence_summary`
- `backend/app/storage_bridge_writer.py`: exportar `field_confidence`
- `backend/tests/test_confidence_routing.py`: tests unitarios (nuevo)
- `backend/tests/test_capture_pipeline.py`: tests integración extendidos
- `docs/tecnica/confianza-y-enrutamiento-hitl.md` (nuevo)
- `docs/usuario/confianza-y-enrutamiento-hitl.md` (nuevo)
- `docs/tecnica/index.md`: enlace
- `docs/usuario/index.md`: enlace

## Riesgos y mitigaciones
- **Riesgo**: Umbrales mal calibrados → autoaceptar errores o saturar revisión
  - **Mitigación**: Defaults conservadores (0.85/0.50), configurables por campo, observabilidad via `field_report`
- **Riesgo**: Campos sensibles (ej. `total`, `comprobante`) bloqueados incorrectamente
  - **Mitigación**: `Sensitive=true` solo para campos críticos, `BlockOnValidationFail=false` para permitir revisión
- **Riesgo**: Regresión en campos sin configuración explícita
  - **Mitigación**: Defaults en código, validación de esquema no obliga a declarar claves nuevas

## Estimación
- Implementación: 2-3 días
- Tests: 1 día
- Documentación: 0.5 días
- Total: ~3.5 días