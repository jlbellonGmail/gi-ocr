# Decision: 02-mejora-precision-ocr

## Estado

Implementacion builder-agent lista para QA. No se marca `ROADMAP.md` y no se
crea PR en esta etapa.

## Evidencia De Entrada

- `runs/02-mejora-precision-ocr/spec.md`: exige benchmark por lote, proveedor y
  campo, JSON estructurado, resumen Markdown, dataset privado opcional,
  sintetico/controlado sin datos sensibles y tests sin muestras privadas.
- `runs/02-mejora-precision-ocr/audit-1.md`: aprobado por reviewer-agent.

## Decisiones Tomadas

- Se reemplazo `scripts/benchmark_captura.py` por un benchmark unico con
  `--docs`, `--dataset`, `--out` y `--report-md`.
- Se mantuvo RapidOCR/ONNX como motor principal para el procesamiento real del
  pipeline. No se cambio ADR-006.
- Se agrego dataset sintetico/controlado generado localmente en `_bench/`, sin
  datos sensibles y sin depender de muestras privadas. Por defecto corre en modo
  `controlled` para CI sin RapidOCR; `--synthetic-mode ocr` procesa esas imagenes
  con el pipeline real cuando el motor esta disponible.
- Se preservo soporte para muestras privadas locales en
  `backend/tests/fixtures/_local_samples/real/expected.local.json`, siempre
  opcionales y gitignored.
- Se agregaron funciones testeables para evaluar resultados, agregar metricas y
  renderizar Markdown sin invocar OCR real.
- Se registro falso positivo evitado cuando un candidato queda rechazado o no
  llega a campo validado por validacion semantica o contrato esperado.
- La medicion de memoria usa `psutil` si existe y fallback de plataforma si no.

## Alcance No Modificado

- No se agregaron proveedores.
- No se crearon extractores Python por proveedor fuera del modelo vigente.
- No se hardcodearon valores privados.
- No se modifico la salida legacy `.DATA` ni `storage_bridge/`.

## Artefactos

- `scripts/benchmark_captura.py`
- `backend/tests/test_benchmark_captura.py`
- `docs/tecnica/mejora-precision-ocr.md`
- `docs/usuario/mejora-precision-ocr.md`
- `runs/02-mejora-precision-ocr/decision.md`
