# Confianza y Enrutamiento HITL — Guía de Usuario

## Propósito
Permite configurar umbrales de confianza por campo para automatizar decisiones:
- **Autoaceptar** campos con alta confianza (sin intervención humana)
- **Enviar a revisión** campos con confianza media (operador valida/corrige)
- **Bloquear** falsos positivos en campos sensibles (requiere corrección manual)

## Configuración en `services.ini`

Agregue las siguientes claves opcionales a cada campo en la sección correspondiente:

```ini
[GAS]
Title=Servicio de Gas
Fields=importe,cliente,periodo

Field.importe.Label=Importe
Field.importe.Example=$ 23.345,56
Field.importe.Type=amount
Field.importe.Required=true
Field.importe.Regex=(?:importe|total)\D{0,40}(\$?\s?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))
; --- Nuevas claves de confianza ---
Field.importe.ConfidenceAutoAccept=0.88
Field.importe.ConfidenceNeedsReview=0.55
Field.importe.Sensitive=true
Field.importe.BlockOnValidationFail=true
```

### Parámetros

| Parámetro | Valores | Default | Descripción |
|-----------|---------|---------|-------------|
| `ConfidenceAutoAccept` | 0.0 – 1.0 | 0.85 | Score mínimo para autoaceptar |
| `ConfidenceNeedsReview` | 0.0 – 1.0 | 0.50 | Score mínimo para enviar a revisión |
| `Sensitive` | `true` / `false` | `false` | Si `true`, fallo de validación bloquea el campo |
| `BlockOnValidationFail` | `true` / `false` | `true` | Si `true`, fallo de validación bloquea (vs solo rechazar) |

### Reglas
- `ConfidenceAutoAccept` debe ser **mayor** que `ConfidenceNeedsReview`
- Booleanos: solo `true` o `false` (minúsculas, sin acentos)
- Todas las claves son **opcionales**; si omitidas, usan defaults

## Flujo de Decisión Automática

Para cada campo extraído, el sistema calcula:

1. **`ocr_score`**: Confianza OCR (0.0–1.0) de la mejor caja en la banda del campo
2. **`extraction_score`**: Según cómo se extrajo el valor
   - 1.0: Regex en zona OCR (two-pass ROI)
   - 0.9: Regex en texto completo de página
   - 0.7: Solo ancla textual + fallback genérico
   - 0.3: Fallback genérico por palabra clave
3. **`final_score`**: `(ocr_score × 0.6) + (extraction_score × 0.4)`
4. **`validation_passed`**: ¿El validador semántico (fecha, monto, etc.) aprobó?

**Decisión final:**
| Validación | `final_score` | Decisión |
|------------|---------------|----------|
| ✅ Aprobada | ≥ `AutoAccept` | `auto_accepted` |
| ✅ Aprobada | ≥ `NeedsReview` | `needs_review` |
| ✅ Aprobada | < `NeedsReview` | `needs_review` |
| ❌ Fallida | — | `blocked` si `Sensitive` o `BlockOnValidationFail` |
| ❌ Fallida | — | `rejected` (legacy) si no sensible |
| Sin candidato | — | `missing` |

## Salida en API / JSON

El resultado del pipeline incluye `structured_output.field_confidence`:

```json
{
  "structured_output": {
    "candidate_fields": { "importe": "1.234,56", ... },
    "validated_fields": { "importe": "1234.56", ... },
    "rejected_fields": { },
    "missing_fields": { },
    "field_confidence": {
      "importe": {
        "ocr_score": 0.92,
        "extraction_score": 1.0,
        "final_score": 0.95,
        "validation_passed": true,
        "validation_reason": null,
        "decision": "auto_accepted",
        "thresholds": { "auto": 0.88, "review": 0.55 },
        "sensitive": true,
        "block_on_validation_fail": true
      },
      "cliente": { ... }
    }
  },
  "field_report": {
    "confidence_summary": {
      "auto_accepted": 3,
      "needs_review": 1,
      "blocked": 0,
      "missing": 1,
      "by_field": { ... }
    }
  }
}
```

## Revisión Humana (HITL)

Los campos con `decision = "needs_review"` se presentan en el frontend para revisión.

Al confirmar, el sistema registra en `confirmation_metadata`:
- `confidence_at_review`: snapshot del `field_confidence` al momento de revisión
- `decision_at_review`: estado humano (`confirmed` / `corrected` / `unresolved`)

Esto permite auditoría completa: decisión automática vs decisión humana.

## Exportación Legacy (`storage_bridge`)

Además del `.DATA` (formato plano), se genera un archivo compañero `.CONFIDENCE.json`:

```
storage_bridge/ready/
  GAS_20260825_143000.DATA
  GAS_20260825_143000.CONFIDENCE.json
```

Contenido de `.CONFIDENCE.json`:
```json
{
  "service": "GAS",
  "timestamp": "2026-08-25T14:30:00",
  "field_confidence": {
    "importe": { "decision": "auto_accepted", "final_score": 0.95, ... },
    "cliente": { "decision": "needs_review", "final_score": 0.62, ... }
  }
}
```

## Ejemplos de Configuración

### Campo Monetario Crítico (bloquear errores)
```ini
Field.total_a_pagar.ConfidenceAutoAccept=0.90
Field.total_a_pagar.ConfidenceNeedsReview=0.60
Field.total_a_pagar.Sensitive=true
Field.total_a_pagar.BlockOnValidationFail=true
```

### Campo Opcional Permisivo (revisión humana)
```ini
Field.observaciones.ConfidenceAutoAccept=0.80
Field.observaciones.ConfidenceNeedsReview=0.40
Field.observaciones.Sensitive=false
Field.observaciones.BlockOnValidationFail=false
```

### Campo Fecha Estándar
```ini
Field.vencimiento.ConfidenceAutoAccept=0.85
Field.vencimiento.ConfidenceNeedsReview=0.50
Field.vencimiento.Sensitive=false
Field.vencimiento.BlockOnValidationFail=false
```

## Buenas Prácticas

1. **Empiece conservador**: defaults (0.85/0.50) funcionan bien para la mayoría
2. **Ajuste por campo**: montos y comprobantes → umbrales altos + `Sensitive=true`
3. **Monitoree `field_report.confidence_summary`**: detecte campos que saturan revisión
4. **No declare claves innecesarias**: omita para usar defaults y mantener `services.ini` limpio
5. **Valide esquema**: ejecute `python -m backend.app.services_config` para verificar

## Validación de Esquema

```bash
python -c "from backend.app.services_config import validate_services_schema; validate_services_schema(); print('OK')"
```

Errores comunes:
- `ConfidenceAutoAccept` ≤ `ConfidenceNeedsReview` → ajuste valores
- Valores fuera de rango [0.0, 1.0] → corrija
- Booleanos no son `true`/`false` → use minúsculas exactas

## Integración con Frontend

El endpoint `/api/v1/jobs/{job_id}/review` incluye `field_confidence` en la respuesta. El frontend debe:
1. Mostrar `decision` y `final_score` junto a cada campo
2. Pre-seleccionar campos `needs_review` para edición
3. Permitir override humano (cambiar valor, marcar `confirmed`/`corrected`)
4. Enviar correcciones con `state` y `final_value` a `/api/v1/jobs/{job_id}/confirm`

## Solución de Problemas

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| Muchos campos en `needs_review` | Umbrales muy altos | Baje `ConfidenceAutoAccept` o suba `ConfidenceNeedsReview` |
| Campos sensibles bloqueados correctamente | `Sensitive=true` + validación falla | Corrija regex/validador o baje umbrales |
| Campo `missing` pero visible en imagen | OCR no detectó / banda mal configurada | Ajuste `zones` o `band` en template |
| Error validación `services.ini` | Sintaxis incorrecta | Use `true`/`false` exactos, floats con punto decimal |

## Referencias Técnicas
- Documentación técnica: `docs/tecnica/confianza-y-enrutamiento-hitl.md`
- Spec: `runs/09-confianza-y-enrutamiento-hitl/spec.md`
- Tests: `backend/tests/test_confidence_routing.py`