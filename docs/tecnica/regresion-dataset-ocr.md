# Regresión Dataset OCR — Documentación Técnica

## Algoritmo

La suite de regresión OCR valida que cambios en el pipeline (RapidOCR PP-OCRv3, extracción de campos, validación semántica) no degraden la precisión ya validada por proveedor, tipo de documento y campo.

### Componentes

1. **Generador de fixtures sintéticos** (`scripts/generate_regression_fixtures.py`)
   - Renderiza plantillas base con texto variable usando Pillow
   - Aplica ruido gaussiano, rotación leve, DPI variable
   - Genera imágenes PNG determinísticas (seed configurable)
   - Lee campos por proveedor desde `services.ini` (fuente única de verdad)

2. **Expected outputs versionados** (`backend/tests/fixtures/regression/expected/`)
   - Un JSON por fixture con valores normalizados (formato validador)
   - Incluye `fixtures_version` para trazabilidad
   - Estructura: `{provider}/{document_id}.json`

3. **Suite pytest** (`backend/tests/test_regression_dataset.py`)
   - Descubre casos: imagen + expected output
   - Ejecuta pipeline completo: OCR → Extracción → Validación
   - Compara campo a campo con métricas de accuracy
   - Umbrales globales y por campo/proveedor desde `regression.ini`

4. **Configuración** (`backend/config/regression.ini`)
   - `min_global_accuracy`: umbral global (default 0.95)
   - `min_field_accuracy`: umbral por campo (default 0.90)
   - `thresholds.{provider}.{field}`: overrides específicos
   - `providers.{provider}`: habilita/deshabilita proveedores

5. **Reporte CI** (`regression-report.json`)
   - Verdict PASS/FAIL
   - Accuracy global y por proveedor
   - Diff campo a campo para failures

### Flujo de datos

```
Fixtures sintéticos (PNG)
    ↓
Mock OCR / RapidOCR real (texto)
    ↓
extract_service_fields (extracción por regex de services.ini)
    ↓
validate_semantic (normalización: amounts, dates, CUITs, etc.)
    ↓
compare_fields (accuracy por campo)
    ↓
Assert umbrales → PASS/FAIL
```

### Casos borde manejados

- **Formatos de fecha**: normalización YYYY/MM/DD → DD/MM/YYYY (validator output)
- **Períodos**: normalización YYYY/MM → MM/YYYY
- **Montos AR**: parsing tolerante a confusiones OCR (punto/coma)
- **CUITs**: solo dígitos y guiones
- **Código pago electrónico**: regex captura solo parte alfanumérica final
- **Versiones de fixtures**: mismatch detectado y falla el test

### Decisiones de diseño

1. **Mock OCR para tests rápidos**: El modo mock genera texto determinístico desde expected outputs, coincidiendo con patrones regex de `services.ini`. Permite CI rápido sin descargar modelos ONNX.

2. **Campos desde services.ini**: Los expected outputs usan exactamente los nombres de campo que produce el motor de extracción, evitando desalineación.

3. **Validación semántica en suite**: Replica la normalización del pipeline real (validators.py) para comparar valores ya normalizados, no texto bruto OCR.

4. **Umbrales por proveedor/campo**: Permite ajustar sensibilidad donde la precisión histórica varía (ej. `gas.importe` más estricto).

5. **Versionado de fixtures**: `fixtures_version` en metadata y cada expected output previene roturas silenciosas al regenerar fixtures.

### Integración con evaluate_ocr_service.py

La suite reutiliza la lógica de extracción y validación del evaluador existente vía import directo (`from backend.app.extraction_engine import extract_service_fields`), sin pasar por HTTP.

### Mantenimiento

- **Agregar casos**: `python scripts/generate_regression_fixtures.py --provider gas --count 5`
- **Actualizar umbrales**: Editar `backend/config/regression.ini`
- **Regenerar fixtures**: Bump version, regenerar expected outputs, validar manualmente
- **Solo proveedores en services.ini**: El test filtra automáticamente proveedores no configurados