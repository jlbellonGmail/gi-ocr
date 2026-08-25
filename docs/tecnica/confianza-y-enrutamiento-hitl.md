# Confianza y Enrutamiento HITL

## Resumen
Sistema de scores y umbrales por campo para enrutamiento automático en el pipeline OCR:
- **auto_accepted**: alta confianza → aceptar sin intervención humana
- **needs_review**: confianza media → enviar a revisión humana
- **blocked**: falsos positivos sensibles → bloquear y requerir corrección manual
- **missing**: campo no encontrado → requerir entrada manual

Registra trazabilidad completa: confianza OCR, confianza de extracción, validación semántica y decisión final.

## Arquitectura

### Configuración (`services.ini`)
Nuevas claves por campo en sección `Field.<nombre>.*`:

| Clave | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `ConfidenceAutoAccept` | float [0.0-1.0] | 0.85 | Umbral para autoaceptar |
| `ConfidenceNeedsReview` | float [0.0-1.0] | 0.50 | Umbral para enviar a revisión |
| `Sensitive` | true/false | false | Campo sensible: bloquea si validación falla |
| `BlockOnValidationFail` | true/false | true | Bloquear (vs solo rechazar) si validación falla |

Reglas de validación:
- `ConfidenceAutoAccept > ConfidenceNeedsReview` (si ambos declarados)
- Valores en rango [0.0, 1.0]
- Booleanos solo `true`/`false` (sin variantes localizadas)

### Cálculo de Scores

#### `ocr_score`
Score máximo OCR de las cajas cuyo centro cae en la banda del campo (ya existía en `field_scores`).

#### `extraction_score`
Heurística según camino de extracción:
- `zone_regex`: 1.0 (regex matcheó en banda OCR)
- `fulltext_regex`: 0.9 (regex matcheó en texto completo página)
- `anchor_only`: 0.7 (solo ancla matcheó, regex genérico)
- `generic`: 0.3 (fallback genérico por palabra clave)
- `none`: 0.0 (sin candidato)

#### `final_score`
Combinación ponderada:
```
final_score = (ocr_score * 0.6) + (extraction_score * 0.4)
```

### Lógica de Decisión

```python
if validation_passed:
    if final_score >= ConfidenceAutoAccept:
        decision = "auto_accepted"
    elif final_score >= ConfidenceNeedsReview:
        decision = "needs_review"
    else:
        decision = "needs_review"
else:
    # Validación semántica falló
    if Sensitive or BlockOnValidationFail:
        decision = "blocked"
    else:
        decision = "rejected"  # comportamiento legacy → rejected_fields
```

Si no hay candidato → `decision = "missing"`

### Salida Estructurada (`field_confidence`)

```json
{
  "importe": {
    "ocr_score": 0.92,
    "extraction_score": 1.0,
    "final_score": 0.95,
    "validation_passed": true,
    "validation_reason": null,
    "decision": "auto_accepted",
    "thresholds": {"auto": 0.88, "review": 0.55},
    "sensitive": true,
    "block_on_validation_fail": true
  }
}
```

### Integración con Revisión Humana
- Campos `needs_review` aparecen en frontend para revisión
- `review_service.py` registra `confidence_at_review` y `decision_at_review` en `confirmation_metadata`
- Frontend muestra score y decisión automática, permite override humano

### Persistencia
- `field_confidence` en JSON confirmado (`review_service`)
- `field_confidence` en exportación `.DATA` + `.CONFIDENCE.json` (`storage_bridge_writer`)
- `confidence_summary` en reporte de campos (`field_reporting_processor`)

## Casos Borde

1. **Solo un umbral declarado**: usa default para el otro, valida `auto > review`
2. **Campo sin configuración**: usa defaults globales (0.85/0.50, sensitive=false, block=true)
3. **PDF nativo (sin OCR)**: `ocr_score=0.0`, `extraction_score=0.9` (regex sobre texto nativo)
4. **Calidad rechazada**: `field_confidence={}` vacío (no hay OCR)
5. **Provider UNKNOWN**: sin `field_confidence` (no hay template)

## Configuración por Defecto (services.ini)

### GAS
| Campo | AutoAccept | NeedsReview | Sensitive | BlockOnFail |
|-------|------------|-------------|-----------|-------------|
| importe | 0.88 | 0.55 | true | true |
| cliente | 0.85 | 0.50 | false | false |
| nro_medidor | 0.80 | 0.45 | false | false |
| a_pagar_hasta | 0.85 | 0.50 | false | false |
| periodo | 0.80 | 0.45 | false | false |

### CEVT
| Campo | AutoAccept | NeedsReview | Sensitive | BlockOnFail |
|-------|------------|-------------|-----------|-------------|
| medidor_numero | 0.85 | 0.50 | false | false |
| periodo | 0.80 | 0.45 | false | false |
| vencimiento | 0.85 | 0.50 | false | false |
| codigo_pago_electronico | 0.88 | 0.55 | true | true |
| total_a_pagar | 0.88 | 0.55 | true | true |

## API Expuesta

### `services_config.get_service_confidence_config(service)`
Devuelve dict con configuración de confianza por campo.

### `services_config.get_field_confidence_config(cfg, section, name)`
Lee configuración de confianza para un campo desde parser ya cargado.

### `capture_pipeline._make_confidence_decision(...)`
Función interna de decisión (testeable unitaria).

### `field_reporting_processor.generate_field_report(..., field_confidence=...)`
Incluye `confidence_summary` en reporte.

## Tests
- `backend/tests/test_confidence_routing.py`: 23 tests unitarios
  - `_calc_extraction_score`: 6 tests
  - `_make_confidence_decision`: 10 tests
  - `services_config` confidence: 7 tests

## Decisiones de Diseño

1. **Pesos 0.6/0.4**: OCR más importante que extracción; ajustable en futuro via config
2. **`blocked` vs `rejected`**: `blocked` = sensible o política estricta; `rejected` = legacy compatible
3. **Defaults conservadores**: 0.85/0.50 evitan autoaceptar errores; ajustables por campo
4. **Compatibilidad hacia atrás**: claves opcionales, defaults en código, no rompe `services.ini` existentes
5. **Trazabilidad completa**: cada decisión registra inputs y thresholds usados

## Referencias
- Spec: `runs/09-confianza-y-enrutamiento-hitl/spec.md`
- Auditoría: `runs/09-confianza-y-enrutamiento-hitl/audit-1.md`
- Decisiones: `runs/09-confianza-y-enrutamiento-hitl/decision.md`
- Usuario: `docs/usuario/confianza-y-enrutamiento-hitl.md`