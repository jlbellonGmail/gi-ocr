```yaml
status: approved
attempt: 1
feedback: []
```

# QA report: 08-regresion-dataset-ocr (attempt 1)

Worktree: `D:\proyectos\worktrees\08-regresion-dataset-ocr`
Rama: `feature/08-regresion-dataset-ocr`
Commit evaluado: `418ee7e`
Entorno: `.venv` propio del worktree, Python 3.14.7, Windows 11.

## 1. Suite completa (`pytest -q backend/tests tests`)

Comando:

```
.venv/Scripts/python.exe -m pytest -q backend/tests tests \
  --basetemp="C:/Users/jlbel/AppData/Local/Temp/claude/qa08tmp_full"
```

Resultado:

```
434 passed, 8 skipped, 56 warnings in 491.75s (0:08:11)
```

**0 fallos.** Los 8 `skipped` son los ya conocidos y no relacionados con esta
feature: `test_e2e_playwright.py` (falta `playwright`), `test_api_jobs.py` y
`test_local_samples_real.py` x4 (muestras privadas gitignored ausentes),
`test_upload_security.py` x2 (permisos POSIX no aplican en Windows).

### Verificación de la afirmación del builder sobre `test_preflight_script.py`

El builder reportó 3 fallos en `tests/test_preflight_script.py` en su corrida
de la suite conjunta, y los atribuyó a contención de recursos (no a una
regresión real de esta feature), aportando como evidencia que el módulo
pasa completo en aislamiento.

Verificación independiente (no acepté la explicación sin comprobarla):

1. Corrida de la suite completa por mi cuenta (arriba): **0 fallos**, incluido
   `test_preflight_script.py` — no reproduje los 3 fallos que vio el builder.
2. Corrida de `tests/test_preflight_script.py` en aislamiento:

   ```
   .venv/Scripts/python.exe -m pytest -q tests/test_preflight_script.py \
     --basetemp="C:/Users/jlbel/AppData/Local/Temp/claude/qa08tmp_preflight"
   ```

   Resultado: `20 passed in 171.43s (0:02:51)`.

Conclusión: el módulo pasa siempre en aislamiento, y en mi corrida de la
suite conjunta pasó también junto al resto (incluida
`test_ocr_regression_dataset.py`). Que el builder haya visto 3 fallos ahí en
su propia corrida y yo no los haya reproducido corriendo la misma suite
conjunta es consistente con un problema de flakiness/contención de recursos
en el entorno local (probablemente E/S de disco o CPU compartida durante la
carga simultánea de modelos OCR y `scripts/preflight.ps1`), no con una
regresión determinística introducida por esta feature. No hay ninguna
dependencia de código entre `test_ocr_regression_dataset.py`/
`synthetic_ocr_documents.py` y `scripts/preflight.ps1`/
`tests/test_preflight_script.py`. Confirmo la afirmación del builder: no es
un problema de esta feature.

## 2. Suite nueva en aislamiento, motor OCR real

Comando:

```
.venv/Scripts/python.exe -m pytest -q backend/tests/test_ocr_regression_dataset.py \
  --basetemp="C:/Users/jlbel/AppData/Local/Temp/claude/qa08tmp1"
```

Resultado: `22 passed, 4 warnings in 9.82s` (warnings son
`DeprecationWarning` de `datetime.utcnow()` en
`field_reporting_processor.py`, preexistente, no introducido por esta
feature).

Confirmado por lectura directa del código (no solo por el nombre de los
tests) que el motor OCR es real, sin mocks ni atajos:

- `engine_warm` (fixture module-scope) llama a `ocr_engine.warmup()` /
  `ocr_engine.get_engine()` real; no hay monkeypatch de `ocr_engine` ni de
  `capture_pipeline` en el módulo.
- Cada caso llama a `capture_pipeline.process_document(str(path), name)`
  contra una imagen `.png` real guardada en `tmp_path` — el mismo pipeline
  productivo (RapidOCR/ONNX two-pass ROI, ADR-006), nunca
  `synthetic_controlled_result` de `scripts/benchmark_captura.py` (ese
  símbolo ni siquiera se importa en el módulo nuevo).

## 3. Contrato del circuito (`Assert-FeatureContract`)

Ejecutado con:

```powershell
Import-Module .\scripts\feature-contract.ps1 -Force
Assert-FeatureContract -Slug '08-regresion-dataset-ocr' -Title 'Regresion dataset OCR'
```

- Antes de escribir este `test-report-1.md`: falló únicamente con
  `"Falta al menos un test-report-N.md en runs/08-regresion-dataset-ocr."`
  — confirma que **todo el resto** del contrato (`decision.md`, docs
  técnica/usuario, enlaces exactos en ambos índices) ya estaba en orden
  antes de que yo interviniera.
- Verificado además manualmente:
  - `docs/tecnica/regresion-dataset-ocr.md`: existe, no vacío (268 líneas),
    cubre casos, fixtures, criterio de comparación, ubicación del módulo y
    la decisión de no extraer un módulo compartido para `values_match`.
  - `docs/usuario/regresion-dataset-ocr.md`: existe, no vacío (121 líneas),
    incluye ejemplo concreto de salida en verde y de un fallo con mensaje.
  - `runs/08-regresion-dataset-ocr/decision.md`: existe, no vacío (193
    líneas), decisiones demostrables (calibración de brillo con tabla de
    valores medidos, causa raíz del solapamiento de bandas ROI, evidencia
    de gate real), no ornamental.
  - `docs/tecnica/index.md:22`: `- [Regresion Dataset OCR](regresion-dataset-ocr.md)`.
  - `docs/usuario/index.md:20`: `- [Regresion Dataset OCR](regresion-dataset-ocr.md)`.

Tras agregar `test-report-1.md`, `Assert-FeatureContract` no reporta ya el
único punto pendiente (el archivo ahora existe).

## 4. Verificación contra el spec (no solo contra el reporte del builder)

Leí `backend/tests/test_ocr_regression_dataset.py` y
`backend/tests/fixtures/synthetic_ocr_documents.py` completos.

- **4 casos mínimos, todos con pipeline real** (criterio 7):
  `TestLitoralGasValidDocument`, `TestCevtValidDocument`,
  `TestLitoralGasInvalidPeriod`, `TestUnknownDocument`. Los cuatro llaman a
  `_process()` → `capture_pipeline.process_document`, sin mocks. Confirmado
  que ningún test usa `synthetic_controlled_result` (no aparece en el
  módulo).
- **5 estados de campo verificados por separado, por caso** (criterio 8):
  - `raw_ocr_text`: verificado explícitamente en cada una de las 4 clases
    (`test_raw_ocr_text_is_not_empty` / `test_raw_ocr_text_contains_the_invalid_value`).
  - `candidate_fields`: verificado en `_assert_validated_matches` (para
    casos válidos/parcialmente válidos) y explícitamente en
    `test_periodo_candidate_carries_the_invalid_value` /
    `test_no_candidate_fields_for_any_known_provider`.
  - `validated_fields`: verificado campo por campo vía
    `_assert_validated_matches` y en
    `test_no_validated_fields_for_any_known_provider`.
  - `rejected_fields`: verificado con motivo no vacío en
    `test_periodo_is_rejected_with_non_empty_reason`, y su ausencia
    verificada explícitamente en los demás casos
    (`test_no_unexpected_rejected_or_missing_fields`,
    `test_no_rejected_and_no_missing_fields`).
  - `missing_fields`: verificado explícitamente en los 4 casos
    (`test_no_unexpected_rejected_or_missing_fields`,
    `test_periodo_never_validated_nor_missing`,
    `test_no_rejected_and_no_missing_fields`).
  No hay ningún assert que compare un único diccionario combinado: cada
  estado tiene su propio assert con mensaje específico.
- **Caso "documento no reconocido" (el punto que rechazó `audit-1.md`)**:
  leí `TestUnknownDocument` con cuidado, no de oídas.
  - `test_quality_gate_does_not_reject` verifica explícitamente
    `quality_gate["verdict"] != "reject"` — confirma que el fixture
    atraviesa el quality gate y no lo esquiva.
  - `test_provider_detected_is_unknown` verifica explícitamente
    `processing_metadata["provider_detected"] == "UNKNOWN"`.
  - `test_no_candidate_fields_for_any_known_provider` y
    `test_no_validated_fields_for_any_known_provider` verifican que
    `candidate_fields`/`validated_fields` sean `{}` y que la intersección
    con los `required_fields` de `LITORAL_GAS`/`CEVT` sea vacía — sin
    campos inventados.
  - Corrida real (parte de la corrida de 22 tests arriba): estas 6
    aserciones de `TestUnknownDocument` pasan con el motor OCR real, no es
    solo código sin ejecutar.
  - `build_unknown_document_image()` (leído en
    `synthetic_ocr_documents.py`): dibuja texto plausible ("Comprobante
    Generico de Servicio", fecha, monto, referencia) sin ninguna
    subcadena de `"litoral gas"`/`"litoralgas"`/`"litoral"`/`"cevt"`/
    `"cooperativa"`/`"electri"` — verificado por inspección directa del
    texto dibujado contra la lista de `classify_keywords` citada en el
    spec.
- **Reutilización de `values_match`**: confirmado por import directo,
  `from scripts.benchmark_captura import values_match` (línea 48 del
  módulo de test), no una reimplementación. Verificado además que
  `scripts/benchmark_captura.py::values_match` (línea 272) es exactamente
  la función citada por el spec: `math.isclose(..., abs_tol=0.01)` para
  numéricos, `strip().lower()` para texto.
- **Determinismo** (criterio 10): `test_synthetic_fixtures_are_deterministic`
  compara `Image.tobytes()` de dos generaciones para las 3 fixtures; pasa
  en la corrida real.
- **No regresión sobre la suite existente** (criterio 14): confirmado en la
  corrida completa de la sección 1 (0 fallos en `backend/tests/`, incluidos
  `test_benchmark_captura.py` y `test_local_samples_real.py` sin cambios de
  comportamiento).

## 5. Evidencia de gate real (criterio 11) — reproducida por QA, no solo por el builder

No acepté la afirmación del builder sin repetirla yo mismo, en una copia de
trabajo no commiteada:

1. Alteré `backend/tests/fixtures/synthetic_ocr_documents.py`, cambiando el
   `total` esperado de `LITORAL_GAS` de `12345.67` a `99999.99` (el valor
   *esperado* del fixture, no el pipeline — para provocar una regresión
   deliberada del contrato de comparación).
2. Corrí `pytest -q backend/tests/test_ocr_regression_dataset.py::TestLitoralGasValidDocument`.
   Resultado: `1 failed, 4 passed` con mensaje claro:

   ```
   AssertionError: 'total' validado con valor inesperado: obtenido='12345.67' esperado=99999.99
   assert False
    +  where False = values_match('12345.67', 99999.99)
   ```

3. Revertí con `git checkout -- backend/tests/fixtures/synthetic_ocr_documents.py`
   (confirmado con `git status --short` sin salida, working tree limpio) y
   volví a correr la misma clase: `5 passed in 4.95s`.

El sabotaje no quedó commiteado ni como test permanente. Esta es evidencia
independiente de QA (no solo el relato del builder en `decision.md`, que
reporta la misma prueba hecha por su parte de forma consistente).

## 6. Lint

```
.venv/Scripts/python.exe -m ruff check backend/tests/test_ocr_regression_dataset.py backend/tests/fixtures/synthetic_ocr_documents.py
→ All checks passed!

.venv/Scripts/python.exe -m ruff format --check backend/tests/test_ocr_regression_dataset.py backend/tests/fixtures/synthetic_ocr_documents.py
→ 2 files already formatted
```

(Nota: `AGENTS.md` indica que el lint automatizado en CI queda pendiente
como tarea futura; se corrió igual aquí como verificación adicional de
calidad y pasó limpio.)

## 7. Tiempo de ejecución (criterio 13)

22 tests nuevos en 9.82s en aislamiento — muy por debajo del umbral de
"minutos" señalado como alerta en el spec. La suite completa (434 tests)
tomó 491.75s (~8m11s) en este entorno, dominado por el resto de
`backend/tests/` (motor OCR real en múltiples suites), no por esta feature
en particular.

## Veredicto

`approved`. Los 4 casos mínimos del spec están presentes, ejecutan el
pipeline real sin mocks/atajos, verifican los 5 estados de campo por
separado, el caso "documento no reconocido" cumple exactamente el punto
que había bloqueado `audit-1.md` (`provider_detected == "UNKNOWN"`,
`quality_gate.verdict != "reject"`, sin campos de proveedores conocidos), el
criterio de comparación reutiliza `values_match` real por import directo, el
determinismo está verificado con test propio, la suite es gate real
(reproducido independientemente por QA), no hay regresión sobre la suite
existente, y el contrato común del circuito (docs, decision, índices) está
completo. Los 3 fallos vistos por el builder en
`tests/test_preflight_script.py` no se reprodujeron en mi corrida
independiente de la suite completa y son consistentes con flakiness/
contención de recursos del entorno local, no con una regresión de esta
feature.
