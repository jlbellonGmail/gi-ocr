# Spec: Calidad de captura mobile (control de calidad previo al OCR)

## Alcance

Incluye:

- Un chequeo de calidad de imagen que corre **antes** de invocar el motor
  OCR (`ocr_engine`), sobre la imagen ya orientada por EXIF
  (`image_prep.apply_exif_orientation`) pero antes de `image_prep.prepare`
  (deskew/perspectiva/escala) y antes de `capture_pipeline.process_image`.
- Detección de 8 señales de calidad de captura declaradas en el backlog
  (`ROADMAP.md`, ítem `06`): blur/desenfoque, baja resolución, reflejos,
  sombras, documento cortado (fuera de encuadre), mala perspectiva, mala
  iluminación, encuadre insuficiente (documento no llena el cuadro).
- Un veredicto de tres niveles (`ok` / `warn` / `reject`) con razones
  explícitas por señal, aplicado de forma **genérica** (antes de saber a
  qué servicio/proveedor pertenece el documento — la clasificación de
  proveedor ocurre después, dentro del OCR).
- Extensión del contrato de `capture_pipeline.process_document` /
  `JobQueue._process` para que un veredicto `reject` no invoque OCR y deje
  el job en un estado distinto de `ready`/`failed`, con mensaje específico
  de qué está mal.
- Extensión del contrato de `capture_pipeline.process_document` para que
  un veredicto `warn` sí procese normalmente pero agregue la información
  de calidad al resultado (`processing_metadata`), de forma que la UI de
  revisión pueda mostrar una advertencia de posible baja confianza.
- Cambios mínimos de frontend (`frontend/src/app.js`, `frontend/src/
  style.css`) para mostrar: (a) el estado de "nueva foto requerida" con
  las razones concretas, siguiendo el mismo patrón visual que el estado
  `failed` existente (`pill`/`error-box`), y (b) un aviso de advertencia
  visible dentro de la vista de revisión (`renderReady`) cuando el
  resultado trae `quality_gate.verdict === "warn"`.
- Documentación técnica y de usuario, y los enlaces de índice
  correspondientes.
- Tests automatizados con fixtures sintéticas (no comprobantes reales)
  para cada señal.

Explícitamente NO incluye:

- Reemplazar, reentrenar o cambiar el motor OCR (ADR-006, sin cambios) ni
  el two-pass ROI existente.
- Cambiar el formato `.DATA`/`services.ini` (ADR-007, sin cambios): los
  umbrales de esta feature son **globales**, no de configuración por
  servicio (ver "Riesgos / supuestos").
- Trazabilidad formal de todas las transformaciones de imagen aplicadas
  (versión original vs. preparada, manifest de transformaciones): eso es
  `07-preprocesamiento-documental-no-destructivo`, todavía no iniciada.
  Esta feature solo agrega el *chequeo* de calidad, no una reformulación
  del pipeline de preparación de imagen.
- Scoring de confianza de campos extraídos ni enrutamiento a revisión
  humana basado en esa confianza: eso es `09-confianza-y-enrutamiento-
  hitl`. Esta feature solo cubre calidad de la **captura** (imagen cruda),
  no confianza de la **extracción**.
- Corrección automática de la imagen para arreglar los problemas
  detectados (por ejemplo, deshacer sombras o reflejos). Solo se
  detecta y se decide (`ok`/`warn`/`reject`); la corrección activa de
  perspectiva/deskew/escala ya existe en `image_prep.py` y no cambia.
- Reintento automático de captura (por ejemplo, disparar la cámara de
  nuevo): el frontend solo informa al usuario, quien decide volver a subir
  o capturar.
- Nueva dependencia externa de visión por computadora: se usa
  `opencv-python-headless` (ya declarada en `backend/requirements.txt`),
  igual que `image_prep.py`.

## Contexto

El pipeline actual (`backend/app/capture_pipeline.py::process_document`)
abre la imagen, corrige orientación EXIF, la prepara (`image_prep.
prepare`: heurística de orientación, deskew, escala) y recién ahí corre
OCR two-pass ROI-focalizada (`ocr_engine`, ADR-006) y extracción/
validación semántica. `docs/tecnica/correccion-orientacion-exif.md`
("Fuera de alcance") declara explícitamente que el control de calidad de
captura (blur, baja resolución, mala iluminación) es esta feature, `06`,
no la `05`.

El caso de uso real es un frontend mobile-first (`frontend/`) donde el
usuario fotografía un comprobante rápido, muchas veces con mala luz,
encuadre apurado o superficies reflectantes (plástico, vidrio). Sin un
filtro previo:

- Se gasta cómputo OCR (RapidOCR/ONNX, ~2.35–2.57s/documento medido en
  `01-captura-ocr-local-agil`) en fotos que no tienen ninguna chance de
  producir campos útiles (documento cortado a la mitad, negro/blanco casi
  puro).
- El usuario recibe recién en la pantalla de revisión (`job` en estado
  `ready` con `missing_fields` lleno) la señal de que algo salió mal, en
  vez de en el momento de la captura, cuando todavía tiene el documento a
  mano para repetir la foto.

Esta feature agrega ese filtro previo, sincrónico (corre dentro del mismo
`run_in_executor` que ya ejecuta `process_document` en `JobQueue._process`,
sin bloquear el loop de eventos ni requerir infraestructura nueva), y
define los tres umbrales de decisión pedidos por el ítem `06` del
`ROADMAP.md`: procesar directo, advertir, o pedir nueva foto.

Encaja en el pipeline así: **captura (frontend) → upload/validación de
archivo (`upload_validation.py`, sin cambios) → cola (`job_queue.py`) →
`capture_pipeline.process_document` → [NUEVO: control de calidad] →
`image_prep.prepare` → OCR (`ocr_engine`) → extracción/validación
semántica → reporte de campos → revisión humana (`review_service.py`)**.
El control de calidad se ubica **antes** de `image_prep.prepare` y de OCR,
después de la corrección EXIF (para no penalizar como "mala perspectiva"
o "documento cortado" una foto que solo estaba rotada por metadata).

## Criterios de aceptación

### Generales (obligatorios en todo spec)

1. Debe existir `docs/tecnica/calidad-captura-mobile.md`, no vacío, con el
   algoritmo/heurística usada para cada una de las 8 señales, los tres
   umbrales de decisión y las decisiones de diseño relevantes.
2. Debe existir `docs/usuario/calidad-captura-mobile.md`, no vacío, con el
   propósito del flujo y al menos un ejemplo de uso HTTP completo
   (request + response) para cada uno de los tres veredictos (`ok`,
   `warn`, `reject`).
3. Debe existir `runs/06-calidad-captura-mobile/decision.md`, con
   decisiones demostrables desde spec/auditoría/implementación (no
   ornamental).
4. Debe existir un enlace exacto a `calidad-captura-mobile.md` agregado en
   `docs/tecnica/index.md`.
5. Debe existir un enlace exacto a `calidad-captura-mobile.md` agregado en
   `docs/usuario/index.md`.

### Específicos de detección de calidad (regla de dominio OCR)

Por cada señal, el criterio de aceptación exige declarar explícitamente:
señal detectada, tipo de imagen/fixture usada, salida esperada,
verificación aplicada y falso positivo evitado. Los ocho:

6. **Blur/desenfoque**: métrica = varianza del Laplaciano
   (`cv2.Laplacian(gray, cv2.CV_64F).var()`) sobre la imagen en escala de
   grises. Fixture: imagen sintética con texto nítido (ver
   `backend/tests/fixtures/gas_sample.jpg` o equivalente generado en
   memoria) vs. la misma imagen con `cv2.GaussianBlur` aplicado con kernel
   grande. Salida esperada: la versión nítida obtiene veredicto de señal
   `ok` para blur; la versión con blur fuerte obtiene `reject` (varianza
   por debajo del umbral reject) y la versión con blur leve obtiene `warn`
   (varianza entre el umbral warn y el umbral reject). Falso positivo
   evitado: una imagen nítida pero con fondo uniforme (poco detalle, ej.
   documento sobre superficie lisa) no debe confundirse con blur — el test
   debe usar una imagen con suficiente densidad de texto/bordes para que
   la métrica sea representativa, documentando esa limitación conocida en
   `docs/tecnica/calidad-captura-mobile.md`.
7. **Baja resolución**: métrica = lado menor de la imagen en píxeles
   (`min(height, width)`) sobre la imagen tal como llega (antes de
   `normalize_scale`, que reduce a 1600px el lado mayor pero no sube
   resolución). Fixture: imagen sintética de 300x400px (reject esperado) y
   una de 1200x1600px (ok esperado). Salida esperada: verificar que el
   veredicto de la señal cambia según el umbral. Falso positivo evitado:
   no penalizar imágenes que ya vienen escaladas por el propio pipeline
   (el chequeo corre sobre la imagen original recién cargada, no sobre una
   copia ya reducida por `normalize_scale`).
8. **Reflejos (glare)**: métrica = proporción de píxeles con brillo
   cercano a saturación (`gray > 245`, aprox.) agrupados en una región
   contigua significativa (`cv2.connectedComponentsWithStats` sobre la
   máscara de umbral, área del componente más grande / área total de la
   imagen). Fixture: imagen sintética con un óvalo/rectángulo blanco puro
   superpuesto sobre el texto simulando reflejo de luz. Salida esperada:
   la imagen sin el óvalo da `ok`, la imagen con el óvalo cubriendo una
   zona relevante da `warn` o `reject` según el área cubierta. Falso
   positivo evitado: un fondo de papel blanco brillante pero uniforme
   (sin texto oculto) no debe disparar `reject` solo por brillo alto y
   difuso — se exige que el brillo esté concentrado en un componente
   conexo relativamente pequeño y compacto (no todo el frame), documentado
   como distinción explícita frente a la señal de "mala iluminación"
   (criterio 11, que sí mira el brillo global/difuso).
9. **Sombras / iluminación desigual**: métrica = comparación de brillo
   medio entre bloques de una grilla (ej. 4x4) sobre la imagen en escala
   de grises; diferencia entre el bloque más oscuro y el más claro por
   encima de un umbral indica iluminación desigual. Fixture: imagen
   sintética con brillo uniforme vs. una con un gradiente de oscurecimiento
   aplicado a una mitad (simulando sombra de mano/cuerpo). Salida
   esperada: la uniforme da `ok`; la del gradiente marcado da `warn`/
   `reject` según la magnitud. Falso positivo evitado: distinguir de la
   señal de "mala iluminación" (criterio 11): esta señal mira **varianza**
   entre regiones, no el nivel absoluto de brillo global; una imagen
   uniformemente oscura no debe disparar esta señal (dispara la otra).
10. **Documento cortado (fuera de encuadre)**: heurística = detección del
    contorno más grande por bordes (`cv2.Canny` + `cv2.findContours`,
    mismo enfoque que ya usa `image_prep.correct_perspective` para
    detectar el borde del documento) y verificación de si el contorno
    principal toca o cruza el borde del frame en más de un lado con área
    significativa. Fixture: imagen sintética con el "documento" (rectángulo
    con texto) completo dentro del frame vs. una donde el rectángulo se
    corta contra uno o más bordes de la imagen. Salida esperada: la
    completa da `ok`, la cortada da `reject`. Falso positivo evitado: un
    documento que llena legítimamente casi todo el frame sin quedar
    cortado (borde del documento cerca del borde de la imagen pero sin
    tocarlo) no debe confundirse con "cortado" — se exige tolerancia de
    margen documentada explícitamente en `docs/tecnica/
    calidad-captura-mobile.md`.
11. **Mala perspectiva**: heurística = a partir del mismo contorno
    detectado en el criterio 10, evaluar qué tan lejos está el
    cuadrilátero aproximado (`cv2.approxPolyDP`) de un rectángulo (relación
    entre lados opuestos, ángulos entre lados adyacentes respecto de 90°).
    Fixture: imagen sintética del documento fotografiado "de frente"
    (rectángulo regular) vs. una con transformación de perspectiva
    (`cv2.warpPerspective`) aplicada simulando ángulo pronunciado. Salida
    esperada: la de frente da `ok`, la con perspectiva marcada da `warn`/
    `reject` según la magnitud de la deformación. Falso positivo evitado:
    no confundir con "documento cortado" (criterio 10) — si no se
    encuentra un cuadrilátero de 4 lados claro (por ejemplo porque el
    documento está cortado), esta señal no debe evaluarse como "perspectiva
    mala", sino que cede el resultado a la señal de corte, evitando doble
    penalización redundante por la misma causa raíz (ver "Casos borde").
12. **Mala iluminación (subexpuesta o sobreexpuesta)**: métrica = brillo
    medio global de la imagen en escala de grises (histograma / media).
    Fixture: imagen sintética con brillo medio normal vs. una oscurecida
    (`* 0.15` de brillo) vs. una sobreexpuesta (`* 3` con clip). Salida
    esperada: la normal da `ok`; la oscura y la sobreexpuesta dan `warn`/
    `reject` según qué tan lejos del rango aceptable esté la media. Falso
    positivo evitado: distinguir de "reflejos" (criterio 8, brillo
    concentrado y compacto) y de "sombras" (criterio 9, varianza entre
    regiones) — esta señal solo mira el nivel medio global.
13. **Encuadre insuficiente (documento no llena el frame)**: métrica =
    proporción entre el área del contorno del documento detectado
    (criterio 10) y el área total de la imagen. Fixture: imagen sintética
    donde el "documento" ocupa la mayor parte del frame vs. una donde
    ocupa una fracción pequeña (mucho margen/fondo alrededor). Salida
    esperada: la que llena el frame da `ok`; la de encuadre insuficiente da
    `warn` (nunca `reject` directo por esta señal sola — ver "Riesgos /
    supuestos", encuadre insuficiente es recuperable con zoom digital antes
    de OCR y no amerita descartar la foto por sí sola). Falso positivo
    evitado: si no se detecta ningún contorno de documento claro (fondo
    muy uniforme con el documento indistinguible), esta señal no debe
    inventar un área — debe degradar a "no evaluable" sin afectar el
    veredicto agregado por esta señal específica, dejando que otras
    señales (blur, iluminación) sigan aplicando igual.

### Umbrales y semántica del veredicto

14. Cada señal produce un sub-veredicto individual (`ok`/`warn`/`reject`)
    contra dos umbrales configurables (ver "Riesgos / supuestos" sobre
    dónde vive esa configuración). El veredicto agregado (`quality_gate.
    verdict`) es el peor sub-veredicto entre todas las señales evaluables
    (`reject` > `warn` > `ok`), con la lista completa de razones que
    dispararon `reject` o `warn` (no solo la primera), verificable por
    test.
15. Veredicto `ok`: el documento sigue el pipeline normal
    (`image_prep.prepare` → OCR → extracción → validación) sin ningún dato
    de calidad adicional visible más allá de un bloque informativo neutro
    en `processing_metadata.quality_gate` (verificable: job resultante
    tiene `status == "ready"`, sin bandera de advertencia).
16. Veredicto `warn`: el documento sigue el pipeline normal igual que
    `ok` (no se bloquea ni se pide nueva foto), pero
    `processing_metadata.quality_gate.verdict == "warn"` con las razones
    específicas, y el job resultante debe permitir a la UI de revisión
    mostrar un aviso de "posible baja confianza en los resultados"
    (verificable: test de `capture_pipeline.process_document` sobre una
    fixture marginal, y test de frontend/lógica de render que confirme que
    el aviso aparece cuando `quality_gate.verdict == "warn"`).
17. Veredicto `reject`: el documento **no** se envía a OCR
    (`ocr_engine`/`process_image` no debe invocarse — verificable con
    mock/spy en test unitario). El job resultante debe quedar en un estado
    explícitamente distinto de `ready` y de `failed` (ver "Riesgos /
    supuestos" sobre el nombre exacto del estado nuevo), con un mensaje
    específico por cada razón de rechazo (ej. "El documento está cortado
    en el encuadre", "Hay un reflejo sobre parte del texto", "La foto está
    demasiado oscura para leerse"), consumible por el endpoint
    `GET /api/v1/jobs/{job_id}` y mostrado en el frontend con el mismo
    patrón visual que el estado `failed` existente.
18. El endpoint `POST /api/v1/jobs/{job_id}/confirm` debe seguir
    rechazando (404, comportamiento ya existente vía `store.
    original_exists`) la confirmación de un job en el nuevo estado de
    rechazo por calidad, porque no se generó resultado OCR que confirmar
    (verificable con test de integración).
19. El endpoint `POST /api/v1/jobs/{job_id}/retry` debe seguir
    funcionando sin lanzar excepción sobre un job en el nuevo estado de
    rechazo por calidad (reprocesa el mismo archivo, y debe volver a dar
    el mismo veredicto de forma determinística — verificable con test).

## Casos borde a contemplar

- Múltiples señales en `reject` simultáneamente (ej. documento cortado +
  mala iluminación): el veredicto agregado es `reject` una sola vez, con
  **todas** las razones listadas, no solo la primera encontrada.
- Señales con severidad mixta (una en `reject`, otra en `warn`): el
  agregado es `reject` (la peor gana), pero el listado de razones incluye
  ambas.
- Perspectiva mala **causada** por el mismo motivo que "documento
  cortado" (no se detecta cuadrilátero de 4 lados limpio): no se debe
  reportar como dos razones independientes cuando la causa raíz es la
  misma detección de contorno fallida; documentar en
  `docs/tecnica/calidad-captura-mobile.md` cómo se evita esa doble cuenta.
- Imagen muy pequeña además de con documento cortado: ambas señales
  (`baja resolución` + `documento cortado`) pueden dispararse juntas de
  forma independiente y legítima (no son la misma causa raíz); ambas
  razones deben listarse.
- Documento fotografiado correctamente pero con resolución baja por
  limitación real del dispositivo (celular viejo, cámara de baja
  resolución): esto no se puede corregir pidiendo "otra" foto (sería la
  misma resolución). El mensaje de rechazo/advertencia para esta señal
  específica debe ser distinguible del resto ("la imagen tiene poca
  resolución, si tu dispositivo no permite una foto de mayor calidad
  puede que el resultado no sea preciso") — a decidir el texto exacto en
  la implementación, pero el spec exige que el *identificador* de razón
  para esta señal sea estable y distinguible de las demás (verificable).
- PDF cargado como documento (`pdf_util`, camino `_process_pdf`): el
  control de calidad de esta feature aplica solo al camino de imagen
  (igual que `apply_exif_orientation`, ver `docs/tecnica/
  correccion-orientacion-exif.md`, "Fuera de alcance"). Un PDF renderizado
  con `pypdfium2` no pasa por este chequeo en esta iteración — declarado
  explícitamente como fuera de alcance, no ambigüedad silenciosa.
- Imagen con formato válido pero contenido degenerado (todo negro, todo
  blanco, 1x1 px re-escalado): no debe lanzar excepción; debe degradar a
  `reject` con una razón clara (ej. "iluminación" o "resolución" según
  corresponda), nunca un 500.
- Imagen ilegible/corrupta que pasó la validación de firma
  (`upload_validation.py`) pero falla al abrirse con Pillow/OpenCV dentro
  del chequeo de calidad: debe tratarse como error de procesamiento
  (`status == "failed"`, camino de excepción ya existente en
  `JobQueue._process`), no como rechazo de calidad — son conceptualmente
  distintos (archivo corrupto vs. foto de mala calidad pero válida).
- Reintento (`retry`) de un job rechazado por calidad sobre el mismo
  archivo: debe dar el mismo veredicto (determinístico), no una
  excepción ni un veredicto distinto por azar.
- Formato de imagen no soportado para el chequeo específico (por ejemplo,
  TIFF multi-página): el chequeo de calidad debe operar sobre la misma
  representación (`np.ndarray` RGB) que ya usa `image_prep`, sin agregar
  soporte de formato nuevo — si `Image.open` ya falla antes de esta
  feature, sigue fallando igual (camino de excepción, `status ==
  "failed"`), sin cambios de comportamiento respecto de eso.

## Riesgos / supuestos

- **Umbrales globales, no en `services.ini`**: el chequeo de calidad corre
  **antes** de la clasificación de proveedor (`process_image` clasifica
  el servicio/documento dentro del propio OCR), por lo tanto no se sabe a
  qué servicio pertenece la imagen en el momento del chequeo. Asumo que
  los umbrales de las 8 señales (y sus dos niveles `warn`/`reject` cada
  uno) son **globales al sistema**, configurables por variable de entorno
  con default razonable, siguiendo el mismo patrón ya usado en
  `upload_validation.max_upload_bytes` (`GI_OCR_MAX_UPLOAD_BYTES`), **no**
  agregados a `backend/config/services.ini` (que es config de extracción
  de campos por servicio, ADR-007, y no aplica a un chequeo que corre
  antes de saber el servicio). Si el reviewer prefiere umbrales por
  servicio a futuro, debe ser una decisión de arquitectura explícita
  aparte, no asumida acá.
- **Nombre del nuevo estado de job**: el spec exige un estado distinto de
  `ready`/`failed`/`queued`/`processing`/`confirmed` para el veredicto
  `reject`, pero no fija el string exacto (ej. `needs_new_photo` vs.
  `rejected_quality`) — decisión de implementación menor, siempre que sea
  estable, documentado en `docs/tecnica/calidad-captura-mobile.md` y
  reflejado en el frontend (`app.js`, filtros de estado en el dashboard,
  ej. `stat-queued`/`stat-ready`/`stat-failed`, que deberán contemplar
  este nuevo estado para no contarlo como "listo" ni omitirlo del
  resumen).
- **No se agrega dependencia nueva**: `opencv-python-headless` ya está en
  `backend/requirements.txt` y ya se usa en `image_prep.py` para
  operaciones equivalentes (Sobel, Canny, contornos, umbralado). No hace
  falta scikit-image, numpy adicional ni ninguna librería de "blur
  detection" de terceros.
- **Reutilización de la lógica de detección de contorno de documento**:
  `image_prep.correct_perspective` ya implementa detección del contorno
  más grande vía `cv2.Canny` + `cv2.findContours` + `cv2.approxPolyDP`.
  Esta feature necesita esa misma detección (o una extracción compartida
  de esa lógica) para las señales de "documento cortado", "mala
  perspectiva" y "encuadre insuficiente". Queda como decisión de
  implementación si se extrae una función común reutilizada por ambos
  módulos o se duplica de forma acotada — no se fuerza el diseño de
  código en el spec, pero se deja registrada la dependencia funcional
  para que el builder no la resuelva por sorpresa.
- **`encuadre insuficiente` nunca dispara `reject` por sí sola**: asumo
  que un documento que no llena bien el frame pero por lo demás es nítido,
  bien iluminado y no está cortado sigue siendo procesable (con posible
  pérdida de resolución efectiva de ROI), así que esta señal individual
  tiene techo `warn`, no `reject`. Si el reviewer considera que amerita
  `reject` en casos extremos (documento ocupando <10% del frame, por
  ejemplo), debe objetarlo explícitamente; documentado acá para que sea
  discutible.
- **El chequeo corre después de EXIF, antes de deskew/perspectiva/escala**:
  asumo que evaluar sobre la imagen ya orientada (pero sin deskew ni
  normalización de escala) da señales más representativas de "cómo la
  vio la cámara" que evaluar después de `image_prep.prepare` (que ya
  intenta corregir algunos de estos problemas). Este orden es coherente
  con el objetivo de "evitar gastar cómputo OCR", ya que el chequeo debe
  ocurrir antes de cualquier preparación cara, no después.
- **Alcance de frontend acotado**: el spec pide mostrar el veredicto
  `warn`/`reject` en la UI existente (`app.js`), reutilizando los mismos
  patrones visuales (`pill`, `error-box`) ya presentes para `failed`, sin
  rediseñar la UI de revisión. Cambios más profundos de UX de captura
  (por ejemplo, feedback de calidad en vivo mientras la cámara está
  abierta, antes de sacar la foto) quedan fuera de alcance — esta feature
  es un chequeo **post-captura, pre-OCR**, no un visor en vivo.
- **Fixtures sintéticas, no comprobantes reales**: siguiendo el patrón ya
  establecido (`backend/tests/fixtures/gas_sample.jpg`, generación en
  memoria en `test_image_prep.py`/`test_exif_orientation.py`), todas las
  fixtures de esta feature deben construirse sintéticamente (rectángulos,
  texto dibujado con PIL, transformaciones OpenCV controladas), nunca
  subir imágenes reales de comprobantes ni derivarlas de
  `storage_bridge/`.
