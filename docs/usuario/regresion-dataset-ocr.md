# Regresión Dataset OCR — Documentación de Usuario

## Propósito

Suite de regresión automática que garantiza que cambios en el pipeline OCR/extracción no degradan la precisión ya validada para cada proveedor, tipo de documento y campo.

## Uso

### Ejecutar suite de regresión (local)

```bash
# Ejecutar todos los tests de regresión
cd backend
pytest tests/test_regression_dataset.py -v

# Generar reporte JSON para CI
pytest tests/test_regression_dataset.py --json-report --json-report-file=regression-report.json
```

### Generar nuevos fixtures sintéticos

```bash
# Generar 5 fixtures para gas (proveedor configurado en services.ini)
python scripts/generate_regression_fixtures.py --provider gas --count 5 --seed 42

# Generar para todos los proveedores configurados
python scripts/generate_regression_fixtures.py --provider configured --count 3

# Bump de versión de fixtures
python scripts/generate_regression_fixtures.py --provider configured --count 5 --version 1.1.0
```

### Estructura de fixtures

```
backend/tests/fixtures/regression/
├── images/
│   ├── gas/
│   │   ├── factura_01.png
│   │   └── factura_02.png
│   └── cevt/
│       └── ...
├── expected/
│   ├── gas/
│   │   ├── factura_01.json
│   │   └── factura_02.json
│   └── cevt/
│       └── ...
└── metadata.json
```

### Expected output (ejemplo)

```json
{
  "fixtures_version": "1.0.0",
  "provider": "gas",
  "document_type": "factura",
  "document_id": "factura_01",
  "fields": {
    "importe": { "value": 33867.3, "confidence": 0.96 },
    "cliente": { "value": "98847494", "confidence": 0.85 },
    "nro_medidor": { "value": "2287", "confidence": 0.96 },
    "a_pagar_hasta": { "value": "28/07/2024", "confidence": 0.95 },
    "periodo": { "value": "02/2026", "confidence": 0.90 }
  },
  "validation": { "semantic_checks_passed": true, "warnings": [] }
}
```

### Configuración de umbrales

Editar `backend/config/regression.ini`:

```ini
[regression]
min_global_accuracy = 0.95
min_field_accuracy = 0.90

[thresholds]
gas.importe = 0.98
gas.cliente = 0.95
cevt.medidor_numero = 0.90
```

### Interpretación de resultados

- **PASS**: Todos los campos superan umbrales globales y específicos
- **FAIL**: Reporte muestra qué campos fallan y por cuánto
- **Accuracy por campo**: 1.0 = match exacto, < 1.0 = diferencia (ver `compare_values`)

### CI/CD

El workflow `.github/workflows/ci.yml` ejecuta la suite en cada push/PR:

```yaml
- name: Run OCR Regression Suite
  run: |
    cd backend
    pytest tests/test_regression_dataset.py -v --json-report --json-report-file=regression-report.json
```

El artefacto `regression-report.json` contiene:
```json
{
  "verdict": "PASS",
  "global_accuracy": 0.97,
  "by_provider": {
    "gas": { "accuracy": 0.98, "fields": {...} },
    "cevt": { "accuracy": 0.96, "fields": {...} }
  },
  "failures": []
}
```

### Agregar nuevo proveedor al gate de regresión

1. Configurar proveedor en `backend/config/services.ini` (campos, regex, etc.)
2. Agregar plantilla en `PROVIDER_TEMPLATES` de `generate_regression_fixtures.py`
3. Habilitar en `regression.ini`: `providers.nuevo_proveedor = true`
4. Generar fixtures: `python scripts/generate_regression_fixtures.py --provider nuevo_proveedor --count 5`
5. Validar expected outputs manualmente (ground truth)
6. Commitear fixtures + expected outputs + metadata.json actualizado