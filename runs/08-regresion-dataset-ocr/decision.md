# Decision: 08-regresion-dataset-ocr — Suite permanente de regresión OCR/extracción

## Estado

MERGE aprobado por evidencias del circuito agéntico.

## Evidencias revisadas

- `runs/08-regresion-dataset-ocr/spec.md`
- `runs/08-regresion-dataset-ocr/audit-1.md`
- `runs/08-regresion-dataset-ocr/test-report-1.md`

## Decisiones demostrables

- **Fixtures sintéticos determinísticos**: Generados por `scripts/generate_regression_fixtures.py` con seed configurable, ruido controlado, rotación y DPI variables. No usan imágenes reales de comprobantes (cumple reglas de dominio OCR).
- **Campos desde services.ini**: Los expected outputs usan exactamente los nombres de campo que produce el motor de extracción (GAS: importe, cliente, nro_medidor, a_pagar_hasta, periodo; CEVT: medidor_numero, periodo, vencimiento, codigo_pago_electronico, total_a_pagar). Fuente única de verdad respetada.
- **Validación semántica replicada**: La suite aplica la misma normalización que el pipeline real (validators.py: amounts, dates, CUITs, períodos) para comparar valores ya validados, no texto bruto OCR.
- **Mock OCR para CI rápido**: Modo mock genera texto determinístico desde expected outputs, coincidiendo con patrones regex de services.ini. Permite CI sin descargar modelos ONNX.
- **Umbrales configurables**: `backend/config/regression.ini` define umbrales globales (0.95), por campo (0.90) y overrides por proveedor/campo (ej. gas.importe=0.98).
- **Versionado de fixtures**: `fixtures_version` en metadata.json y cada expected output previene roturas silenciosas al regenerar fixtures.
- **Solo proveedores configurados**: El test filtra automáticamente proveedores no presentes en services.ini via `regression.ini [providers]`.
- **Integración sin HTTP**: Reutiliza `extract_service_fields`, `validate_semantic` vía import directo, sin pasar por API.
- **Reporte CI**: Genera `regression-report.json` con verdict PASS/FAIL, accuracy global y por proveedor, diff campo a campo.

## Resultado

La feature queda apta para integrarse/cerrarse cuando GitHub confirme merge contra `develop` y el cierre automático marque `ROADMAP.md`.