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

## Fix post-CI: separación `cliente`/`periodo` en `build_litoral_gas_image`

CI (`.github/workflows/ci.yml`, `ubuntu-latest`, Python 3.12.14, PR #14,
[run 32574915254](https://github.com/jlbellonGmail/gi-ocr/actions/runs/32574915254/job/97035712131))
falló con 5 tests rojos, todos sobre `periodo` en `LITORAL_GAS` (los 22
tests pasaban en Windows local, Python 3.14). Diagnóstico con evidencia
real (no supuesto), reproducido con un entorno Linux equivalente (WSL
Ubuntu 22.04, Python 3.12.12, mismas versiones exactas de
`backend/requirements.txt` relevantes para OCR/imagen que usa CI):

### Causa raíz real (verificada, no la hipótesis inicial de fuente faltante)

La hipótesis inicial razonable era la fuente TrueType faltante
(`arial.ttf`/`DejaVuSans.ttf` ausentes en el runner, cayendo a
`ImageFont.load_default(size=...)`). **Se descartó con evidencia**: el
runner Linux de prueba (WSL Ubuntu 22.04) sí tiene `DejaVuSans.ttf`
instalada (`fonts-dejavu-core`, típico también en runners `ubuntu-latest`
de GitHub Actions), y comparando `PIL.ImageDraw.textbbox` de
`arial.ttf` (Windows) vs `DejaVuSans.ttf` (Linux) vs el fallback
`ImageFont.load_default(size=...)`, el bounding box de `periodo` variaba
apenas unos pocos píxeles entre los tres — no alcanza para explicar un
campo que pasa de extraerse siempre a no extraerse nunca.

La causa raíz real: `capture_pipeline.process_document` corre
`image_prep.prepare` (feature `07-preprocesamiento-documental-no-
destructivo`) **antes** de OCR, que incluye `normalize_scale` -- en este
fixture concreto reescala el canvas de 1400x1960 a 1142x1600 (factor
~0.8163). Con la posición original de `periodo` (fuente 32, x=0.80), el
hueco horizontal entre el texto de `cliente` (`"12345678"`, banda
x:0.66-0.82) y el de `periodo` (banda x:0.78-0.90, banda adyacente/con
solape parcial x:0.78-0.82) era de sólo ~44-52px **antes** del
reescalado; después del reescalado de `normalize_scale` ese hueco se
angosta aún más (~36px). A esa distancia, el detector de texto
(RapidOCR/DBNet, `ocr_engine.detect_page`) fusiona ambas cajas en una
sola detección: `"12345678 06/2026"`, cuyo centro (`cx≈0.777`) cae **sólo**
dentro de la banda de `cliente` (x hasta 0.82) y **no** dentro de la de
`periodo` (x desde 0.78) -- confirmado imprimiendo `box_results` real
(texto, score, bbox normalizado) en el entorno Linux de reproducción, con
y sin `image_prep.prepare` de por medio:

- **Sin** `image_prep.prepare` (llamando `capture_pipeline.process_image`
  directo sobre el canvas 1400x1960 sin reescalar): `periodo` se detecta
  como caja propia (`"06/2026"`, centro `(0.8464, 0.2883)`, dentro de su
  banda) — el pipeline extrae y valida `periodo` correctamente.
- **Con** `image_prep.prepare` (el camino real de
  `capture_pipeline.process_document`, el que ejercita el test): las cajas
  de `cliente` y `periodo` se fusionan en una sola (`"12345678 06/2026"`,
  centro `(0.7771, 0.2894)`), que sólo cae en la banda de `cliente`.
  `cliente` sigue validando bien (su regex `\d{8,10}` matchea
  `"12345678"` igual dentro del texto fusionado), pero `periodo` termina
  sin ninguna caja en su banda: `candidate_fields["periodo"] = None`,
  reportado en `missing_fields`, nunca llega a `rejected_fields` ni a
  `validated_fields`. Exactamente el síntoma de los 5 tests rojos de CI.

Por qué no se veía en Windows/Python 3.14 local: el margen de ~44-52px
(antes del reescalado) evidentemente queda, en ese entorno concreto
(fuente `arial.ttf`, motor RapidOCR/ONNX Runtime sobre la misma versión
fijada, pero con diferencias de bajo nivel de rendering/inferencia entre
plataformas — antialiasing de FreeType empaquetado en el wheel de Pillow
por plataforma, y/o sensibilidad numérica del post-procesamiento de DBNet)
justo del lado seguro de la fusión; en Linux (CI real y la reproducción
local de este fix) queda del lado que fusiona. Es una condición de
carrera geométrica real entre bandas ROI adyacentes con muy poco margen,
no un problema exclusivo de fuente -- la hipótesis de la fuente en el
docstring original de `synthetic_ocr_documents.py` señalaba la clase
correcta de riesgo (dependencia de renderizado entre plataformas) pero no
el mecanismo exacto.

### Fix aplicado

`backend/tests/fixtures/synthetic_ocr_documents.py::build_litoral_gas_image`:
`periodo` se dibuja con fuente más chica (22 en vez de 32) y desplazado a
la derecha dentro de su propia banda ROI (`x=0.85, y=0.283` en vez de
`x=0.80, y=0.278`). No se tocó `cliente` (sigue en `x=0.66, y=0.280,
size=32`, ya funcionaba bien) ni ninguna banda ROI de
`backend/app/templates/providers.py` (fuera de alcance: esas bandas son
configuración de producción, no del fixture de test).

Con esta posición, el hueco horizontal entre el texto de `cliente` y el
de `periodo` (medido con `PIL.ImageDraw.textbbox`, fuente `DejaVuSans.ttf`,
la misma que usa el runner Linux) pasa de ~44px a ~103px -- más del doble,
calibrado mediante una búsqueda exhaustiva de combinaciones
tamaño/posición que maximiza esa separación sin sacar el centro de la caja
de la banda ROI de `periodo` (con margen de seguridad de al menos 0.01 en
normalizado, ~14px en Y / ~14px en X, respecto de cada borde de banda) ni
para el valor válido (`"06/2026"`) ni para el inválido (`"13/2026"`). No se
modificó `vencimiento` (su separación respecto de `periodo`, ya calibrada
en la ronda anterior, queda con ~40px de margen vertical, sin cambios).

### Verificación empírica del fix (evidencia, no sólo argumento)

1. **Reproducción real del bug** en un entorno Linux equivalente a CI: WSL
   Ubuntu 22.04.5 LTS, intérprete standalone CPython 3.12.12
   (`astral-sh/python-build-standalone`, misma versión menor que la
   3.12.14 del runner de CI), mismas versiones exactas de
   `backend/requirements.txt` relevantes para esta suite (`Pillow==12.3.0`,
   `numpy==2.5.2`, `opencv-python-headless==5.0.0.93`,
   `rapidocr-onnxruntime==1.2.3`, `onnxruntime==1.28.0`,
   `pypdfium2==5.13.0`, `pytest==9.1.1`, `fastapi==0.141.1`,
   `pydantic==2.13.4`, `pydantic-settings==2.15.0`, `httpx==0.28.1`,
   `python-multipart==0.0.32`). Con el fixture **sin** el fix: los mismos 5
   tests que falló CI fallan también ahí, con el mismo síntoma
   (`periodo` en `missing_fields`, nunca candidato). Confirma que la causa
   es real y reproducible fuera de GitHub Actions, no un artefacto
   específico del runner de GitHub.
2. **Con el fix aplicado**, en ese mismo entorno Linux de reproducción:
   `pytest backend/tests/test_ocr_regression_dataset.py -v` -> **22
   passed**, corrido 3 veces consecutivas sin flakiness
   (~6 segundos cada corrida).
3. **En Windows local** (`.venv`, Python 3.14, entorno original de la
   feature): `pytest backend/tests/test_ocr_regression_dataset.py -v` ->
   **22 passed** (sin regresión sobre el entorno donde ya pasaba).
4. **Suite completa** (`pytest -q` sobre `backend/tests/` + `tests/`),
   corrida en ambos entornos después del fix:
   - Windows local (`.venv`, Python 3.14): **434 passed, 8 skipped** (0
     fallas), 513s. Los `skipped` son los ya esperados en este entorno
     (muestras privadas locales ausentes, `playwright` no instalado,
     permisos POSIX no aplicables en Windows) -- ninguno nuevo ni
     relacionado con este fix.
   - Entorno Linux de reproducción (WSL Ubuntu 22.04, Python 3.12.12),
     sólo `backend/tests/` (equivalente al alcance de esta feature; `tests/`
     son los del circuito agéntico, no del producto OCR): **385 passed, 5
     skipped** (0 fallas), 143s. Los `skipped` son las mismas muestras
     privadas locales ausentes (gitignored), esperado en cualquier
     checkout limpio.
   - Ninguna falla nueva atribuible a este fix en ninguno de los dos
     entornos; los `PytestUnraisableExceptionWarning` sobre
     `JobQueue._worker`/`Event loop is closed` en ambos entornos son
     preexistentes (limpieza de un worker asyncio al cerrar el event loop
     de test), no relacionados con `synthetic_ocr_documents.py` ni con
     este fix -- no se investigan ni se corrigen aquí (fuera de alcance de
     esta feature).

No se pudo ejecutar el job exacto de GitHub Actions localmente (no hay
`act`/Docker Desktop funcional disponible en este entorno), pero la
reproducción en WSL Ubuntu con las mismas versiones fijadas de
dependencias relevantes, mismo Python 3.12.x, y el mismo síntoma exacto
(5 tests, mismos nombres, mismo mensaje de assert) es la evidencia más
fuerte disponible sin acceso directo al runner de GitHub.

### Alcance del fix

- Sólo se modificó `backend/tests/fixtures/synthetic_ocr_documents.py`
  (posición/tamaño de `periodo` en `build_litoral_gas_image`) y su
  docstring. No se tocó `backend/tests/test_ocr_regression_dataset.py`
  (los asserts y expectativas de valor no cambiaron), ni
  `backend/app/templates/providers.py`, ni `backend/app/image_prep.py`,
  ni `backend/app/capture_pipeline.py`, ni `backend/app/ocr_engine.py`.
- No se marcó `ROADMAP.md` (sigue en `READY_FOR_PR`), no se creó una PR
  nueva (se reutiliza la PR #14 existente), no se hizo `git commit
  --amend` (commit nuevo sobre la misma rama).

## Artefactos

- `backend/tests/test_ocr_regression_dataset.py` (nuevo)
- `backend/tests/fixtures/synthetic_ocr_documents.py` (nuevo)
- `docs/tecnica/regresion-dataset-ocr.md` (nuevo)
- `docs/usuario/regresion-dataset-ocr.md` (nuevo)
- `docs/tecnica/index.md`, `docs/usuario/index.md` (enlace agregado vía
  `scripts/update-doc-indexes.ps1`)
- `runs/08-regresion-dataset-ocr/decision.md` (este archivo)
