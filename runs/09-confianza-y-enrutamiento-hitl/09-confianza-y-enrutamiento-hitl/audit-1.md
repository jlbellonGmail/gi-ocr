status: approved
attempt: 1
feedback:
  - El spec incluye correctamente los 4 criterios de documentación obligatorios (docs/tecnica, docs/usuario, decision.md, enlaces en índices)
  - La lógica de decisión en líneas 63-64 es redundante: ambas condiciones llevan a `needs_review`. Unificar en `ConfidenceNeedsReview <= final_score < ConfidenceAutoAccept`
  - El `extraction_score` (línea 58) necesita definición precisa por camino de extracción: zone regex (1.0), field regex (0.9), patterns legacy (0.7), anchor-only (0.5), genérico (0.3)
  - Faltan detalles sobre interacción con `rejected_fields` actual: ¿un campo `blocked` va a `rejected_fields` o a nueva estructura? Especificar en spec.
  - Verificar que `field_confidence` se incluya también para campos `missing` y `blocked` (trazabilidad completa)
  - En `services_config.py`, la validación de `ConfidenceAutoAccept > ConfidenceNeedsReview` debe ser warning no error si uno no está declarado (usar defaults)