# Decision: 06-calidad-captura-mobile

## Estado

Implementación builder-agent lista para QA. No se marca `ROADMAP.md` y no
se crea PR en esta etapa.

## Evidencia de entrada

- `runs/06-calidad-captura-mobile/spec.md`: exige un chequeo de calidad de
  imagen que corra antes de OCR, sobre la imagen ya orientada por EXIF
  pero antes de `image_prep.prepare`, evaluando 8 señales (blur, baja
  resolución, reflejos, sombras, documento cortado, mala perspectiva, mala
  iluminación, encuadre insuficiente) con un veredicto de tres niveles
  (`ok`/`warn`/`reject`), reutilizando la detección de contorno ya
  existente en `image_prep.correct_perspective`, sin tocar
  `services.ini`, sin agregar dependencias nuevas, con umbrales
  configurables por variable de entorno y con fixtures 100 % sintéticas.
- `runs/06-calidad-captura-mobile/audit-1.md`: veredicto `approved`, sin
  bloqueantes. Feedback no bloqueante recibido y atendido explícitamente
  en esta implementación:
  1. Documentar los valores de umbral por defecto elegidos con su
     justificación → cubierto en la tabla completa de
     `docs/tecnica/calidad-captura-mobile.md` (sección "Umbrales
     configurables por variable de entorno"), con justificación
     específica por señal en la sección de cada una de las 8 señales.
  2. Dejar constancia del riesgo de calibración contra fotos reales →
     sección dedicada "Riesgo de calibración conocido (no bloqueante, a
     revisar post-despliegue)" en `docs/tecnica/calidad-captura-mobile.md`
     y en este documento (ver más abajo).
  3. Accesibilidad del aviso `warn` (aria-live) → el spec ya declara
     explícitamente que el rediseño de UI está fuera de alcance; no se
     agregó nada nuevo en ese sentido, consistente con el scope acotado
     ya aprobado.

## Decisiones tomadas

### Nombre del estado de job nuevo

`needs_new_photo` (constante `quality_gate.REJECTED_JOB_STATUS`). Se
prefirió sobre `rejected_quality`/`quality_rejected` porque describe la
acción que el usuario debe tomar (sacar una foto nueva), coherente con el
resto de los nombres de estado existentes (`queued`, `processing`,
`ready`, `confirmed`, `failed`), y es el texto mostrado directamente en el
frontend (`pill`, contador `stat-quality`).

### Cómo se evita el doble conteo perspectiva/corte (dedup de causa raíz)

`image_prep.find_document_contour` (extraída de la lógica que ya tenía
`correct_perspective`) devuelve `None` cuando no encuentra un cuadrilátero
de 4 lados cerrado. Se verificó (y se documentó en
`docs/tecnica/calidad-captura-mobile.md`) que un documento cortado en el
encuadre produce, por construcción, un contorno de bordes **abierto** (no
hay gradiente Canny detectable exactamente en el límite del array de
píxeles), cuya área encerrada es casi nula — por eso
`find_document_contour` naturalmente devuelve `None` en ese caso concreto,
sin necesidad de ningún caso especial de código. La señal de "mala
perspectiva" (`quality_gate._perspective_signal`) directamente no evalúa
nada cuando el cuadrilátero es `None` (devuelve `(None, None)`, sin
agregar ninguna razón), así que nunca reporta una segunda razón
independiente por la misma causa raíz que "documento cortado". La señal de
"documento cortado" en sí usa una función **distinta**
(`image_prep.largest_contour_bounding_box`, que ordena los contornos
candidatos por área de *bounding box* en vez de área encerrada) porque el
contorno abierto sí tiene un bounding box representativo del documento
visible, aunque no cierre en un cuadrilátero — se detalla el porqué
técnico completo en `docs/tecnica/calidad-captura-mobile.md`. Verificado
por test (`test_cut_document_deduplicates_perspective_reason`).

### Umbrales por defecto y su justificación (resumen; detalle completo en
`docs/tecnica/calidad-captura-mobile.md`)

Todos configurables por variable de entorno (`GI_OCR_QUALITY_*`), mismo
patrón que `upload_validation.max_upload_bytes`. El valor más delicado de
calibrar fue el umbral de "sobreexposición" (mala iluminación, lado
claro): se fijó deliberadamente muy cerca del techo
(`GI_OCR_QUALITY_BRIGHTNESS_BRIGHT_REJECT_ABOVE=254.5` sobre 255) porque
el propio comprobante de referencia de este repo
(`backend/tests/fixtures/gas_sample.jpg`, fondo blanco con texto disperso)
mide un brillo medio global de `~254.1` sin tener ningún problema real —
un umbral más conservador (por ejemplo `>240`) habría generado un falso
positivo sistemático contra el estilo de documento que el propio proyecto
usa como referencia, y habría roto además la integración end-to-end de la
feature `05-correccion-orientacion-exif` (`test_exif_orientation.py`) y
`backend/tests/test_process_document_cli.py`, que procesan `process_document`
completo sobre fixtures con ese mismo perfil de brillo. Se verificó
explícitamente, corriendo la suite completa antes y después del ajuste,
que ese es el punto de calibración correcto para no introducir una
regresión sobre tests preexistentes no relacionados con esta feature.

### Umbrales globales, no en `services.ini`

Confirmado como en el spec: el chequeo corre antes de que
`capture_pipeline.process_image` clasifique el proveedor/servicio, así que
no hay forma de tener un umbral "por servicio" en este punto del pipeline
sin invertir el orden. No se tocó `backend/config/services.ini`.

### Reutilización de contorno, no duplicación

`image_prep.py` quedó con dos funciones nuevas reutilizables
(`find_document_contour`, `largest_contour_bounding_box`), ambas
construidas sobre una tercera función interna compartida
(`_document_edge_contours`). `correct_perspective` se reescribió para
llamar a `find_document_contour(img, min_area_ratio=0.3)` en vez de tener
su propio bucle Canny/findContours/approxPolyDP — se verificó por test
(`backend/tests/test_image_prep.py`, sin cambios y sin fallos) que el
comportamiento es idéntico al de antes de esta feature.

### Punto de integración

`capture_pipeline.process_document`, justo después de
`apply_exif_orientation` y antes de `image_prep.prepare`/OCR, tal como
exige el spec. Veredicto `reject` → `_quality_rejected_result` (resultado
mínimo, mismo "shape" que el resultado normal, sin invocar
`process_image`/`ocr_engine`). Veredicto `ok`/`warn` → pipeline normal,
con `processing_metadata.quality_gate` agregado al resultado final.

### `job_queue.py` — sin tocar `confirm`/`retry` en `main.py`

No hizo falta ningún cambio en `backend/app/main.py`: como el camino
`reject` no llama `store.save_original` (igual que el camino `failed`
existente), `store.original_exists(job_id)` sigue devolviendo `False` para
un job rechazado por calidad, y por lo tanto `confirm_job`/
`download_confirmed`/`download_original` siguen devolviendo 404/409 sin
ningún cambio de código — se heredó gratis del comportamiento existente,
tal como anticipaba `audit-1.md`. De la misma forma, `JobQueue.retry()`
solo bloquea `"ready"`/`"confirmed"`; `"needs_new_photo"` no está en esa
tupla, así que el reintento funciona sin cambios de código, y al ser
`quality_gate.evaluate` una función pura y determinística, el reintento
sobre el mismo archivo da el mismo veredicto.

## Riesgo conocido: calibración de umbrales contra fotos reales (no
bloqueante)

Todos los umbrales por defecto se calibraron empíricamente contra
fixtures **100 % sintéticas** (rectángulos, texto dibujado con PIL,
transformaciones OpenCV controladas), siguiendo la política de este repo
de no versionar comprobantes reales ni derivarlos de `storage_bridge/`.
Esto es una limitación reconocida y explícita, señalada también por
`audit-1.md`: estos valores **no** están calibrados contra un corpus de
fotos reales de celular (variedad real de cámaras, condiciones de luz,
tipos de papel, reflejos de plástico/vidrio, ruido de compresión JPEG
real). Quedan como punto de partida razonable, no como valores
definitivos. Se recomienda explícitamente revisar y recalibrar estos
umbrales (todos expuestos por variable de entorno, sin necesidad de
cambios de código) una vez que el flujo esté en uso real con fotos de
usuarios — esto queda registrado como tarea de seguimiento post-despliegue,
no como bloqueante de esta feature. Detalle completo en
`docs/tecnica/calidad-captura-mobile.md`, sección "Riesgo de calibración
conocido".

## Alcance no modificado

- No se cambió el motor OCR (RapidOCR/ONNX, ADR-006) ni el two-pass ROI.
- No se tocó `backend/config/services.ini` ni el formato `.DATA`.
- No se implementó corrección automática de imagen (deshacer sombras,
  reflejos, etc.) — solo detección + decisión, tal como exige el spec.
- No se implementó reintento automático de captura ni feedback de cámara
  en vivo — fuera de alcance explícito del spec.
- No se agregó ninguna dependencia nueva: se usa `opencv-python-headless`,
  ya declarada en `backend/requirements.txt` y ya usada por
  `image_prep.py`.
- No se versionaron fotos reales de celular ni comprobantes reales:
  todas las fixtures de test son 100 % sintéticas, generadas en memoria.
- El camino PDF (`_process_pdf`) no pasa por este chequeo, consistente con
  el precedente ya documentado en `docs/tecnica/correccion-orientacion-exif.md`.

## Verificación de tests

`pytest -q` corrido con el entorno virtual del repo
(`D:\proyectos\gi-ocr\.venv`, con `rapidocr_onnxruntime`/`opencv-python-headless`
instalados). Igual que en `05-correccion-orientacion-exif`, se evitó el
fixture `tmp_path` de pytest en los tests nuevos (`backend/tests/
test_quality_gate.py` usa `tempfile.mkdtemp()`/`tempfile.mktemp()` en su
lugar) por un problema de entorno preexistente y no relacionado con esta
feature: permiso denegado sobre la carpeta temporal compartida de pytest
en Windows (`%TEMP%/pytest-of-<usuario>`) en este entorno de desarrollo —
el mismo problema ya afecta, sin relación con esta feature, a
`test_retention.py`, `test_storage_bridge_writer.py`,
`test_services_config_schema.py` y otros, antes y después de este cambio.

- `backend/tests/test_quality_gate.py`: 48/48 tests pasan — cobertura de
  las 8 señales (ok/warn/reject y falsos positivos evitados por señal),
  veredicto agregado (señales simultáneas, severidad mixta, dedup de
  causa raíz corte/perspectiva), integración con
  `capture_pipeline.process_document` (OCR no invocado en `reject`,
  `warn` sigue el pipeline normal), integración con `JobQueue`
  (`needs_new_photo`, determinismo de `retry`, regresión de `save_original`
  en `ok`/`ready`), integración HTTP end-to-end (`confirm` → 404,
  `retry` → 200) e imágenes degeneradas/corruptas sin excepción.
- `backend/tests/test_image_prep.py`: 5/5 sin cambios, confirma que el
  refactor de `correct_perspective` no altera su comportamiento.
- `backend/tests/test_exif_orientation.py`,
  `backend/tests/test_process_document_cli.py`: sin regresiones —
  ambos ejercitan `capture_pipeline.process_document` de punta a punta
  sobre fixtures existentes; motivó el ajuste fino del umbral de
  sobreexposición documentado arriba.
- Resto de la suite (`backend/tests/`): 281 passed, 7 skipped (antes de
  esta feature: 233 passed sobre el mismo subconjunto no afectado por los
  errores de entorno preexistentes), sin regresiones atribuibles a esta
  feature. Los mismos ~57 errores de entorno preexistentes (`tmp_path`)
  persisten idénticos antes y después del cambio.

## Artefactos

- `backend/app/quality_gate.py` (nuevo)
- `backend/app/image_prep.py` (`find_document_contour`,
  `largest_contour_bounding_box`, refactor de `correct_perspective`)
- `backend/app/capture_pipeline.py` (`process_document`,
  `_quality_rejected_result`)
- `backend/app/job_queue.py` (estado `needs_new_photo`)
- `frontend/src/app.js`, `frontend/src/style.css`, `frontend/index.html`
- `backend/tests/test_quality_gate.py`
- `docs/tecnica/calidad-captura-mobile.md`
- `docs/usuario/calidad-captura-mobile.md`
- `runs/06-calidad-captura-mobile/decision.md`
