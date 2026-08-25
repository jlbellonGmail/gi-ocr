# Spec: Suite de regresión OCR/extracción con dataset controlado

## Alcance

Incluye:

- Una suite de tests **permanente, no condicionada a skip por defecto**,
  ejecutada como parte de la invocación estándar `pytest -q`/`pytest -v`
  (la misma que corre `.github/workflows/ci.yml`), que ejerce el pipeline
  real de captura (`backend/app/capture_pipeline.process_document`, motor
  RapidOCR/ONNX two-pass ROI, ADR-006, plantillas de proveedor de
  `backend/app/templates/providers.py`) contra un conjunto mínimo de
  fixtures anónimas o sintéticas controladas, con expected outputs field
  by field para los proveedores/servicios ya configurados hoy
  (`LITORAL_GAS`/`GAS` y `CEVT`/`ELECTRICITY`, ver `providers.py` y
  `backend/config/services.ini`).
- Al menos un caso de regresión por proveedor con documento válido
  completo (`LITORAL_GAS`, `CEVT`), un caso con un valor semánticamente
  inválido en un campo que debe terminar rechazado (no missing, no
  validado), y un caso de documento no reconocido: una imagen sintética
  con texto legible y nítido (misma calidad de imagen que los fixtures
  `gas_valid`/`cevt_valid`, para pasar `quality_gate.evaluate` sin
  disparar `reject` de calidad) pero sin ninguna de las
  `classify_keywords` de `LITORAL_GAS` ni `CEVT`
  (`backend/app/templates/providers.py`), de forma que sí llegue a la
  clasificación de proveedor y resulte en `provider_detected == "UNKNOWN"`
  sin campos inventados (ver criterio 7 y "Riesgos / supuestos" para la
  decisión frente al hallazgo de `audit-1.md` sobre la interacción con
  `quality_gate`).
- Verificación explícita, por caso, de los estados de campo distintos que
  exige `AGENTS.md` (regla de dominio OCR): texto bruto OCR, campo
  candidato, campo validado, campo rechazado, campo no encontrado — no
  alcanza con comparar un único diccionario combinado.
- Reutilización, en la medida de lo razonable, de la lógica de generación
  sintética ya existente en `scripts/benchmark_captura.py`
  (`_base_case_image`, `variant`, `build_synthetic_dataset`) y del mismo
  criterio de comparación de valores (`values_match`, con tolerancia
  numérica para montos), para no introducir un segundo criterio de
  "esperado vs. obtenido" divergente del ya usado por el benchmark
  existente. Si hace falta extraer esas funciones a un módulo compartido
  importable desde `backend/tests/` y desde `scripts/` para evitar
  duplicación, es una decisión de implementación del builder, documentada.
- Que la suite sea un gate real: si el pipeline deja de producir el
  resultado esperado en cualquiera de los casos mínimos, el test
  correspondiente falla y por lo tanto `pytest`/CI fallan (no queda como
  reporte informativo, a diferencia del benchmark de latencia existente).
- Documentación técnica y de usuario, y enlaces de índice
  correspondientes.

Explícitamente NO incluye:

- Cambiar el motor OCR (ADR-006), el formato `.DATA`/`services.ini`
  (ADR-007), ni la separación OCR/extracción/validación/storage
  documentada en `docs/tecnica/arquitectura.md`.
- Medir o gatear performance/latencia (p50/p95, memoria, throughput): eso
  ya es responsabilidad de `02-mejora-precision-ocr` y
  `scripts/benchmark_captura.py` (umbral `hot_p95_s <= 5.0`), sin cambios.
  Esta feature es exclusivamente sobre precisión/corrección estructural
  de la extracción (validated/rejected/missing), no sobre tiempos.
- Reemplazar `scripts/benchmark_captura.py` como herramienta de
  benchmarking de lote grande (400 documentos, JSON/Markdown
  exploratorio): esa herramienta sigue existiendo tal cual para ese
  propósito operativo; esta feature agrega una suite pytest permanente y
  acotada, complementaria, que puede reutilizar su lógica de generación
  de casos sin duplicarla, pero no la sustituye.
- Agregar facturas reales de clientes como fixtures: prohibido por
  `AGENTS.md` (regla de dominio OCR: no versionar comprobantes reales).
  Todo fixture de esta suite es generado por código versionado
  (sintético), nunca derivado de un documento real de un tercero.
- Modificar ni volver obligatoria `backend/tests/test_local_samples_real.py`
  (suite gated sobre muestras privadas gitignored): sigue existiendo tal
  cual, como cobertura opcional adicional cuando hay muestras privadas
  disponibles localmente. Esta feature no depende de esas muestras.
- Extender la cobertura de regresión al motor genérico
  `backend/config/services.ini` +
  `backend/app/extraction_engine.py`/`scripts/evaluate_ocr_service.py`
  (usado para exportación legacy `.DATA` batch, ADR-007). Verificado en
  el código: `capture_pipeline.process_document` (el pipeline web/job real,
  el que ya midieron `01-captura-ocr-local-agil` y
  `02-mejora-precision-ocr`) usa exclusivamente las plantillas de
  `backend/app/templates/providers.py` (`get_template`), **no**
  `extraction_engine`/`services.ini`. Son dos mecanismos de extracción de
  campos distintos y hoy paralelos en el repo, con nombres de campo que no
  coinciden 1:1 (ver "Riesgos / supuestos"). Esta feature cubre el
  pipeline realmente expuesto por la API/cola de jobs
  (`capture_pipeline`), que es el que "precisión ya validada" en el ítem
  `08` del `ROADMAP.md` referencia (mismo pipeline benchmarkeado en `01`/
  `02`). Si el reviewer considera que el motor `services.ini` también
  necesita su propio gate de regresión, debe objetarlo explícitamente:
  sería una feature adicional, no un ajuste menor de esta.
- Scoring de confianza y enrutamiento HITL (`09-confianza-y-enrutamiento-
  hitl`), expediente de auditoría por documento (`20-...`), políticas de
  retención (`21-...`): fuera de alcance.
- Agregar soporte de regresión para un proveedor/servicio que no exista
  hoy en `backend/app/templates/providers.py`: la suite cubre
  `LITORAL_GAS` y `CEVT` (los únicos registrados en `REGISTRY`). Un
  proveedor nuevo futuro agrega su propio caso de regresión como parte de
  la feature que lo introduzca, no de esta.

## Contexto

El pipeline de captura real (`backend/app/capture_pipeline.py`, invocado
por la cola de jobs y por `scripts/benchmark_captura.py`) usa RapidOCR/ONNX
two-pass ROI-focalizada (ADR-006) junto con las plantillas de proveedor
de `backend/app/templates/providers.py` (`get_template`): cada
`ProviderTemplate` (`LITORAL_GAS`, `CEVT`, `UNKNOWN`) define bandas ROI
normalizadas, anclas, regex de extracción y validadores tipados
(`backend/app/validators.py`) por campo. El resultado expone
`structured_output.candidate_fields`, `validated_fields`,
`rejected_fields`, `missing_fields` — los cinco estados de campo que
`AGENTS.md` exige diferenciar (más el texto OCR bruto en
`raw_ocr_text`).

Hoy existen tres piezas relacionadas pero ninguna cierra la brecha que
pide el ítem `08` del `ROADMAP.md`:

1. `scripts/benchmark_captura.py`: ya genera un dataset sintético/
   controlado (`build_synthetic_dataset`, con casos `gas_valid`,
   `cevt_valid`, `gas_invalid_period`, `unknown_blank`) con expected
   outputs por campo, calcula `field_results` (`validated_match`,
   `validated_mismatch`, `rejected`, `rejected_expected`,
   `missing_allowed`, `missing_unexpected`) y `false_positives_avoided`.
   Es una herramienta exploratoria/operativa (JSON + Markdown), pensada
   para lotes grandes (hasta 400 documentos) y para medir además
   latencia/memoria. **No falla** (exit code 0) si la precisión
   estructural empeora; solo marca `risk` en el umbral de latencia p95.
   Además, su modo `--dataset synthetic --synthetic-mode controlled`
   (el usado implícitamente en `test_benchmark_captura.py`) **no invoca
   OCR real**: usa `synthetic_controlled_result`, un atajo que devuelve
   directamente los valores esperados para validar el contrato de
   agregación, no la precisión real del motor.
2. `backend/tests/test_benchmark_captura.py`: tests unitarios sobre las
   funciones de agregación de `benchmark_captura.py`
   (`evaluate_document_result`, `aggregate_results`,
   `render_markdown_report`), todos con un `_pipeline_result()`
   **mockeado a mano**, nunca ejecutan el motor OCR real.
3. `backend/tests/test_local_samples_real.py`: sí ejecuta
   `capture_pipeline.process_document` con el motor OCR real contra
   imágenes reales de factura (`GAS.jpeg`, `cevt.jpeg`) y compara contra
   un contrato (`expected.local.json`), verificando estados
   diferenciados. Pero está **gateado**: ambos archivos están en
   `backend/tests/fixtures/_local_samples/real/`, gitignored y ausentes
   en cualquier entorno de CI, por lo que `pytestmark = pytest.mark.skipif(...)`
   salta toda la suite en CI. Nunca actúa como gate para nadie salvo quien
   tenga esas muestras privadas en su máquina local.

Es decir: la única suite que compara *precisión real* (OCR real +
extracción + validación) contra un contrato de campos esperados está
gateada y ausente en CI; la única suite que corre siempre en CI usa datos
mockeados o no ejecuta OCR real. No existe ningún punto del circuito que
hoy rompa automáticamente si una futura feature (ej. un cambio en
`image_prep.py`, en una plantilla de `providers.py`, en un validador de
`validators.py`, o una actualización de dependencia de RapidOCR/ONNX)
degrada silenciosamente la extracción de un campo ya validado. Esta
feature cierra esa brecha: agrega la suite de regresión permanente que
`07-preprocesamiento-documental-no-destructivo` (en su sección "Riesgos /
supuestos") ya señaló como pendiente ("la suite de regresión permanente y
sistemática con fixtures/expected outputs por proveedor es responsabilidad
de `08-regresion-dataset-ocr`").

Encaja en el pipeline como una capa de verificación transversal: no
cambia OCR, extracción, validación ni storage; los ejercita end-to-end
con fixtures controladas y asegura, vía CI, que un cambio futuro en
cualquiera de esas capas no rompa en silencio un campo/proveedor ya
validado.

## Criterios de aceptación

### Generales (obligatorios en todo spec)

1. Debe existir `docs/tecnica/regresion-dataset-ocr.md`, no vacío, con el
   diseño de la suite: casos cubiertos, fixtures usadas y cómo se
   generan/persisten, criterio de comparación de valores esperados,
   dónde vive el módulo de test, y la decisión de diseño sobre reutilizar
   o no la lógica de `scripts/benchmark_captura.py`.
2. Debe existir `docs/usuario/regresion-dataset-ocr.md`, no vacío, con el
   propósito de la suite (evitar regresiones de precisión OCR/extracción
   ya validada) y un ejemplo concreto de cómo se ejecuta y se interpreta
   un fallo (ej. salida de `pytest -k regresion_dataset -v` mostrando un
   caso roto), dado que esta feature no agrega un endpoint HTTP nuevo.
3. Debe existir `runs/08-regresion-dataset-ocr/decision.md`, con
   decisiones demostrables desde spec/auditoría/implementación (no
   ornamental).
4. Debe existir un enlace exacto a `regresion-dataset-ocr.md` agregado en
   `docs/tecnica/index.md`.
5. Debe existir un enlace exacto a `regresion-dataset-ocr.md` agregado en
   `docs/usuario/index.md`.

### Suite permanente y gate real

6. Debe existir un módulo de test nuevo en `backend/tests/` (nombre a
   definir por el builder, ej. `test_ocr_regression_dataset.py`),
   incluido sin ninguna condición de skip por defecto en la ejecución
   estándar `pytest -q`/`pytest -v` (la misma invocada por
   `.github/workflows/ci.yml`). No debe depender de
   `backend/tests/fixtures/_local_samples/real/` ni de ningún archivo
   gitignored/privado — debe correr igual en un checkout limpio de CI.
7. Debe definir, como mínimo, los siguientes casos de regresión, cada uno
   ejecutado contra `backend/app/capture_pipeline.process_document` con
   el motor OCR real (RapidOCR/ONNX two-pass ROI, ADR-006) — **no** el
   atajo `synthetic_controlled_result` de `scripts/benchmark_captura.py`:
   - **`LITORAL_GAS` válido completo**: Campo(s): `provider`, `cliente`,
     `periodo`, `comprobante`, `fecha_emision`, `vencimiento`, `total`
     (los `required_fields` de `litoral_gas_template()` en
     `backend/app/templates/providers.py`). Documento/servicio:
     `LITORAL_GAS_BILL`/`GAS`. Fixture: imagen sintética generada por
     código (texto dibujado con valores ficticios, análoga a
     `_base_case_image("gas_valid")` de `scripts/benchmark_captura.py`,
     reutilizada o adaptada). Salida esperada: todos los campos listados
     aparecen en `validated_fields` con el valor esperado (tolerancia
     numérica para `total`, comparación normalizada para el resto).
     Validación semántica aplicada: validadores reales de
     `backend/app/validators.py` (`validate_comprobante`,
     `validate_date`, `validate_account`, `validate_period`,
     `validate_amount`), sin mocks. Falsos positivos evitados: ningún
     campo fuera de los esperados aparece en `validated_fields`.
   - **`CEVT` válido completo**: análogo, con los `required_fields` de
     `cevt_template()` (`provider`, `cliente`, `medidor`, `periodo`,
     `comprobante`, `fecha_emision`, `vencimiento`,
     `codigo_pago_electronico`, `total`), documento/servicio
     `CEVT_ELECTRICITY_BILL`/`ELECTRICITY`, fixture análoga a
     `_base_case_image("cevt_valid")`.
   - **`LITORAL_GAS` con campo semánticamente inválido**: mismo fixture
     base que el caso válido, con `periodo` forzado a un valor fuera de
     rango (ej. `13/2026`, igual que `gas_invalid_period` en
     `scripts/benchmark_captura.py`). Salida esperada: `periodo` termina
     en `rejected_fields` con un motivo no vacío (`validate_period`
     debe rechazarlo), **nunca** en `validated_fields` ni ausente sin
     más — es el caso que demuestra un falso positivo evitado real, no
     solo un campo `missing`.
   - **Documento no reconocido**: imagen sintética con texto legible y
     nítido, de calidad de imagen equivalente a los fixtures de los casos
     válidos (`gas_valid`/`cevt_valid`: mismo tamaño de fuente, contraste
     y brillo medio dentro del rango `ok`/`warn`, nunca `reject`, de
     `quality_gate.evaluate`), con contenido textual plausible de un
     comprobante genérico (ej. un rótulo de encabezado, un monto, una
     fecha) pero **sin** ninguna de las `classify_keywords` definidas en
     `backend/app/templates/providers.py` para `LITORAL_GAS`
     (`"litoral gas"`, `"litoralgas"`, `"litoral"`) ni para `CEVT`
     (`"cevt"`, `"cooperativa"`, `"electri"`), ni ninguna subcadena que
     las contenga. **Decisión frente al hallazgo bloqueante de
     `audit-1.md`** (se elige la opción (a) de las dos propuestas por el
     reviewer, en vez de un canvas en blanco): un canvas totalmente en
     blanco hace que `quality_gate.evaluate` (feature
     `06-calidad-captura-mobile`) devuelva verdict `reject` (varianza del
     Laplaciano `0` < `GI_OCR_QUALITY_BLUR_REJECT_BELOW`; brillo medio
     `255.0` > `GI_OCR_QUALITY_BRIGHTNESS_BRIGHT_REJECT_ABOVE`), y
     `capture_pipeline.process_document` corta en
     `_quality_rejected_result` **antes** de clasificar proveedor: ese
     resultado nunca tiene la clave `processing_metadata["provider_detected"]`
     (solo trae `processing_metadata["quality_gate"]` y `engine`), por lo
     que ese fixture prueba el camino de calidad rechazada (feature `06`),
     no la clasificación de proveedor "no reconocido" que es el objetivo
     real de este caso — mezclarlos produciría un test que falla por
     `KeyError`, no por lo que se quiere verificar. Con un documento
     legible sin `classify_keywords`, `quality_gate.evaluate` debe dar
     verdict distinto de `reject`, el pipeline sigue el camino normal
     (`capture_pipeline.py`, líneas ~252-271) y llega a clasificar
     proveedor sobre la plantilla `UNKNOWN` (`providers.py`,
     `required_fields=[]`, `fields=[]`, `classify_keywords=[]`). Salida
     esperada verificada explícitamente: (i)
     `processing_metadata["provider_detected"] == "UNKNOWN"`; (ii)
     `processing_metadata["quality_gate"]["verdict"] != "reject"` (para
     dejar constancia de que el caso efectivamente atravesó el quality
     gate y no lo esquivó por otra vía); (iii) `structured_output.validated_fields`
     no contiene ningún campo de `LITORAL_GAS` ni `CEVT` (sin campos
     inventados para un proveedor no reconocido).
8. Cada caso del criterio 7 debe verificar explícitamente, por separado,
   los estados de campo que exige la regla de dominio OCR de
   `AGENTS.md`: texto bruto OCR (`raw_ocr_text`, no vacío cuando hay
   contenido), campo candidato (`structured_output.candidate_fields`),
   campo validado (`validated_fields`), campo rechazado
   (`rejected_fields`, con motivo), campo no encontrado
   (`missing_fields`) — no alcanza con comparar un único diccionario
   combinado o solo `validated_fields`.
9. El criterio de comparación entre valor esperado y valor obtenido debe
   reutilizar (importar) o replicar exactamente el mismo comportamiento
   que la función `values_match` ya existente en
   `scripts/benchmark_captura.py` (tolerancia numérica `abs_tol=0.01`
   para montos, comparación normalizada `strip().lower()` para texto),
   para no introducir un segundo criterio de comparación divergente sin
   justificación explícita.
10. Determinismo de fixtures: cada fixture sintética debe producir
    siempre la misma imagen dado el mismo código (sin aleatoriedad no
    controlada). Persistirla como archivo versionado en
    `backend/tests/fixtures/` (patrón ya existente para
    `gas_sample.jpg`) o generarla en tiempo de test hacia un directorio
    temporal (`tmp_path`) son ambas opciones aceptables — decisión de
    implementación del builder, documentada explícitamente en
    `docs/tecnica/regresion-dataset-ocr.md`, incluido el motivo.
11. Evidencia de que la suite es un gate real (no solo informativo): el
    `test-report` de QA debe dejar constancia de al menos una corrida en
    la que, al alterar deliberadamente un valor esperado o el resultado
    de un caso (por ejemplo, vía una modificación temporal revertida
    después, o un caso auxiliar que fuerza un campo a un valor
    incorrecto conocido), el test correspondiente falla con un mensaje
    claro de qué campo/caso rompió — sin dejar ese sabotaje como test
    permanente en el repo.
12. La suite no debe introducir dependencia de red ni de servicios
    externos: mismo motor OCR local ya usado por el resto de
    `backend/tests/` (RapidOCR/ONNX, cargado en proceso, sin llamadas a
    APIs externas).
13. Tiempo de ejecución acotado: los casos nuevos de esta suite no deben
    multiplicar de forma desproporcionada el tiempo de `pytest -q`
    (referencia de ADR-006: ~2.35–2.57s por documento en caliente; con 4
    casos mínimos más warmup del motor, el orden de magnitud esperado es
    de segundos, no minutos). Si el builder agrega más casos, debe
    mantenerlos acotados y documentar el tiempo total agregado en el
    `test-report`.

### No regresión sobre la suite existente

14. La suite completa de tests existente (`backend/tests/`, `pytest -q`)
    sigue en verde. En particular, `test_local_samples_real.py` (gated,
    privado) y `test_benchmark_captura.py` (unitario sobre agregación,
    sin OCR real) quedan sin cambios de comportamiento ni de
    expectativas.

## Casos borde a contemplar

- Fuente tipográfica (`ImageFont`) no disponible en el runner de CI:
  `scripts/benchmark_captura.py::_font` cae a
  `ImageFont.load_default()` (fuente bitmap pequeña) si no encuentra
  `arial.ttf`/`DejaVuSans.ttf`, lo que puede degradar la legibilidad del
  texto dibujado y producir un falso negativo de la propia suite (no del
  pipeline real). Debe contemplarse tamaño de fuente y contraste
  suficientes, y verificarse en CI real, no solo en desarrollo local.
- **Interacción entre `quality_gate` (feature `06-calidad-captura-mobile`)
  y esta suite (`08`)**: cualquier fixture sintética de esta suite, no
  solo la del caso "documento no reconocido", pasa primero por
  `quality_gate.evaluate` dentro de `capture_pipeline.process_document`
  antes de llegar a OCR/clasificación. Un fixture demasiado "limpio" (poco
  texto, fondo mayormente blanco, contraste muy alto) puede acercarse a
  los umbrales de brillo (`GI_OCR_QUALITY_BRIGHTNESS_BRIGHT_WARN_ABOVE` /
  `_REJECT_ABOVE` en `backend/app/quality_gate.py`) y producir un
  `warn`/`reject` espurio de **calidad de imagen**, no un problema de
  legibilidad OCR (que es el riesgo ya contemplado en el punto anterior,
  sobre la fuente tipográfica). Todo caso de esta suite debe verificar
  también `processing_metadata["quality_gate"]["verdict"]` (o su
  ausencia, en el único caso donde se verifica explícitamente el camino
  de rechazo por calidad) para distinguir un fallo por clasificación/
  extracción de un fallo por interacción no contemplada con `06`.
- Campo con formato ambiguo soportado por el regex de la plantilla (ej.
  separador `-` vs `/` en fechas) que la fixture sintética no cubre: no
  inventar variantes no soportadas por la plantilla vigente de
  `providers.py`.
- Cambio futuro legítimo en `backend/app/templates/providers.py` (agregar
  o quitar un campo/banda ROI de una plantilla existente, o agregar/quitar
  una `classify_keyword`) que rompe esta suite porque el fixture o el
  expected output quedaron desactualizados: debe documentarse en
  `docs/tecnica/regresion-dataset-ocr.md` que modificar una plantilla
  cubierta por esta suite obliga a revisar y actualizar su caso de
  regresión — es el comportamiento **deseado** de un gate, no un bug de
  la suite. En particular, si una `classify_keyword` nueva coincide por
  accidente con el texto del fixture "documento no reconocido", ese caso
  dejaría de ser `UNKNOWN` y el test debe fallar de forma explícita, no
  quedar en silencio.
- Entorno sin el motor RapidOCR/ONNX correctamente instalado
  (dependencias faltantes): debe fallar con un error claro (mismo
  comportamiento que hoy tiene `test_ocr_gas.py`/
  `test_local_samples_real.py` al usar el motor real) — no debe
  silenciarse ni saltarse por default, a diferencia de
  `test_local_samples_real.py` (que sí se salta, pero por ausencia de
  fixtures privadas, no por ausencia del motor).
- Imagen sintética degenerada (texto solapado, campos pisándose) por una
  variante mal calibrada: el test debe fallar con un mensaje que indique
  qué caso/campo rompió, no una excepción genérica sin contexto.
- Orden/aislamiento de ejecución: como la suite comparte el motor OCR
  cargado en proceso (posible warmup singleton) con otros tests
  (`test_ocr_gas.py`, `test_local_samples_real.py`,
  `test_benchmark_captura.py`), debe funcionar sin importar el orden en
  que `pytest` los ejecute.
- Documento con dos campos que compiten por el mismo patrón textual (ej.
  dos secuencias de 8-10 dígitos en la misma imagen, una es `cliente` y
  otra no debería capturarse): la fixture del caso "válido completo" debe
  evitar ambigüedad deliberada, para no convertir esta suite en un test
  de desambiguación que no es su objetivo (eso, si hace falta, es una
  fixture adicional explícita, no un caso accidental).

## Riesgos / supuestos

- **Resolución del hallazgo bloqueante de `audit-1.md` (fixture "documento
  no reconocido")**: el reviewer propuso dos opciones explícitas — (a)
  fixture con texto legible/nítido sin `classify_keywords`, o (b) mantener
  el canvas en blanco pero reescribir el criterio para verificar el camino
  de `quality_gate` rechazado en vez de `provider_detected`. Se elige (a),
  siguiendo la recomendación del propio reviewer: "documento no
  reconocido" (clasificación de proveedor `UNKNOWN` con OCR exitoso) y
  "calidad de imagen rechazada" (feature `06`) son dos casos de falla
  conceptualmente distintos, y mezclarlos en un único fixture de canvas en
  blanco oscurecía el objetivo real de este caso de regresión. La opción
  (b) queda descartada para este caso, aunque el caso borde de interacción
  con `quality_gate` (ver arriba) sigue exigiendo verificar
  `processing_metadata["quality_gate"]["verdict"]` en todos los casos de
  la suite, no solo en este.
- **Ámbito del pipeline cubierto**: esta suite cubre
  `capture_pipeline.process_document` + `templates/providers.py` (el
  pipeline web/job real, el mismo que midieron `01-captura-ocr-local-agil`
  y `02-mejora-precision-ocr`), **no** el motor genérico
  `extraction_engine`/`services.ini` (ADR-007, usado por
  `scripts/evaluate_ocr_service.py` para exportación `.DATA` batch).
  Verificado en el código: son dos mecanismos de extracción distintos y
  paralelos, con vocabularios de campo que no coinciden 1:1 (ej.
  `services.ini` usa `nro_medidor`/`a_pagar_hasta`/`importe` para `GAS`,
  mientras `providers.py` usa `medidor`/`vencimiento`/`total` para
  `LITORAL_GAS`). Se interpreta que "precisión ya validada" en el ítem
  `08` del `ROADMAP.md` se refiere al pipeline efectivamente benchmarkeado
  en `01`/`02` (`capture_pipeline`). Si el reviewer considera que
  `services.ini`/`extraction_engine` también necesita su propio gate de
  regresión, debe objetarlo explícitamente — sería una ampliación de
  alcance no trivial, potencialmente una feature separada.
- **Persistencia de fixtures**: se deja como decisión del builder
  (archivo versionado vs. generado en tiempo de test) porque ya existen
  ambos patrones en el repo (`backend/tests/fixtures/gas_sample.jpg`
  versionado; `scripts/benchmark_captura.py::build_synthetic_dataset`
  generado en `_bench/`, gitignored). El reviewer puede objetar si
  prefiere fijar una sola convención para esta suite.
- **Reutilización de `scripts/benchmark_captura.py`**: se asume deseable
  reutilizar su lógica de generación de casos sintéticos (`_base_case_image`,
  `variant`) y su criterio de comparación (`values_match`) en vez de
  duplicarlos, aunque implique un refactor menor (extraer funciones a un
  módulo compartido importable desde `backend/tests/` y desde
  `scripts/`). Si el reviewer prefiere una suite totalmente independiente
  sin tocar `scripts/benchmark_captura.py`, debe objetarlo
  explícitamente: es una decisión de diseño sobre acoplamiento entre
  `scripts/` y `backend/tests/`, no trivial.
- **Riesgo de calibración/flakiness por fuentes del sistema operativo**:
  la generación de texto sintético depende de fuentes TrueType
  (`arial.ttf`/`DejaVuSans.ttf`) que pueden no estar disponibles en todos
  los entornos de CI, cayendo a una fuente bitmap por defecto que podría
  degradar la lectura OCR real y producir falsos negativos de la propia
  suite (no del pipeline). El builder debe verificarlo en CI real y, si
  hace falta, fijar una fuente empaquetada o ajustar tamaño/contraste —
  riesgo de calibración explícito, no bloqueante para este spec.
- **No reabre ADR-006, ADR-007 ni la separación OCR/extracción/
  validación/storage** documentada en `docs/tecnica/arquitectura.md`;
  esta feature es estrictamente aditiva (un módulo de test nuevo +
  documentación), sin tocar el pipeline de producción.
- **Relación con `scripts/benchmark_captura.py` como benchmark
  operativo**: esta feature no cambia el umbral de latencia (`hot_p95_s
  <= 5.0`) ni el modo `--dataset local --docs 400` usado como evidencia
  de `02-mejora-precision-ocr`; ambos siguen siendo responsabilidad de
  esa feature, sin cambios.
