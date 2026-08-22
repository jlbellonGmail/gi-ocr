# Regresión de dataset OCR (suite permanente de precisión)

## Propósito

`backend/app/capture_pipeline.process_document` (motor RapidOCR/ONNX
two-pass ROI, ADR-006, plantillas de `backend/app/templates/providers.py`)
es el pipeline real de captura, ya medido por `01-captura-ocr-local-agil` y
`02-mejora-precision-ocr`. Hasta esta feature, ningún test de CI ejercitaba
ese pipeline con el motor OCR real contra un contrato de campos esperados:

- `scripts/benchmark_captura.py` en su modo `--synthetic-mode controlled`
  (el usado en `test_benchmark_captura.py`) usa `synthetic_controlled_result`,
  un atajo que **no invoca OCR real**.
- `backend/tests/test_local_samples_real.py` sí ejecuta OCR real contra
  facturas reales, pero está **gateado**: las imágenes son privadas,
  gitignored, ausentes en cualquier checkout de CI, por lo que la suite se
  salta siempre en ese entorno.

`backend/tests/test_ocr_regression_dataset.py` cierra esa brecha: corre
**siempre**, sin condición de skip, como parte de `pytest -q`/`pytest -v`
(la misma invocación de `.github/workflows/ci.yml`), y falla si el pipeline
deja de producir el resultado esperado en cualquiera de los casos mínimos.
Es la suite de regresión que `07-preprocesamiento-documental-no-destructivo`
ya señaló como pendiente.

## Ubicación del código

- `backend/tests/test_ocr_regression_dataset.py`: módulo de test. Cuatro
  clases (una por caso de regresión) más un test de determinismo de
  fixtures.
- `backend/tests/fixtures/synthetic_ocr_documents.py`: generación de las
  imágenes sintéticas. No es un módulo de test (no matchea
  `test_*.py`/`*_test.py`, ver `pytest.ini`): pytest no lo colecciona, sólo
  se importa desde el módulo de test. Vive junto a `gas_sample.jpg`, el
  patrón ya existente de fixtures en ese directorio.

## Casos cubiertos

Los cuatro casos mínimos exigidos por el spec, cada uno ejecutado contra
`capture_pipeline.process_document` con el motor OCR real (nunca el atajo
`synthetic_controlled_result` de `scripts/benchmark_captura.py`):

| Caso | Clase de test | Fixture | Proveedor/servicio esperado |
|---|---|---|---|
| `LITORAL_GAS` válido completo | `TestLitoralGasValidDocument` | `build_litoral_gas_image()` | `LITORAL_GAS`/`GAS` |
| `CEVT` válido completo | `TestCevtValidDocument` | `build_cevt_image()` | `CEVT`/`ELECTRICITY` |
| `LITORAL_GAS` con `periodo` inválido | `TestLitoralGasInvalidPeriod` | `build_litoral_gas_image(periodo="13/2026")` | `LITORAL_GAS`/`GAS`, `periodo` rechazado |
| Documento no reconocido | `TestUnknownDocument` | `build_unknown_document_image()` | `UNKNOWN` |

Cada clase verifica, por separado (criterio 8 del spec / regla de dominio
OCR de `AGENTS.md`), los cinco estados de campo:

1. **Texto bruto OCR** (`raw_ocr_text`): no vacío, y en los casos con
   proveedor conocido contiene el texto esperable (encabezado del
   proveedor, valor inválido inyectado).
2. **Campo candidato** (`structured_output.candidate_fields`): no `None`
   para los campos que terminan validados o rechazados; `{}` para el
   documento `UNKNOWN` (la plantilla `unknown_template()` tiene
   `fields=[]`, no hay extracción posible).
3. **Campo validado** (`validated_fields`): valor exacto esperado (via
   `values_match`, ver más abajo) para cada `required_field` de la
   plantilla, en los dos casos "válido completo"; para el caso inválido,
   todos los campos **salvo** `periodo` siguen validándose con normalidad
   (el campo inválido no debe arrastrar al resto).
4. **Campo rechazado** (`rejected_fields`): sólo `periodo` en el caso
   inválido, con `reason` no vacío (`month_out_of_range`, de
   `validators.validate_period`) y `value` igual al valor inyectado.
5. **Campo no encontrado** (`missing_fields`): `{}` en los cuatro casos
   (ningún campo queda ambiguamente ausente; el caso inválido demuestra un
   falso positivo evitado real -- `rejected`, no `missing`).

Cada caso "válido completo" también verifica `provider_detected`,
`validated_fields["service"]` y que `quality_gate.evaluate` no haya dado
`reject` (ver más abajo). El caso `UNKNOWN` verifica además que
`validated_fields`/`candidate_fields`/`rejected_fields`/`missing_fields`
no contengan ningún campo de `LITORAL_GAS` ni `CEVT` -- sin campos
inventados para un proveedor no reconocido.

## Criterio de comparación de valores: reutilización de `values_match`

El módulo importa directamente `values_match` de
`scripts/benchmark_captura.py` (`from scripts.benchmark_captura import
values_match`) en vez de reimplementar un segundo criterio de "esperado vs.
obtenido". Mismo comportamiento en toda la suite de precisión del repo:
tolerancia numérica `abs_tol=0.01` para montos (`total`), comparación
normalizada `strip().lower()` para el resto de los campos de texto.

**Decisión de no extraer un módulo compartido nuevo**: el spec dejaba abierta
la posibilidad de extraer `values_match` (y `_base_case_image`/`variant`) a
un módulo compartido importable desde `backend/tests/` y `scripts/`, para
evitar duplicación. Se optó por **no** hacerlo para `values_match`: ya es
trivialmente importable tal cual (`scripts/` no tiene `__init__.py`, pero
`pytest.ini` define `pythonpath = .`, y `backend/tests/test_benchmark_captura.py`
ya hace exactamente `from scripts import benchmark_captura as benchmark`
sin problema). Extraer un módulo nuevo sólo para una función de ~8 líneas
sin estado hubiera sido una capa de indirección sin beneficio real. Para la
generación de imágenes (`_base_case_image`/`variant`) sí se adaptó (no se
reutilizó tal cual): ver la siguiente sección.

## Fixtures: adaptación de `_base_case_image`, no reutilización directa

`backend/tests/fixtures/synthetic_ocr_documents.py` parte de las mismas
posiciones relativas de campo por proveedor que
`scripts/benchmark_captura.py::_base_case_image` (ya alineadas contra las
bandas ROI de `providers.py`), pero con tres diferencias deliberadas,
verificadas empíricamente contra el motor OCR real y `quality_gate.evaluate`
(ver `runs/08-regresion-dataset-ocr/decision.md` para el detalle exacto de
la calibración):

### 1. Fondo gris (210,210,210), no blanco puro

`audit-2.md` (hallazgo no bloqueante) advirtió que `_base_case_image` nunca
se había ejercitado contra `quality_gate.evaluate` con el motor OCR real, y
que un canvas blanco puro con poco texto queda peligrosamente cerca del
umbral `GI_OCR_QUALITY_BRIGHTNESS_BRIGHT_REJECT_ABOVE` (254.5) --
especialmente si el runner de CI cae al fallback `ImageFont.load_default()`
(menos píxeles negros, brillo medio más alto).

Se verificó empíricamente (script exploratorio, no versionado) que un
canvas blanco puro con el texto de `_base_case_image("gas_valid")` da un
brillo medio de **251.17** (verdict `warn`, no `reject`, pero con sólo 3.3
puntos de margen respecto del umbral de `reject`). Con fondo gris
`(210,210,210)`, el brillo medio de las cuatro fixtures de esta suite
(`gas_valid`, `gas_invalid_period`, `cevt_valid`, `unknown`) queda entre
**206.85 y 208.15**, con **~42-47 puntos de margen** respecto de
`warn`/`reject` (250/254.5) y un margen aún mayor respecto del umbral
opuesto (`dark_warn`=70). Verificado también forzando el fallback de fuente
bitmap (`ImageFont.load_default()` sin `arial.ttf`/`DejaVuSans.ttf`
disponibles): el brillo medio sube apenas a ~207-208, sigue muy lejos de
`reject`.

### 2. Canvas más grande (1400x1960, no 1000x1400)

Al calibrar el fixture `LITORAL_GAS` completo se detectó, ejecutando el
motor OCR real, el caso borde explícito del spec ("dos campos que compiten
por el mismo patrón textual"): con el canvas 1000x1400 original, el
detector de texto fusionaba en una sola caja OCR los valores de `cliente`
(`"12345678"`) y `periodo` (`"06/2026"`), dando un texto único
`"1234567806/2026"` que el regex de `cliente` (`\d{8,10}`) interpretaba mal
(`"1234567806"`, 10 dígitos, valor incorrecto). Un canvas más grande separa,
en píxeles absolutos, el mismo gap normalizado entre campos, evitando la
fusión de cajas.

### 3. Reposicionamiento de `vencimiento` dentro de su propia banda

También detectado ejecutando el motor real: el campo `vencimiento`
(`"20/06/2026"`, fecha completa) generaba una caja OCR cuyo centro caía
dentro de la banda ROI de `periodo` (las bandas de ambos campos se solapan
en `litoral_gas_template()`). Como el regex de `periodo`
(`\d{1,2}[/-]\d{4}`) es un subconjunto sintáctico del de una fecha completa,
`re.search` encontraba `"06/2026"` como subcadena de `"20/06/2026"` **antes**
de llegar al texto real de `periodo`, y ese candidato ganaba (aparecía
primero en el orden de cajas OCR). El fixture del caso "válido completo"
evita esta ambigüedad deliberada (tal como exige el spec en "Casos borde")
dibujando `vencimiento` más arriba dentro de su propia banda, de forma que
el centro de su caja OCR quede fuera del rango vertical de la banda de
`periodo`. Verificado con el caso inválido (`periodo="13/2026"`): antes del
ajuste, el `periodo` extraído era `"06/2026"` (de `vencimiento`, no de
`periodo`) y el test de "campo inválido rechazado" pasaba por la razón
equivocada; después del ajuste, `raw_ocr_text` y `candidate_fields["periodo"]`
reflejan correctamente `"13/2026"`, el valor realmente inyectado.

### 4. Fallback de fuente mejorado

`scripts/benchmark_captura.py::_font` cae a `ImageFont.load_default()` (sin
argumentos) si no encuentra `arial.ttf`/`DejaVuSans.ttf` -- en Pillow eso
es una fuente bitmap fija de ~10px, ilegible para OCR a cualquier tamaño de
imagen razonable. `synthetic_ocr_documents._font` usa en cambio
`ImageFont.load_default(size=<size pedido>)` (fuente escalable embebida en
Pillow desde la versión 10.1, confirmado disponible en Pillow 12.3.0 de
`backend/requirements.txt`). Verificado empíricamente forzando este
fallback (sin ninguna TrueType disponible): los cuatro casos de esta suite
dan exactamente el mismo resultado (mismos campos validados/rechazados/
candidatos) que con `arial.ttf`. Esto resuelve, para esta suite en
concreto, el riesgo de calibración por fuente que el spec señalaba como "no
bloqueante" en un runner de CI mínimo.

## Decisión: fixtures generadas en tiempo de test, no versionadas

Se optó por generar cada imagen en memoria dentro del propio test
(`build_litoral_gas_image()`, `build_cevt_image()`,
`build_unknown_document_image()`, guardadas a un `tmp_path` sólo para
pasarle una ruta de archivo a `capture_pipeline.process_document`, que
espera un `path`), en vez de persistir un `.jpg`/`.png` versionado en
`backend/tests/fixtures/` (patrón que sí usa `gas_sample.jpg`).

Motivo: el código que genera cada imagen (posiciones, texto, fondo, fuente)
**es** la especificación exacta y auditable del fixture -- cualquier cambio
queda en el diff de un archivo de texto, revisable en una PR igual que
cualquier otro cambio de código. Un `.jpg`/`.png` binario versionado no es
diffable ni auditable de la misma forma, y el criterio de determinismo del
spec (criterio 10: "generar la misma fixture dado el mismo código, sin
aleatoriedad no controlada") se puede verificar directamente con un test
(`test_synthetic_fixtures_are_deterministic`, compara bytes de dos
generaciones) sin depender de que un binario versionado no se corrompa o
se regenere accidentalmente distinto. `gas_sample.jpg` sigue versionado
porque no es sintético reproducible por código (es una captura real
anonimizada usada por otras features previas); estos cuatro fixtures sí lo
son, así que no hay necesidad de persistirlos como binario.

### 5. Fix post-CI: separación `cliente`/`periodo` sensible a `image_prep.prepare`

Tras el primer merge de esta feature, CI (`ubuntu-latest`, Python 3.12)
falló con 5 tests rojos, todos sobre `periodo` en `LITORAL_GAS` (los 22
pasaban en Windows local). Diagnóstico con evidencia real (reproducido en
un entorno Linux equivalente, ver `runs/08-regresion-dataset-ocr/decision.md`,
"Fix post-CI: separación `cliente`/`periodo`", para el detalle completo):

La causa **no** fue la fuente TrueType faltante (hipótesis inicial
razonable, descartada con evidencia: el bounding box de `periodo` apenas
varía unos píxeles entre `arial.ttf`, `DejaVuSans.ttf` y el fallback
`ImageFont.load_default(size=...)`). La causa real es que
`capture_pipeline.process_document` corre `image_prep.prepare` (feature
`07-preprocesamiento-documental-no-destructivo`, `normalize_scale`) antes
de OCR, reescalando este fixture de 1400x1960 a 1142x1600. Ese reescalado
angosta aún más el ya ajustado hueco horizontal (~44-52px) entre el texto
de `cliente` (banda x:0.66-0.82) y el de `periodo` (banda adyacente/con
solape parcial x:0.78-0.90): el detector de texto (RapidOCR/DBNet) fusiona
ambas cajas en una sola (`"12345678 06/2026"`), cuyo centro cae sólo
dentro de la banda de `cliente` -- `periodo` termina en `missing_fields`
sin haber sido nunca candidato. `cliente` sigue validando bien (su regex
matchea igual dentro del texto fusionado), lo que explica que sólo
`periodo` fallara.

Es una condición de carrera geométrica real entre bandas ROI adyacentes
con muy poco margen, sensible a diferencias de bajo nivel entre
plataformas (antialiasing de FreeType empaquetado por wheel de Pillow,
sensibilidad numérica del post-procesamiento de DBNet) que Windows/Python
3.14 local no disparaba pero Linux/Python 3.12 sí. **Fix**: `periodo` se
dibuja con fuente más chica (22 en vez de 32) y desplazado a la derecha
dentro de su propia banda (`x=0.85, y=0.283`), duplicando con margen el
hueco horizontal frente a `cliente` (de ~44px a ~103px, medido con
`DejaVuSans.ttf`). No se tocó `cliente` ni ninguna banda ROI de
`backend/app/templates/providers.py`. Verificado empíricamente en un
entorno Linux real (no sólo en Windows): 22/22 tests verdes, 3 corridas
consecutivas sin flakiness, más la suite completa (`backend/tests/`) en
ambos entornos sin fallas nuevas -- ver decision.md para el detalle
completo de la reproducción y verificación.

## Determinismo

`test_synthetic_fixtures_are_deterministic` genera cada fixture dos veces
y compara `Image.tobytes()` -- no hay aleatoriedad en ningún paso de
`synthetic_ocr_documents.py` (ni `random`, ni timestamps, ni orden de
iteración no determinista), así que ambas generaciones son bit-a-bit
idénticas.

## Tiempo de ejecución

`backend/tests/test_ocr_regression_dataset.py` completo (22 tests, motor
OCR real, sin `--synthetic-mode controlled`) corre en ~9 segundos en el
entorno de desarrollo de esta feature (ver
`runs/08-regresion-dataset-ocr/decision.md` para el detalle de la corrida),
muy por debajo del orden de magnitud "minutos" que el spec marca como señal
de alerta (criterio 13). El costo dominante es el warmup del motor RapidOCR
(fixture `engine_warm`, scope `module`, se paga una sola vez para toda la
suite) más ~4 documentos procesados con OCR real.

## Relación con `scripts/benchmark_captura.py`

Sin cambios de comportamiento en `scripts/benchmark_captura.py`: sigue
siendo la herramienta operativa de benchmarking de lote grande (hasta 400
documentos, JSON/Markdown, `--synthetic-mode ocr`/`--dataset local`), sin
gate automático de CI y sin cubrir latencia/memoria en esta feature (fuera
de alcance, ver `spec.md`). Esta suite es complementaria: acotada (4 casos
mínimos), permanente, y sí es un gate real -- si el pipeline deja de
producir el resultado esperado, `pytest`/CI fallan.

## Casos borde contemplados

- **Cambio futuro en `providers.py`** (agregar/quitar un campo, banda ROI o
  `classify_keyword`): rompe esta suite si el fixture o el expected output
  quedan desactualizados. Es el comportamiento **deseado** de un gate, no
  un bug -- modificar una plantilla cubierta por esta suite obliga a
  revisar y actualizar su caso de regresión correspondiente. En particular,
  si una `classify_keyword` nueva coincide por accidente con el texto del
  fixture "documento no reconocido"
  (`build_unknown_document_image`), `TestUnknownDocument` fallará
  explícitamente (deja de dar `provider_detected == "UNKNOWN"`), no queda
  en silencio.
- **Entorno sin RapidOCR/ONNX instalado**: `ocr_engine.get_engine()` lanza
  `RuntimeError` explícito (mismo comportamiento que `test_ocr_gas.py`/
  `test_local_samples_real.py`); el fixture `engine_warm` no atrapa esa
  excepción, así que la suite falla con un error claro, no se salta.
- **Orden de ejecución**: cada clase usa su propio fixture `scope="class"`
  (no comparte estado mutable entre casos); el motor OCR es un singleton
  compartido (`ocr_engine.get_engine()`) con el resto de `backend/tests/`
  (`test_ocr_gas.py`, `test_quality_gate.py`, `test_local_samples_real.py`),
  pero es de sólo lectura una vez cargado -- no hay dependencia de orden.
- **Imagen sintética degenerada**: no aplica a estos cuatro fixtures (texto
  fijo, sin variantes aleatorias de rotación/perspectiva como las de
  `scripts/benchmark_captura.py::variant`); si un cambio futuro agrega
  variantes, cada assert de esta suite ya reporta explícitamente qué
  campo/caso rompió (mensajes de `assert` con valores obtenidos/esperados),
  no una excepción genérica.

## Ver también

- [docs/tecnica/mejora-precision-ocr.md](mejora-precision-ocr.md):
  benchmark operativo de precisión/latencia (`scripts/benchmark_captura.py`),
  sin cambios en esta feature.
- [docs/tecnica/calidad-captura-mobile.md](calidad-captura-mobile.md):
  `quality_gate.evaluate`, veredictos y umbrales de brillo/blur usados para
  calibrar estos fixtures.
- [docs/tecnica/preprocesamiento-documental-no-destructivo.md](preprocesamiento-documental-no-destructivo.md):
  `image_prep.prepare`, que corre sobre estos mismos fixtures antes de OCR.
