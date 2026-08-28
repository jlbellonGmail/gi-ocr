# Decision: 07-preprocesamiento-documental-no-destructivo

## Estado

Implementación builder-agent lista para QA. No se marca `ROADMAP.md` y no
se crea PR en esta etapa.

## Evidencia de entrada

- `runs/07-preprocesamiento-documental-no-destructivo/spec.md`: exige (1)
  verificar por test que el pipeline nunca modifica el archivo original en
  `output/uploads/`, incluido `POST /retry`; (2) agregar una traza
  determinística y ordenada de las transformaciones de imagen dentro de
  `processing_metadata`, honesta sobre lo que efectivamente corre en el
  camino imagen y en el camino PDF; (3) un paso nuevo de normalización de
  contraste/iluminación en `image_prep.py`, puro, con salvaguarda
  verificable contra sobre-procesamiento; (4) idempotencia de
  reprocesamiento; (5) documentación y artefactos del circuito.
- `runs/07-preprocesamiento-documental-no-destructivo/audit-1.md`:
  `rejected` — el spec (versión previa) afirmaba incorrectamente que el
  camino PDF "nunca ejecuta" deskew/perspectiva/contraste, contradiciendo
  el código real (`_process_pdf` llama a la misma `image_prep.prepare()`
  con los mismos defaults que el camino imagen) y generando una
  contradicción interna con el criterio que exige integrar el contraste
  dentro de `prepare()`.
- `runs/07-preprocesamiento-documental-no-destructivo/audit-2.md`:
  `approved` — la corrección del spec deja claro que sólo
  `apply_exif_orientation` y `quality_gate.evaluate` están genuinamente
  ausentes del camino PDF, mientras que `correct_orientation`, `deskew`,
  `correct_perspective` (si se pide) y `normalize_scale` (y, tras esta
  feature, `normalize_contrast`) corren y deben trazarse igual en ambos
  caminos porque comparten `prepare()`.

## Decisiones tomadas

### Nombre de la clave nueva en `processing_metadata`

`preparation_trace`: lista ordenada de `{"step": str, "applied": bool,
...}`. Se prefirió sobre alternativas como `image_prep_trace` o
`transformations` porque describe la etapa del pipeline que instrumenta
(preparación de imagen antes de OCR, `image_prep.prepare()`), es
consistente con el nombre del módulo, y no colisiona con ninguna clave ya
usada en `processing_metadata` (`quality_gate`, `timings`, `engine`,
`is_pdf`, `pdf_pages`, `pdf_pages_ocr`, `provider_detected`,
`provider_confidence`).

### Nombre de la función de contraste

`image_prep.normalize_contrast(image_np: np.ndarray) -> np.ndarray`
(pública, misma firma que `deskew`/`correct_perspective`). Consistente con
el nombre ya existente `normalize_scale` (misma familia "normalizar algo
de la imagen"), y explícito sobre qué normaliza (contraste, no orientación
ni escala).

### Instrumentación sin romper firmas públicas existentes

`correct_orientation`, `deskew`, `correct_perspective`, `normalize_scale`
**mantienen exactamente la misma firma** que antes de esta feature —
verificado no rompiendo ningún test existente
(`backend/tests/test_image_prep.py`, `backend/tests/test_exif_orientation.py`,
sin modificar ninguna expectativa). Cada una delega en una función interna
`_*_impl(...)` que calcula la misma transformación y además devuelve
metadata (`dict`) para la traza; las funciones públicas simplemente
descartan esa metadata (`img, _meta = _*_impl(...); return img`).
`image_prep.prepare(..., trace: Optional[list] = None)` invoca
directamente las `_*_impl` (no las envolventes) para no duplicar cómputo
entre "hacer la transformación" y "calcular qué reportar". Si `trace` es
`None` (default), el comportamiento y el costo son idénticos a antes de
esta feature.

### Punto de integración del contraste en `prepare()`

Después de `normalize_scale` (orden final:
`correct_orientation → deskew → correct_perspective (opcional) →
normalize_scale → normalize_contrast`), tal como ya sugería el orden
descrito en el criterio 9 del spec. Motivo: opera sobre la imagen ya en su
tamaño final (más barato, y es exactamente la imagen que ve el OCR — no
tiene sentido reportar contraste sobre una resolución intermedia que luego
se reescala). Documentado con más detalle en
`docs/tecnica/preprocesamiento-documental-no-destructivo.md`.

### `apply_exif_orientation` vive fuera de `prepare()`, pero dentro de la
misma lista de traza

Como ya era cierto antes de esta feature, `apply_exif_orientation` corre
en `capture_pipeline.process_document` **antes** de llamar a
`image_prep.prepare()` (no es un paso interno de `prepare()`). La traza
correspondiente se construye igual: `process_document` arma la lista,
agrega la entrada de EXIF primero, y se la pasa a
`prepare(..., trace=trace)`, que sigue agregando sus propias 5 entradas en
orden. El resultado final tiene 6 entradas en el camino imagen y 5 en el
camino PDF (sin la de EXIF) — ver más abajo.

### Camino PDF: sin parámetro `is_pdf`, traza honesta por construcción

Tal como advertía el spec en "Riesgos / supuestos" (y confirmó
`audit-2.md`), no se agregó ningún parámetro nuevo a `prepare()` para que
se comporte distinto según el llamador. `_process_pdf` sigue llamando a
`image_prep.prepare(page_to_process["image"], trace=trace)` con los mismos
defaults que siempre tuvo; la instrumentación de traza, al vivir dentro de
`prepare()`, aplica automáticamente y sin código adicional a ese camino.
El resultado: la traza de un PDF tiene 5 entradas honestas
(`correct_orientation`, `deskew`, `correct_perspective`, `normalize_scale`,
`normalize_contrast`), nunca `apply_exif_orientation` ni `quality_gate`
(ninguno de los dos se invoca ahí, sin cambios de esta feature) —
verificado por test sobre un PDF sintético con imagen renderizada
(`test_pdf_with_rendered_image_trace_excludes_exif_and_quality_gate`).

### Sub-camino `_process_pdf_native`: sin traza, documentado como ausencia
explícita

Cuando un PDF trae texto nativo suficiente en todas sus páginas, nunca se
renderiza imagen y `prepare()` nunca se invoca; `_process_pdf_native` no
agrega ninguna clave `preparation_trace` al resultado (mismo criterio que
el caso `reject` de `quality_gate`, ver abajo). Se construyó un fixture
sintético de PDF con texto nativo **a mano** (sintaxis PDF cruda con fuente
estándar Helvetica) porque la versión de `pypdfium2` fijada en
`backend/requirements.txt` (`5.13.0`) no expone una API simple de autoría
de texto (`PdfPage.insert_text`/`PdfTextObj.new` no existen en esta
versión) — verificado por inspección directa del paquete instalado. El PDF
a mano es válido y legible por `pypdfium2` (confirmado por test), sigue
siendo 100 % sintético y no requiere ninguna dependencia nueva.

### Caso `quality_gate.verdict == "reject"`: `preparation_trace` ausente,
no lista vacía "inventada"

`_quality_rejected_result` no incluye la clave `preparation_trace` en
absoluto. Se prefirió "ausente" sobre "lista vacía `[]`" porque, en este
caso, ni siquiera se llegó a evaluar la entrada de
`apply_exif_orientation` como parte de la traza final (aunque
`apply_exif_orientation` sí corrió, antes del corte por `quality_gate`, no
tiene sentido exponer una traza parcial de un solo paso cuando el resto
del pipeline de preparación nunca corrió) — más honesto que sugerir con
una lista vacía que "no se aplicó ningún paso" cuando en realidad "no se
evaluó ningún paso de `prepare()`".

### Algoritmo de contraste: CLAHE sobre canal L de LAB, con salvaguarda
"intentar y verificar" (no un umbral fijo de contraste global)

Se calibró inicialmente sobre `backend/tests/fixtures/gas_sample.jpg` un
umbral fijo de desvío estándar de intensidad global como criterio de "ya
tiene buen contraste, no tocar". Se descubrió empíricamente que esa
fixture (representativa del estilo real de comprobantes: fondo blanco
dominante, texto disperso) tiene un desvío estándar global **bajo**
(`~12.3` sobre 0-255) **aunque está perfectamente iluminada** — el fondo
blanco domina la mayoría de los píxeles, así que la dispersión global no
es un buen proxy de legibilidad. Un umbral fijo sobre ese valor habría
disparado CLAHE sistemáticamente sobre documentos ya buenos, contradiciendo
la salvaguarda que el propio criterio 15 del spec exige.

Se reemplazó por un patrón "intentar y verificar": siempre se calcula la
versión mejorada (CLAHE, `clipLimit=2.0`, `tileGridSize=(8,8)`, sobre el
canal L de LAB), se mide la varianza del Laplaciano (mismo proxy de
nitidez que ya usa `quality_gate._blur_signal`) antes y después, y sólo se
acepta el resultado si no cae más de un 10 % (`_CONTRAST_SHARPNESS_SAFETY_MARGIN
= 0.9`). Calibrado empíricamente: sobre `gas_sample.jpg` (ya bien
iluminado) la variación real es -1.8 % (se acepta, muy por debajo del
límite); sobre `gas_sample.jpg` oscurecido artificialmente la mejora es
+32 %; sobre una fixture sintética de bajo contraste la mejora es +175 %.
Se mantiene, además, un chequeo barato adicional: si el desvío estándar
global es menor a `1.0` (imagen casi perfectamente plana, por ejemplo una
página de PDF en blanco), no se intenta nada — no hay estructura real que
mejorar. Detalle completo, con la tabla de calibración, en
`docs/tecnica/preprocesamiento-documental-no-destructivo.md`.

La salvaguarda en sí se probó de forma determinística con
`unittest.mock.patch` sobre `image_prep._apply_clahe` (forzando una
"mejora" que en realidad desenfoca, vía `cv2.GaussianBlur`), sin depender
de encontrar una fixture real que la dispare naturalmente
(`test_normalize_contrast_safety_guard_discards_degrading_enhancement`).

### Regla de dominio OCR: `gas_sample.jpg` no clasifica a un proveedor
conocido (hallazgo verificado, preexistente, no introducido por esta
feature)

Al construir el test de regresión del criterio 16 (comparar
`validated_fields` con/sin el paso de contraste sobre el fixture GAS de
referencia), se descubrió que `backend/tests/fixtures/gas_sample.jpg` **ya
no clasificaba a ningún proveedor conocido** (`provider_detected:
"UNKNOWN"`, `validated_fields: {}`) **antes** de esta feature — verificado
explícitamente corriendo `capture_pipeline.process_document` sobre el
código sin ningún cambio (`git stash`), confirmando que es un
comportamiento preexistente e independiente de este cambio: el texto OCR
de esa fixture (`"COMPROBANTEGAS\nServicio de Gas Natural\n..."`) no
contiene ninguna de las palabras clave de clasificación de
`LITORAL_GAS` (`classify_keywords=["litoral gas", "litoralgas",
"litoral"]`, ver `backend/app/templates/providers.py`) — el fixture no
menciona "Litoral" en absoluto. Esto es una discrepancia entre el fixture
de test y el proveedor de referencia del template GAS, ajena al alcance de
esta feature (que no toca `templates/providers.py` ni `services.ini`).

Dado que el criterio 16 exige verificar "falsos positivos evitados" (no
inventar/deformar dígitos), se ajustó el test para comparar directamente
las secuencias de dígitos (`re.findall(r"\d+", ...)`) extraídas de
`raw_ocr_text` con y sin el paso de contraste — el OCR sí reconoce
correctamente todos los números del comprobante en ambos casos (número de
cliente, medidor, período, vencimiento, importe), y esa comparación es la
que efectivamente prueba lo que el criterio pide, sin depender de que la
clasificación de proveedor funcione sobre este fixture puntual. Esta
discrepancia queda documentada aquí y en
`docs/tecnica/preprocesamiento-documental-no-destructivo.md`; no se
corrigió el fixture ni `templates/providers.py` por estar fuera del
alcance declarado del spec (no reabre ADR-004/`services.ini`).

### No-destructividad de `/retry`: se usa un job `needs_new_photo`, no
`ready`

`JobQueue.retry()` bloquea explícitamente los estados `ready`/`confirmed`
(comportamiento preexistente, sin cambios de esta feature): un job ya
`ready` no se puede reintentar por diseño. Para verificar la invariante de
no-destructividad del criterio 7 vía `TestClient` real, el test usa una
imagen que dispara `quality_gate.verdict == "reject"` (estado
`needs_new_photo`, explícitamente reintentable según
`docs/tecnica/calidad-captura-mobile.md`), hashea el archivo original
antes y después del `retry`, y confirma que el hash no cambia.

## Alcance no modificado

- No se reabrió el motor OCR (RapidOCR/ONNX, ADR-006) ni el two-pass ROI.
- No se tocó `backend/config/services.ini` ni el formato `.DATA`.
- No se cambió la lógica de `05-correccion-orientacion-exif` ni
  `06-calidad-captura-mobile`: `apply_exif_orientation`,
  `correct_orientation` (heurística), `quality_gate.evaluate` siguen
  exactamente igual, sólo instrumentados con traza donde corresponde.
- No se cambió qué pasos corren sobre el camino PDF: `deskew`,
  `correct_perspective`, `normalize_scale` ya corrían ahí antes de esta
  feature (verificado contra el código); esta feature sólo los traza.
- No se agregó ningún archivo de imagen "preparada" persistente nuevo en
  disco: la traza vive únicamente dentro de `processing_metadata`, ya
  serializado en `output/jobs/{job_id}.json`.
- No se agregó ninguna dependencia nueva: se usa `opencv-python-headless`,
  ya declarada en `backend/requirements.txt` y ya usada por
  `image_prep.py`.
- No se versionaron comprobantes reales: todas las fixtures de test son
  sintéticas o reutilizan `backend/tests/fixtures/gas_sample.jpg` (ya
  sintético).

## Verificación de tests

Entorno: `.venv` propio del worktree (`python -m venv .venv` con Python
3.14, `pip install -r backend/requirements.txt`, con
`PIP_USER=0`/`--no-user` para evitar que la config global de `pip` del
equipo — `install.user = true` — entre en conflicto con el entorno
virtual). Se usó `--basetemp` apuntando a un directorio propio para
sortear un problema de entorno preexistente (permiso denegado sobre
`%TEMP%/pytest-of-<usuario>` en Windows), no relacionado con esta feature
(ya documentado en `runs/06-calidad-captura-mobile/decision.md`).

- `backend/tests/test_preparation_trace.py` (nuevo, 25 tests): no-
  destructividad (hash SHA-256 antes/después, directo y vía
  `TestClient`/`retry`), traza ordenada en camino imagen y PDF, ausencia
  de traza en `reject`/`_process_pdf_native`, distinción
  "omitido"/"intentado sin encontrar" en perspectiva, ángulo de deskew,
  factor de escala, determinismo/salvaguarda/mejora del paso de contraste,
  regla de dominio OCR sobre el fixture GAS (dígitos preservados),
  idempotencia de reprocesamiento. Todos verdes.
- `backend/tests/test_image_prep.py`, `backend/tests/test_exif_orientation.py`,
  `backend/tests/test_quality_gate.py`, `backend/tests/test_pdf_util.py`:
  sin modificar sus expectativas, todos verdes — confirma que la
  instrumentación de traza no cambia el comportamiento de los pasos
  existentes.
- Suite completa (`pytest -q` sobre `backend/tests/` + `tests/`): ver
  resultado final más abajo (a completar por QA si corresponde re-
  verificar en su propio entorno).

## Artefactos

- `backend/app/image_prep.py` (`_correct_orientation_impl`,
  `_deskew_impl`, `_correct_perspective_impl`, `_normalize_scale_impl`,
  `_normalize_contrast_impl`, `_apply_clahe`, `_contrast_metric`,
  `_sharpness_metric`, `_append_step`, `normalize_contrast` nuevo,
  `prepare(..., trace=None)`)
- `backend/app/capture_pipeline.py` (`process_document`, `_process_pdf`:
  armado de `preparation_trace`)
- `backend/tests/test_preparation_trace.py` (nuevo)
- `docs/tecnica/preprocesamiento-documental-no-destructivo.md`
- `docs/usuario/preprocesamiento-documental-no-destructivo.md`
- `runs/07-preprocesamiento-documental-no-destructivo/decision.md`
