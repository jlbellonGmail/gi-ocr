# Test Report: 08-regresion-dataset-ocr — Suite de regresión OCR/extracción

## Resumen

- **Total tests**: 33
- **Passed**: 33
- **Failed**: 0
- **Duration**: 32.77s
- **Exit code**: 0

## Tests ejecutados

| Test | Provider | Document | Resultado |
|------|----------|----------|-----------|
| test_regression_field_accuracy[0] | gas | factura_01 | PASSED |
| test_regression_field_accuracy[1] | gas | factura_02 | PASSED |
| test_regression_field_accuracy[2] | gas | factura_03 | PASSED |
| test_regression_field_accuracy[3] | gas | factura_04 | PASSED |
| test_regression_field_accuracy[4] | cevt | factura_01 | PASSED |
| test_regression_field_accuracy[5] | cevt | factura_02 | PASSED |
| test_regression_field_accuracy[6] | cevt | factura_03 | PASSED |
| test_regression_field_accuracy[7] | cevt | factura_04 | PASSED |
| test_regression_field_accuracy[8] | gas | factura_05 | PASSED |
| test_regression_field_accuracy[9] | gas | factura_06 | PASSED |
| test_regression_field_accuracy[10] | cevt | factura_05 | PASSED |
| test_regression_field_accuracy[11] | cevt | factura_06 | PASSED |
| test_regression_field_accuracy[12] | gas | factura_07 | PASSED |
| test_regression_field_accuracy[13] | gas | factura_08 | PASSED |
| test_regression_field_accuracy[14] | cevt | factura_07 | PASSED |
| test_regression_field_accuracy[15] | cevt | factura_08 | PASSED |
| test_regression_field_accuracy[16] | gas | factura_09 | PASSED |
| test_regression_field_accuracy[17] | gas | factura_10 | PASSED |
| test_regression_field_accuracy[18] | cevt | factura_09 | PASSED |
| test_regression_field_accuracy[19] | cevt | factura_10 | PASSED |
| test_regression_field_accuracy[20] | gas | factura_11 | PASSED |
| test_regression_field_accuracy[21] | gas | factura_12 | PASSED |
| test_regression_field_accuracy[22] | cevt | factura_11 | PASSED |
| test_regression_field_accuracy[23] | cevt | factura_12 | PASSED |
| test_regression_field_accuracy[24] | gas | factura_13 | PASSED |
| test_regression_field_accuracy[25] | gas | factura_14 | PASSED |
| test_regression_field_accuracy[26] | cevt | factura_13 | PASSED |
| test_regression_field_accuracy[27] | cevt | factura_14 | PASSED |
| test_regression_field_accuracy[28] | gas | factura_15 | PASSED |
| test_regression_field_accuracy[29] | gas | factura_16 | PASSED |
| test_fixtures_version_consistency | - | - | PASSED |
| test_all_providers_have_fixtures | - | - | PASSED |
| test_expected_outputs_structure | - | - | PASSED |

## Cobertura

- **Proveedores testeados**: GAS, CEVT (configurados en services.ini)
- **Campos validados**: importe, cliente, nro_medidor, a_pagar_hasta, periodo (GAS); medidor_numero, periodo, vencimiento, codigo_pago_electronico, total_a_pagar (CEVT)
- **Fixtures version**: 1.0.0 (consistente en metadata y expected outputs)

## Verificaciones adicionales

- ✅ Versión de fixtures consistente entre metadata y expected outputs
- ✅ Todos los proveedores habilitados en regression.ini tienen fixtures
- ✅ Estructura de expected outputs válida (campos requeridos, confidence en rango)

## Artefactos generados

- `regression-report.json` (reporte JSON completo)
- `regression-report.json` incluye accuracy por campo y veredicto global PASS

## Conclusión

La suite de regresión pasa completamente. El gate de regresión está operativo para detectar degradaciones de precisión en el pipeline OCR/extracción.