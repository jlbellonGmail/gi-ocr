# Calidad de captura mobile (control de calidad previo al OCR)

## Propósito

El caso de uso real de este sistema es un frontend mobile-first
(`frontend/`) donde el usuario fotografía un comprobante rápido, muchas
veces con mala luz, encuadre apurado o superficies reflectantes (plástico,
vidrio). Sin un filtro previo:

- Se gasta cómputo OCR (RapidOCR/ONNX, ~2.35–2.57 s/documento medido en
  `01-captura-ocr-local-agil`, ver `docs/tecnica/captura-ocr-local-agil.md`)
  en fotos que no tienen ninguna chance de producir campos útiles
  (documento cortado a la mitad, foto negra/blanca casi pura).
- El usuario recibe recién en la pantalla de revisión (`job` en estado
  `ready` con `missing_fields` lleno) la señal de que algo salió mal, en
  vez de en el momento de la captura, cuando todavía tiene el documento a
  mano para repetir la foto.

`backend/app/quality_gate.py` agrega un chequeo de calidad de imagen
sincrónico que corre **antes** del motor OCR, evalúa 8 señales de calidad
de captura y produce un veredicto de tres niveles (`ok`/`warn`/`reject`)
que decide si el documento sigue el pipeline normal, sigue con una
advertencia, o vuelve al usuario pidiendo una foto nueva sin gastar OCR.

## Punto de integración en el pipeline

`backend/app/capture_pipeline.py::process_document`, en el camino de
imagen (no PDF, ver "Fuera de alcance"):

```python
img: Image.Image = Image.open(path)
img, exif_applied = image_prep.apply_exif_orientation(img)
img = img.convert("RGB")
arr = np.array(img)

quality = quality_gate.evaluate(arr)
if quality["verdict"] == "reject":
    return _quality_rejected_result(src, quality)   # no se invoca OCR

prepared = image_prep.prepare(arr, exif_orientation_applied=exif_applied)
result = process_image(prepared, src)
result["processing_metadata"]["quality_gate"] = quality
return result
```

El chequeo corre **después** de `apply_exif_orientation` (para no penalizar
como "mala perspectiva" o "documento cortado" una foto que solo estaba
rotada por metadata) y **antes** de `image_prep.prepare` (deskew/
perspectiva/escala) y de OCR (`ocr_engine`/`process_image`), coherente con
el objetivo de "evitar gastar cómputo OCR": el chequeo debe ocurrir antes
de cualquier preparación cara, no después.

## Veredicto agregado de tres niveles

`quality_gate.evaluate(image_np: np.ndarray) -> dict` devuelve:

```json
{
  "verdict": "ok" | "warn" | "reject",
  "reasons": [
    {"signal": "<id>", "severity": "warn" | "reject", "message": "<texto para UI>"}
  ],
  "signals": {
    "<id>": {"metric": <float o null>, "verdict": "ok" | "warn" | "reject" | "not_evaluable"}
  }
}
```

- Cada una de las 8 señales produce un sub-veredicto independiente
  (`ok`/`warn`/`reject`), o `not_evaluable` cuando la señal no pudo
  evaluarse (por ejemplo, no se detectó ningún contorno de documento).
- El veredicto agregado es el **peor** sub-veredicto entre todas las
  señales evaluables (`reject` > `warn` > `ok`). `reasons` lista **todas**
  las señales en `warn`/`reject`, no solo la primera encontrada.
- Semántica en `capture_pipeline`/`job_queue`:
  - **`ok`**: pipeline normal. `processing_metadata.quality_gate` queda
    como bloque informativo neutro (`verdict: "ok"`, `reasons: []`).
  - **`warn`**: pipeline normal igual que `ok` (no se bloquea, no se pide
    nueva foto), pero `processing_metadata.quality_gate.verdict == "warn"`
    con las razones concretas, para que la UI de revisión (`renderReady`
    en `frontend/src/app.js`) muestre un aviso de "posible baja confianza".
  - **`reject`**: **no se invoca OCR**. `capture_pipeline.process_document`
    devuelve un resultado mínimo (mismo "shape" que el resultado normal,
    con `structured_output`/`field_scores` vacíos) y `job_queue.py::_process`
    deja el job en el estado `needs_new_photo` (ver más abajo), sin llamar
    `store.save_original`.

## Las 8 señales

Todas las funciones viven en `backend/app/quality_gate.py`. Cada señal
nunca lanza excepción: `evaluate()` envuelve cada cálculo en
`_safe_signal`/`try-except`, y ante cualquier error de OpenCV o imagen
degenerada devuelve `(None, None)` — la señal queda `not_evaluable` en vez
de romper el pipeline (ver "Casos borde").

### 1. Blur / desenfoque

- **Métrica**: varianza del Laplaciano (`cv2.Laplacian(gray, cv2.CV_64F).var()`)
  sobre la imagen en escala de grises. Valores más altos = imagen más
  nítida (más bordes de alta frecuencia).
- **Umbrales por defecto**: `GI_OCR_QUALITY_BLUR_REJECT_BELOW=40.0`,
  `GI_OCR_QUALITY_BLUR_WARN_BELOW=100.0`. `metric < 40` → `reject`;
  `40 <= metric < 100` → `warn`; `metric >= 100` → `ok`.
- **Justificación del umbral**: calibrado empíricamente contra fixtures
  sintéticas de este repo (documento con texto denso 1200x1600, variantes
  con `cv2.GaussianBlur` de distinto `sigma`). No calibrado contra fotos
  reales de celular (ver "Riesgo de calibración" más abajo).
- **Limitación conocida documentada explícitamente** (exigida por el
  criterio 6 del spec): una imagen nítida pero de **fondo uniforme** (poco
  detalle, por ejemplo un documento fotografiado sobre una superficie lisa
  sin apenas texto) puede dar una varianza de Laplaciano baja aunque la
  imagen esté perfectamente enfocada, porque la métrica depende de que
  haya suficiente densidad de bordes/texto para ser representativa. Los
  tests (`backend/tests/test_quality_gate.py`) usan una fixture con texto
  denso para evitar este falso positivo en la suite, pero la limitación en
  sí sigue existiendo en producción para documentos realmente muy
  "vacíos" (por ejemplo, un documento casi en blanco con una sola línea de
  texto). Es un trade-off inherente a esta métrica, no un bug.

### 2. Baja resolución

- **Métrica**: `min(height, width)` de la imagen tal como llega —
  **antes** de `image_prep.normalize_scale` (que reduce el lado *mayor* a
  1600px pero nunca sube resolución). El chequeo corre sobre `arr`
  (imagen original recién orientada por EXIF), no sobre ninguna copia ya
  preparada.
- **Umbrales por defecto**: `GI_OCR_QUALITY_MIN_SIDE_REJECT_BELOW=500.0`,
  `GI_OCR_QUALITY_MIN_SIDE_WARN_BELOW=900.0`.
- **Justificación**: 500px de lado menor es, en la práctica, el punto
  donde el texto de un comprobante fotografiado completo deja de tener
  suficiente detalle para que RapidOCR reconozca caracteres pequeños
  (importes, números de medidor). 900px da margen de alerta temprana
  (`warn`) antes de llegar al piso duro. Ambos valores son heurísticos, no
  medidos contra un corpus real (mismo riesgo de calibración).
- **Caso borde explícito (identificador estable)**: una imagen con
  resolución baja por limitación real del dispositivo (celular viejo,
  cámara de baja resolución) no se puede corregir pidiendo "otra" foto —
  sería la misma resolución. El identificador de razón (`"signal":
  "low_resolution"`) es estable y distinto de cualquier otra señal, y el
  mensaje (`REASON_MESSAGES["low_resolution"]`) lo aclara explícitamente
  ("Si tu dispositivo no permite una foto de mayor calidad, el resultado
  puede no ser preciso"), en vez de simplemente decir "sacá otra foto"
  como en el resto de señales.

### 3. Reflejos / glare

- **Métrica**: máscara de píxeles con brillo `>= GI_OCR_QUALITY_GLARE_BRIGHT_THRESHOLD`
  (default `245.0`) sobre la imagen en escala de grises, componentes
  conexos (`cv2.connectedComponentsWithStats`, conectividad 8), y del
  componente más grande: `area_ratio` = área del componente / área total
  de la imagen, `bbox_ratio` = área del bounding box del componente / área
  total.
- **Distinción compacto vs. difuso (evita el falso positivo del criterio
  8)**: si `bbox_ratio > GI_OCR_QUALITY_GLARE_MAX_BBOX_RATIO` (default
  `0.5`), el brillo está demasiado disperso por todo el frame para ser un
  reflejo puntual (por ejemplo, un fondo de papel blanco brillante y
  uniforme) — se considera `ok` para esta señal específica. Ese caso lo
  cubre, si corresponde, la señal de "mala iluminación" (que sí mira el
  brillo global/difuso, criterio 12), no esta.
- **Umbrales por defecto**: `GI_OCR_QUALITY_GLARE_AREA_WARN_ABOVE=0.02`
  (2 % del frame), `GI_OCR_QUALITY_GLARE_AREA_REJECT_ABOVE=0.06` (6 %).
  Solo se aplican si el componente es "compacto" (no descartado por
  `bbox_ratio`).
- **Justificación**: un reflejo que cubre más del 6 % del frame en una
  zona compacta tiene alta probabilidad de tapar texto relevante (número
  de cliente, importe); 2 % es el piso de advertencia temprana.

### 4. Sombras / iluminación desigual

- **Métrica**: la imagen en escala de grises se divide en una grilla 4x4;
  se calcula el brillo medio de cada uno de los 16 bloques; la métrica es
  `max(brillo_bloques) - min(brillo_bloques)`.
- **Umbrales por defecto**: `GI_OCR_QUALITY_SHADOW_DIFF_WARN_ABOVE=45.0`,
  `GI_OCR_QUALITY_SHADOW_DIFF_REJECT_ABOVE=80.0` (escala 0-255).
- **Distinción frente a "mala iluminación" (evita el falso positivo del
  criterio 9)**: esta señal mira **varianza entre regiones**, no el nivel
  absoluto de brillo global. Una imagen uniformemente oscura (sin
  variación entre bloques) da una diferencia baja aquí (`ok`) y dispara,
  en cambio, la señal de "mala iluminación" (criterio 12). Verificado por
  test (`test_shadow_does_not_fire_for_uniformly_dark_image`).

### 5. Documento cortado (fuera de encuadre)

- **Heurística**: reutiliza `image_prep.largest_contour_bounding_box`
  (bounding box del contorno de bordes —`cv2.Canny` + `cv2.findContours`—
  con **mayor extensión espacial**, no necesariamente cerrado en un
  cuadrilátero). Si el bounding box cubre al menos
  `GI_OCR_QUALITY_CUT_MIN_AREA_RATIO` (default `0.15`, 15 %) del área
  total, se evalúa si toca o cruza el borde del frame en **más de un
  lado**, con un margen de tolerancia
  `GI_OCR_QUALITY_EDGE_TOUCH_MARGIN_RATIO` (default `0.015`, 1.5 % del
  ancho/alto). Si toca 2 o más lados → `reject`. Esta señal es binaria
  (`ok`/`reject`, sin nivel `warn` intermedio): un documento cortado no es
  ambiguo, o está completo o no lo está.
- **Por qué bounding box y no el cuadrilátero cerrado de
  `find_document_contour`**: un documento que se sale del encuadre produce
  un contorno de bordes *abierto* (no hay gradiente detectable exactamente
  en el límite del frame, ver más abajo "Por qué `find_document_contour`
  no detecta documentos cortados"), cuya área **encerrada**
  (`cv2.contourArea`) es casi nula — es apenas el trazo del borde visible,
  no el interior del documento. Por eso
  `image_prep.largest_contour_bounding_box` ordena los contornos
  candidatos por área de **bounding box** (`w * h`), no por área
  encerrada: así el contorno abierto del documento (que sí tiene un
  bounding box grande, aunque encierre poca área) no pierde frente a un
  trazo de texto pequeño pero cerrado (por ejemplo, el interior de una
  "0" o una "8" en el texto del comprobante).
- **Tolerancia de margen documentada explícitamente (evita el falso
  positivo del criterio 10)**: un documento que llena legítimamente casi
  todo el frame, sin quedar cortado (borde del documento cerca del borde
  de la imagen pero sin tocarlo), no debe confundirse con "cortado". El
  margen (`EDGE_TOUCH_MARGIN_RATIO`, 1.5 %) da ese colchón: solo se
  considera "toca el borde" cuando el bounding box llega a menos de ese
  margen del límite real del frame.
- **Por qué requiere `>= 2` lados tocados, no 1**: un documento
  correctamente encuadrado que llena el frame en una sola dirección (por
  ejemplo, ocupa todo el ancho pero tiene margen arriba/abajo) puede tocar
  o casi tocar un solo lado sin estar cortado. Tocar 2+ lados es una señal
  mucho más específica de que el documento efectivamente se sale del
  cuadro por más de un costado.

#### Por qué `find_document_contour` no detecta documentos cortados

Este es el detalle técnico central para entender por qué la señal de corte
usa una función distinta a la de perspectiva/encuadre. Cuando un
documento claro sobre fondo oscuro se sale del frame por un lado (por
ejemplo, por la izquierda), Canny detecta gradiente en los tres bordes
visibles (arriba, derecha, abajo) pero **no** en el borde que coincide
exactamente con el límite del array de píxeles: no hay "columna -1" contra
la cual calcular un gradiente horizontal en `x=0`, así que ese lado nunca
aparece como línea de borde. El resultado es un contorno de bordes
**abierto** (forma de "U" o "C", no un lazo cerrado). `cv2.findContours`
sobre ese trazo delgado y abierto calcula, vía la fórmula del shoelace, un
área encerrada minúscula (aproximadamente `perímetro × grosor_del_trazo`),
muy por debajo de cualquier umbral razonable de `min_area_ratio` — y
`cv2.approxPolyDP` tampoco lo reduce a un cuadrilátero de 4 lados limpio.
Por diseño, entonces, `find_document_contour(...)` devuelve `None` para un
documento cortado, **sin necesidad de ningún caso especial en el código**:
es una consecuencia natural de cómo Canny + findContours tratan una forma
abierta.

### 6. Mala perspectiva

- **Heurística**: a partir del **mismo** cuadrilátero devuelto por
  `image_prep.find_document_contour` (reutilizado, no reimplementado; ver
  más abajo "Reutilización de la detección de contorno"), se calculan los
  4 lados del cuadrilátero ordenado `(tl, tr, br, bl)`: `top = |tr-tl|`,
  `bottom = |br-bl|`, `left = |bl-tl|`, `right = |br-tr|`. La métrica es
  `max(top/bottom, bottom/top, left/right, right/left)` — la mayor
  desviación entre lados opuestos que deberían ser iguales si el
  documento estuviera fotografiado de frente sobre un plano paralelo a la
  cámara.
- **Umbrales por defecto**: `GI_OCR_QUALITY_PERSPECTIVE_RATIO_WARN_ABOVE=1.25`,
  `GI_OCR_QUALITY_PERSPECTIVE_RATIO_REJECT_ABOVE=1.6`. Un ratio de `1.0`
  es un rectángulo perfecto; `1.6` significa que un lado mide un 60 % más
  que su opuesto, una deformación de perspectiva ya severa.
- **Deduplicación de causa raíz con "documento cortado" (caso borde
  explícito del spec, criterio 11)**: si `find_document_contour` devuelve
  `None` (no se encontró un cuadrilátero de 4 lados claro — lo más común
  cuando el documento está cortado, ver la explicación técnica arriba),
  esta señal devuelve `(None, None)` — **no evaluable**, sin agregar
  ninguna razón. No hay ningún `if` especial para "si ya se reportó
  corte, no reportar perspectiva": simplemente, sin cuadrilátero no hay
  con qué medir deformación, así que la señal queda muda por construcción.
  Esto evita reportar dos razones independientes ("documento cortado" +
  "mala perspectiva") por la misma causa raíz (contorno no detectado).
  Verificado por test
  (`test_cut_document_deduplicates_perspective_reason`).

### 7. Mala iluminación (sub/sobreexpuesta)

- **Métrica**: brillo medio global (`gray.mean()`) de la imagen completa
  en escala de grises.
- **Umbrales por defecto**:
  `GI_OCR_QUALITY_BRIGHTNESS_DARK_REJECT_BELOW=40.0`,
  `GI_OCR_QUALITY_BRIGHTNESS_DARK_WARN_BELOW=70.0`,
  `GI_OCR_QUALITY_BRIGHTNESS_BRIGHT_WARN_ABOVE=250.0`,
  `GI_OCR_QUALITY_BRIGHTNESS_BRIGHT_REJECT_ABOVE=254.5`.
- **Justificación del umbral oscuro**: por debajo de brillo medio 40 (de
  255), en la práctica el texto ya no es legible ni para un humano; 70 es
  el piso de advertencia.
- **Justificación del umbral claro, deliberadamente muy cerca del techo
  (254.5 de 255)**: este es el punto de calibración más delicado de toda
  la feature. Los comprobantes de este proyecto (tanto fixtures sintéticas
  como el comprobante real usado en tests,
  `backend/tests/fixtures/gas_sample.jpg`) son, por convención, imágenes
  de **fondo blanco/muy claro con texto oscuro disperso**: el brillo medio
  global de un documento de este tipo ya está naturalmente muy cerca de
  255 (por ejemplo, `gas_sample.jpg` mide `~254.1` de brillo medio, sin
  estar sobreexpuesto ni tener ningún problema real). Un umbral de
  "sobreexpuesta" más conservador (por ejemplo, `>240`) generaría falsos
  positivos sistemáticos contra el estilo de documento que este propio
  proyecto usa como referencia — literalmente rechazaría por calidad el
  comprobante de ejemplo del repo. Por eso el umbral de `reject` se fijó
  apenas por encima de ese piso empírico (`254.5`), de forma que solo
  dispare para imágenes verdaderamente "lavadas" (mean muy próximo a 255,
  con texto ya invisible). Es una limitación reconocida de usar el brillo
  medio *global* como métrica única (ver "Riesgo de calibración" más
  abajo): esta señal, con estos valores por defecto, es efectivamente poco
  sensible para detectar sobreexposición sobre documentos de fondo claro
  con densidad de texto baja — solo atrapa los casos más extremos.
- **Distinción frente a "reflejos" y "sombras" (evita los falsos positivos
  de los criterios 8 y 9)**: esta señal solo mira el nivel medio global,
  sin importar si el brillo está concentrado (glare) o disperso de forma
  desigual (sombras) — esas dos situaciones las cubren señales aparte.

### 8. Encuadre insuficiente

- **Métrica**: área del cuadrilátero devuelto por
  `image_prep.find_document_contour` (mismo cuadrilátero que la señal de
  perspectiva, con un umbral de detección relajado,
  `GI_OCR_QUALITY_CONTOUR_MIN_AREA_RATIO=0.01`, para poder detectar
  también documentos que ocupan una fracción pequeña del frame) dividida
  por el área total de la imagen.
- **Umbral por defecto**: `GI_OCR_QUALITY_FRAME_FILL_WARN_BELOW=0.35`
  (35 % del frame). Por debajo de ese umbral → `warn`.
- **Techo `warn`, nunca `reject` (regla explícita del spec, criterio
  13)**: un documento que no llena bien el frame pero por lo demás es
  nítido, bien iluminado y no está cortado sigue siendo procesable (con
  posible pérdida de resolución efectiva de la región de interés). Esta
  señal jamás agrega una razón con severidad `reject` — el código de
  `_framing_signal` solo puede devolver `"warn"` u `"ok"`, nunca
  `"reject"`.
- **Degradación sin inventar datos (evita el falso positivo del criterio
  13)**: si `find_document_contour` no detecta ningún cuadrilátero claro
  (por ejemplo, fondo muy uniforme donde el documento es indistinguible),
  esta señal devuelve `(None, None)` — no evaluable, sin afectar el
  veredicto agregado por esta señal específica; las demás señales (blur,
  iluminación, etc.) siguen aplicando igual. Verificado por test
  (`test_framing_degrades_gracefully_without_document_contour`).

## Reutilización de la detección de contorno (no duplicación)

`image_prep.correct_perspective` ya implementaba, antes de esta feature,
la detección del contorno más grande de un documento vía `cv2.Canny` +
`cv2.findContours` + `cv2.approxPolyDP`. Esta feature **extrajo** esa
lógica a dos funciones reutilizables en `image_prep.py` en vez de
duplicarla dentro de `quality_gate.py`:

- `image_prep._document_edge_contours(image_np)`: contornos crudos (sin
  ordenar ni filtrar) sobre el mapa de bordes Canny de la imagen — base
  compartida.
- `image_prep.find_document_contour(image_np, min_area_ratio) ->
  Optional[np.ndarray]`: ordena los contornos candidatos por **área
  encerrada** (`cv2.contourArea`, mayor primero) y devuelve el primer
  cuadrilátero de 4 lados (`cv2.approxPolyDP`) cuya área supere
  `min_area_ratio` del total, ya ordenado `(tl, tr, br, bl)`. Usada por:
  - `correct_perspective` (umbral histórico `0.3`, **sin cambio de
    comportamiento** respecto a antes de esta feature — mismo resultado
    para la misma imagen).
  - `quality_gate._document_geometry` (umbral relajado, `0.01` por
    defecto) para las señales de "mala perspectiva" y "encuadre
    insuficiente".
- `image_prep.largest_contour_bounding_box(image_np) ->
  Optional[Tuple[int,int,int,int]]`: ordena los mismos contornos crudos
  por **área de bounding box** (`w * h`, no área encerrada) y devuelve el
  bounding box del más grande, sin exigir que cierre en un cuadrilátero.
  Usada exclusivamente por la señal de "documento cortado" (ver el detalle
  técnico de por qué en la sección de esa señal, arriba).

`correct_perspective` quedó reescrita para llamar a
`find_document_contour(img, min_area_ratio=0.3)` en vez de tener su propia
copia del bucle Canny/findContours/approxPolyDP; se verificó por test
(`backend/tests/test_image_prep.py`, sin cambios) que el comportamiento es
idéntico al de antes de esta feature.

## Estado de job nuevo: `needs_new_photo`

`backend/app/job_queue.py::JobQueue._process` — antes de esta feature, el
flujo era `queued → processing → ready | failed`. Con esta feature:

```
queued → processing → ready | needs_new_photo | failed
```

- **Nombre elegido**: `needs_new_photo` (constante
  `quality_gate.REJECTED_JOB_STATUS`, importada en `job_queue.py`). Se
  prefirió sobre alternativas como `rejected_quality` o `quality_rejected`
  porque describe la **acción que el usuario debe tomar** (sacar una foto
  nueva), coherente con el resto de estados del sistema que describen
  situación/acción sobre el job (`queued`, `processing`, `ready`,
  `confirmed`, `failed`), y es el texto que efectivamente se muestra en el
  frontend.
- **Cuándo se asigna**: `job_queue.py::_process`, después de llamar a
  `capture_pipeline.process_document`, inspecciona
  `result["processing_metadata"]["quality_gate"]["verdict"]`. Si es
  `"reject"`, el job pasa a `needs_new_photo` (en vez de `"ready"`).
- **No se llama `store.save_original`** en este camino — igual que en el
  camino `failed` existente. Esto es lo que garantiza, sin código
  adicional en `main.py`, que:
  - `POST /api/v1/jobs/{job_id}/confirm` siga devolviendo `404` (vía
    `store.original_exists(job_id)`, que depende únicamente de si existe
    el archivo `jobs/{id}.json` escrito por `save_original`) — criterio 18
    del spec.
  - `GET /api/v1/jobs/{job_id}/download` y `/original` también sigan dando
    404/409 sin cambios de código.
- **`retry` sigue funcionando sin cambios de código** — criterio 19 del
  spec. `JobQueue.retry()` solo bloquea los estados `"ready"` y
  `"confirmed"`:
  ```python
  if job["status"] in ("ready", "confirmed"):
      return False
  ```
  `"needs_new_photo"` no está en esa tupla, así que `retry()` reencola el
  job normalmente (`status = "queued"`, se reprocesa el mismo archivo).
  Como `quality_gate.evaluate` es una función pura y determinística sobre
  los mismos píxeles de entrada (sin aleatoriedad, sin estado global), un
  reintento sobre el mismo archivo produce **el mismo veredicto y las
  mismas razones**, verificado por test
  (`test_job_queue_retry_on_rejected_job_is_deterministic`,
  `test_api_retry_on_rejected_job_returns_200_and_requeues`).

## Umbrales configurables por variable de entorno

Igual patrón que `upload_validation.max_upload_bytes`
(`GI_OCR_MAX_UPLOAD_BYTES`): cada umbral se lee de una variable de entorno
en cada llamada (no se cachea al importar el módulo), con un default
razonable si la variable no está definida, está vacía o no es un `float`
válido. Los umbrales son **globales al sistema**, no configuración por
servicio en `backend/config/services.ini`: el chequeo de calidad corre
**antes** de que se clasifique el proveedor/servicio del documento (esa
clasificación ocurre dentro del propio OCR, en
`capture_pipeline.process_image`), así que no hay forma de tener un umbral
"por servicio" sin invertir el orden del pipeline — decisión ya declarada
explícitamente como riesgo/supuesto en `runs/06-calidad-captura-mobile/
spec.md` y no objetada por la auditoría (`audit-1.md`).

| Variable | Default | Señal |
|---|---|---|
| `GI_OCR_QUALITY_BLUR_REJECT_BELOW` | `40.0` | Blur |
| `GI_OCR_QUALITY_BLUR_WARN_BELOW` | `100.0` | Blur |
| `GI_OCR_QUALITY_MIN_SIDE_REJECT_BELOW` | `500.0` | Baja resolución |
| `GI_OCR_QUALITY_MIN_SIDE_WARN_BELOW` | `900.0` | Baja resolución |
| `GI_OCR_QUALITY_GLARE_BRIGHT_THRESHOLD` | `245.0` | Reflejos |
| `GI_OCR_QUALITY_GLARE_AREA_WARN_ABOVE` | `0.02` | Reflejos |
| `GI_OCR_QUALITY_GLARE_AREA_REJECT_ABOVE` | `0.06` | Reflejos |
| `GI_OCR_QUALITY_GLARE_MAX_BBOX_RATIO` | `0.5` | Reflejos (compacidad) |
| `GI_OCR_QUALITY_SHADOW_DIFF_WARN_ABOVE` | `45.0` | Sombras |
| `GI_OCR_QUALITY_SHADOW_DIFF_REJECT_ABOVE` | `80.0` | Sombras |
| `GI_OCR_QUALITY_BRIGHTNESS_DARK_REJECT_BELOW` | `40.0` | Mala iluminación |
| `GI_OCR_QUALITY_BRIGHTNESS_DARK_WARN_BELOW` | `70.0` | Mala iluminación |
| `GI_OCR_QUALITY_BRIGHTNESS_BRIGHT_WARN_ABOVE` | `250.0` | Mala iluminación |
| `GI_OCR_QUALITY_BRIGHTNESS_BRIGHT_REJECT_ABOVE` | `254.5` | Mala iluminación |
| `GI_OCR_QUALITY_EDGE_TOUCH_MARGIN_RATIO` | `0.015` | Documento cortado |
| `GI_OCR_QUALITY_CUT_MIN_AREA_RATIO` | `0.15` | Documento cortado |
| `GI_OCR_QUALITY_CONTOUR_MIN_AREA_RATIO` | `0.01` | Perspectiva / encuadre (detección de contorno) |
| `GI_OCR_QUALITY_PERSPECTIVE_RATIO_WARN_ABOVE` | `1.25` | Mala perspectiva |
| `GI_OCR_QUALITY_PERSPECTIVE_RATIO_REJECT_ABOVE` | `1.6` | Mala perspectiva |
| `GI_OCR_QUALITY_FRAME_FILL_WARN_BELOW` | `0.35` | Encuadre insuficiente |

## Riesgo de calibración conocido (no bloqueante, a revisar post-despliegue)

Todos los valores por defecto de la tabla anterior se calibraron
empíricamente contra **fixtures 100% sintéticas** (rectángulos, texto
dibujado con PIL, transformaciones OpenCV controladas —
`cv2.GaussianBlur`, `cv2.warpPerspective`, desplazamientos de brillo
aditivos/multiplicativos), siguiendo la política de este repo de no
versionar comprobantes reales ni derivarlos de `storage_bridge/`. Es un
riesgo conocido y explícitamente reconocido (señalado también por la
auditoría, `runs/06-calidad-captura-mobile/audit-1.md`): estos umbrales
**no** están calibrados contra un corpus de fotos reales de celular
(variedad real de cámaras, condiciones de luz, tipos de papel, reflejos de
plástico/vidrio). Quedan como candidatos razonables de partida, no como
valores definitivos. Se recomienda revisar/recalibrar contra datos reales
una vez que el flujo esté en uso, ajustando las variables de entorno de la
tabla sin necesidad de cambios de código. Ver también
`runs/06-calidad-captura-mobile/decision.md`.

## Casos borde cubiertos (y dónde)

Todos verificados por test en `backend/tests/test_quality_gate.py`:

- Señales simultáneas en `reject` (documento cortado + baja resolución):
  el veredicto agregado es `reject` una sola vez, con **todas** las
  razones listadas (`test_verdict_worst_subverdict_wins_with_all_reasons_listed`).
- Severidad mixta (una señal en `warn`, otra en `reject`): el agregado es
  `reject`, pero ambas razones quedan listadas
  (`test_verdict_mixed_severity_reject_wins_but_both_listed`).
- Deduplicación de causa raíz entre "documento cortado" y "mala
  perspectiva" (`test_cut_document_deduplicates_perspective_reason`).
- Imagen muy pequeña **además de** con documento cortado: ambas señales
  se disparan de forma independiente y legítima, sin que una suprima a la
  otra (mismo test de "señales simultáneas" arriba).
- Identificador de razón estable para "baja resolución por limitación real
  del dispositivo" (`test_low_resolution_reason_identifier_is_stable_and_distinguishable`).
- PDF cargado como documento: no pasa por este chequeo (mismo patrón que
  `apply_exif_orientation`, ver `docs/tecnica/correccion-orientacion-exif.md`,
  "Fuera de alcance") — `test_pdf_path_bypasses_quality_gate`, con spy
  sobre `quality_gate.evaluate` verificando que no se invoca.
- Imagen con contenido degenerado (todo negro, todo blanco, `1x1` px): no
  lanza excepción, degrada a `reject` con razones claras
  (`test_degenerate_all_black_image_does_not_raise_and_rejects`,
  `test_degenerate_all_white_image_does_not_raise_and_rejects`,
  `test_degenerate_1x1_image_does_not_raise`).
- Imagen ilegible/corrupta que pasó la validación de firma pero falla al
  abrirse con Pillow: se trata como error de procesamiento (`status ==
  "failed"`, camino de excepción ya existente en `JobQueue._process`), no
  como rechazo de calidad — son conceptualmente distintos
  (`test_process_document_corrupt_file_raises_not_quality_reject`).
- Reintento (`retry`) de un job rechazado por calidad: mismo veredicto,
  determinístico, ni excepción ni resultado distinto por azar
  (`test_evaluate_is_deterministic`,
  `test_job_queue_retry_on_rejected_job_is_deterministic`,
  `test_api_retry_on_rejected_job_returns_200_and_requeues`).
- Umbrales configurables por variable de entorno, con fallback a default
  ante valor ausente/inválido (`test_threshold_overridable_by_env_var`,
  `test_threshold_invalid_env_var_falls_back_to_default`).
- Regresión: un job que sigue el pipeline normal (`ok`/`warn`) sigue
  llamando `store.save_original` como antes de esta feature
  (`test_job_queue_ready_job_still_calls_save_original`).
- Criterios 18/19 verificados también a nivel HTTP real (`TestClient`
  sobre `backend/app/main.py`):
  `test_api_job_rejected_by_quality_gate_returns_needs_new_photo_status`,
  `test_api_confirm_on_rejected_job_returns_404`,
  `test_api_retry_on_rejected_job_returns_200_and_requeues`.

## Ubicación del código

- `backend/app/quality_gate.py`: las 8 señales, el veredicto agregado
  (`evaluate`), los umbrales configurables y los mensajes por razón.
- `backend/app/image_prep.py`: `find_document_contour` y
  `largest_contour_bounding_box` (extraídas/refactorizadas desde
  `correct_perspective`, reutilizadas por `quality_gate.py`).
- `backend/app/capture_pipeline.py::process_document`: punto de
  integración; `_quality_rejected_result` (resultado mínimo sin OCR).
- `backend/app/job_queue.py::JobQueue._process`: estado nuevo
  `needs_new_photo`.
- `frontend/src/app.js`, `frontend/src/style.css`: `renderNeedsNewPhoto`
  (estado nuevo, mismo patrón visual `pill`/`error-box` que `failed`),
  aviso `warn-box` dentro de `renderReady`, contador `stat-quality` en el
  dashboard.
- `backend/tests/test_quality_gate.py`: cobertura de tests.
