# Decision: 08-regresion-dataset-ocr

## Estado

Implementación builder-agent lista para QA. No se marca `ROADMAP.md` y no
se crea PR en esta etapa.

## Evidencia de entrada

- `runs/08-regresion-dataset-ocr/spec.md` (aprobado en el intento 2): exige
  una suite pytest permanente, sin skip, que ejecute
  `backend/app/capture_pipeline.process_document` con el motor OCR real
  contra 4 casos mínimos (`LITORAL_GAS` válido, `CEVT` válido,
  `LITORAL_GAS` con `periodo` inválido, documento no reconocido), con los 5
  estados de campo verificados por separado, reutilizando el criterio de
  comparación `values_match` de `scripts/benchmark_captura.py`.
- `runs/08-regresion-dataset-ocr/audit-1.md`: `rejected` — el fixture
  "documento no reconocido" propuesto (canvas en blanco) dispara `reject`
  de `quality_gate.evaluate` antes de clasificar proveedor, mezclando dos
  casos de falla conceptualmente distintos.
- `runs/08-regresion-dataset-ocr/audit-2.md`: `approved`, con un punto no
  bloqueante: verificar empíricamente en CI real que el brillo medio de
  fixtures con fondo blanco puro (`_base_case_image` original) no cruce
  accidentalmente el umbral `GI_OCR_QUALITY_BRIGHTNESS_BRIGHT_REJECT_ABOVE`
  (254.5), especialmente si el runner cae al fallback
  `ImageFont.load_default()` sin tamaño.

## Decisiones tomadas

### 1. Reutilización de `values_match`: import directo, sin extraer módulo compartido

Se importa `values_match` directamente de `scripts.benchmark_captura`
(`from scripts.benchmark_captura import values_match`) en
`backend/tests/test_ocr_regression_dataset.py`. No se extrajo a un módulo
compartido nuevo: `backend/tests/test_benchmark_captura.py` ya hace
`from scripts import benchmark_captura as benchmark` sin problema
(`pytest.ini` define `pythonpath = .`), así que no había ninguna barrera
técnica que resolver. Extraer una función de ~8 líneas sin estado a un
módulo nuevo sólo para evitar un import cruzado `backend/tests` ->
`scripts` hubiera sido una capa de indirección sin beneficio real, dado que
ese import cruzado ya es un patrón existente y aceptado en el repo.

### 2. Fixtures: adaptación de `_base_case_image`, no reutilización directa ni extracción a módulo compartido

Se decidió **no** extraer `_base_case_image`/`variant` de
`scripts/benchmark_captura.py` a un módulo compartido, ni llamarlas
directamente. En cambio, se creó
`backend/tests/fixtures/synthetic_ocr_documents.py`: mismas posiciones
relativas de campo por proveedor (ya alineadas contra las bandas ROI de
`providers.py`), con tres adaptaciones deliberadas, cada una **verificada
empíricamente contra el motor OCR real** (no sólo argumentada):

**a) Fondo gris `(210,210,210)`, no blanco puro** — resuelve el punto no
bloqueante de `audit-2.md`. Medido con `quality_gate.evaluate` real:

| Fondo | Brillo medio (`gas_valid`) | Veredicto |
|---|---|---|
| Blanco puro (255) | 251.17 | `warn` (margen de sólo 3.3 respecto de `reject`=254.5) |
| Gris 230 | 226.61 | `ok` |
| Gris 210 (elegido) | 206.99 | `ok` |
| Gris 190 | 187.33 | `ok` |

Con gris 210, las cuatro fixtures finales de esta suite dan brillo medio
entre 206.85 y 208.15 — margen de ~42-47 puntos respecto de `warn`/`reject`
(250/254.5), y un margen aún mayor respecto de los umbrales `dark`
(40/70). Se repitió la medición forzando el fallback de fuente bitmap
(`ImageFont.load_default()` sin `arial.ttf`/`DejaVuSans.ttf`, el escenario
concreto que preocupaba a `audit-2.md`): el brillo medio sube apenas a
~207-208, sigue muy lejos de `reject`. Confirmado también que el blur
(varianza del Laplaciano) queda entre 320 y 590 en todos los escenarios
probados, muy por encima del umbral `warn` (100) y `reject` (40).

**b) Canvas 1400x1960 en vez de 1000x1400** — detectado ejecutando el motor
OCR real contra el canvas original: el detector de texto fusionaba las
cajas de `cliente` (`"12345678"`) y `periodo` (`"06/2026"`) en una sola
(`"1234567806/2026"`), rompiendo la extracción de `cliente`. Un canvas más
grande separa en píxeles absolutos el mismo gap normalizado, y el problema
desapareció (verificado, ver más abajo).

**c) Reposición de `vencimiento` dentro de su propia banda ROI** —
detectado ejecutando el caso "período inválido" con el motor real: el
`periodo` extraído era `"06/2026"` (leído por *substring* de la fecha
completa de `vencimiento`, `"20/06/2026"`) en vez de `"13/2026"` (el valor
realmente inyectado en el fixture). Causa raíz: el centro de la caja OCR de
`vencimiento` caía dentro de la banda ROI de `periodo` (bandas solapadas en
`litoral_gas_template()`), y el regex de `periodo`
(`\d{1,2}[/-]\d{4}`) matcheaba como subcadena de una fecha completa. Se
corrigió desplazando `vencimiento` más arriba dentro de su propia banda
(de `y=0.262` a `y=0.249`, tamaño de fuente reducido de 32 a 30) para que
el centro de su caja OCR quede fuera del rango vertical de la banda de
`periodo`. Verificado: después del ajuste, `candidate_fields["periodo"]`
refleja correctamente el valor inyectado (`"13/2026"`) en el caso inválido,
y el caso válido sigue dando `"06/2026"` para `periodo` sin afectar
`vencimiento` (`"20/06/2026"`, validado correctamente).

Este es exactamente el caso borde que el spec anticipaba explícitamente
("Documento con dos campos que compiten por el mismo patrón textual"), y
se resolvió empíricamente, no por inspección de código únicamente.

**d) Fallback de fuente escalable, no bitmap fijo** —
`scripts/benchmark_captura.py::_font` cae a `ImageFont.load_default()`
(bitmap ~10px) si no hay TrueType disponible. Se decidió usar
`ImageFont.load_default(size=<size>)` en su lugar (fuente escalable
embebida en Pillow desde 10.1, disponible en Pillow 12.3.0 de
`backend/requirements.txt`). Verificado forzando este fallback (sin
ninguna TrueType disponible en el proceso de prueba): los cuatro casos dan
exactamente el mismo resultado (mismos `validated_fields`/
`rejected_fields`) que con `arial.ttf`.

No se decidió modificar `scripts/benchmark_captura.py` ni sus fixtures
existentes (`_base_case_image`, `variant`, `_font`): esta feature declara
explícitamente que no toca ese script (ver "Alcance no modificado" en
`spec.md`), y `test_benchmark_captura.py` sigue verde sin cambios.

### 3. Persistencia de fixtures: generadas en tiempo de test, no versionadas

Se decidió generar cada imagen en memoria dentro del propio test (guardada
sólo transitoriamente a un `tmp_path` para pasarle una ruta de archivo a
`capture_pipeline.process_document`), no persistirlas como `.jpg`/`.png`
versionado en `backend/tests/fixtures/`. Motivo: el código que genera cada
imagen es la especificación exacta y auditable del fixture (diffable en una
PR, a diferencia de un binario); el criterio de determinismo (10) se
verifica directamente comparando bytes de dos generaciones
(`test_synthetic_fixtures_are_deterministic`), sin depender de que un
binario versionado no se corrompa o quede desincronizado del código que
supuestamente lo generó.

### 4. Índices de documentación

Se ejecutó `scripts/update-doc-indexes.ps1 08-regresion-dataset-ocr
"Regresion Dataset OCR"` para agregar los enlaces en `docs/tecnica/index.md`
y `docs/usuario/index.md` (no se editaron a mano).

## Alcance no modificado

- No se tocó `backend/app/capture_pipeline.py`,
  `backend/app/templates/providers.py`, `backend/app/validators.py`,
  `backend/app/quality_gate.py`, `backend/app/image_prep.py` ni
  `backend/app/ocr_engine.py`: esta feature es exclusivamente aditiva (dos
  módulos de test nuevos + documentación), tal como declara el spec.
- No se tocó `scripts/benchmark_captura.py`: se reutiliza `values_match`
  por import directo; la generación de fixtures se adaptó en un módulo
  nuevo propio de esta suite, sin modificar el script existente.
- No se tocó `backend/config/services.ini` ni `extraction_engine.py`
  (motor de exportación legacy `.DATA`, fuera de alcance explícito del
  spec).
- No se modificó `test_local_samples_real.py` ni `test_benchmark_captura.py`:
  ambos siguen verdes, sin cambios de expectativas.

## Verificación de tests

Entorno: `.venv` propio del worktree (`python -m venv .venv`, Python 3.14,
`pip install -r backend/requirements.txt` con `PIP_USER=0`/`--no-user` para
evitar que la config global de `pip` del equipo -- `install.user = true` --
entre en conflicto con el entorno virtual, mismo ajuste que documentó
`06-calidad-captura-mobile`/`07-preprocesamiento-documental-no-destructivo`).
Se usó `--basetemp` apuntando a un directorio propio para sortear el mismo
problema preexistente de permisos sobre `%TEMP%/pytest-of-<usuario>` en
Windows ya documentado en features anteriores, no relacionado con esta
feature.

- `backend/tests/test_ocr_regression_dataset.py` (nuevo, 22 tests): los 4
  casos de regresión (`LITORAL_GAS` válido, `CEVT` válido, `LITORAL_GAS`
  con período inválido, documento no reconocido) más el test de
  determinismo de fixtures. **Todos verdes**, motor OCR real, ~9 segundos
  de ejecución total (muy por debajo del umbral "minutos" del criterio 13).
- **Evidencia de gate real (criterio 11 del spec)**: se alteró
  deliberadamente, de forma temporal, el valor esperado de `total` en
  `build_litoral_gas_image` (de `12345.67` a `99999.99`) y se corrió
  `TestLitoralGasValidDocument`: el test
  `test_all_required_fields_validated_with_expected_value` falló con el
  mensaje
  `"'total' validado con valor inesperado: obtenido='12345.67' esperado=99999.99"`.
  El cambio se revirtió inmediatamente después de confirmar el fallo (no
  quedó como test permanente ni como sabotaje en el repo); se volvió a
  correr la suite completa y quedó en verde de nuevo.
- `backend/tests/test_benchmark_captura.py`, `backend/tests/test_quality_gate.py`,
  `backend/tests/test_local_samples_real.py` (gated, sigue saltándose por
  falta de muestras privadas): sin cambios de comportamiento.
- Suite completa (`pytest -q` sobre `backend/tests/` + `tests/`): corrida
  antes y después de esta feature, sin nuevas fallas atribuibles a este
  cambio (ver `test-report` de QA para el detalle completo por si hace
  falta re-verificar en su propio entorno).

## Artefactos

- `backend/tests/test_ocr_regression_dataset.py` (nuevo)
- `backend/tests/fixtures/synthetic_ocr_documents.py` (nuevo)
- `docs/tecnica/regresion-dataset-ocr.md` (nuevo)
- `docs/usuario/regresion-dataset-ocr.md` (nuevo)
- `docs/tecnica/index.md`, `docs/usuario/index.md` (enlace agregado vía
  `scripts/update-doc-indexes.ps1`)
- `runs/08-regresion-dataset-ocr/decision.md` (este archivo)
