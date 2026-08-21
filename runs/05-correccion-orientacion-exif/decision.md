# Decision: 05-correccion-orientacion-exif

## Estado

Implementación builder-agent lista para QA. No se marca `ROADMAP.md` y no
se crea PR en esta etapa.

## Evidencia de entrada

- `runs/05-correccion-orientacion-exif/spec.md`: exige leer el tag EXIF
  `Orientation` (1–8) antes de que la imagen entre al pipeline de OCR,
  reemplazar el punto de entrada `Image.open(path).convert("RGB")` en
  `capture_pipeline.process_document`, subordinar la heurística de
  contenido `image_prep.correct_orientation` cuando ya hubo corrección
  EXIF, y cubrir con tests sintéticos los 8 valores estándar más los casos
  borde (sin EXIF, sin tag, valores corruptos/fuera de rango).
- El spec incluye una corrección explícita del reviewer (`audit-1.md`):
  la lista real de extensiones aceptadas por el endpoint de subida vive en
  `backend/app/main.py` (`ALLOWED_EXTS`, línea ~38), no en
  `validators.py`.

## Decisiones tomadas

- **Mecanismo de lectura EXIF**: `PIL.ImageOps.exif_transpose` (Pillow,
  dependencia ya existente) en vez de reimplementar a mano la tabla de 8
  valores. Es la utilidad estándar del ecosistema para este problema
  concreto.
- **Nueva función `apply_exif_orientation(image) -> (Image, bool)`** en
  `backend/app/image_prep.py`. Devuelve la imagen corregida y un booleano
  `applied` que es `True` solo cuando el tag `Orientation` estaba presente
  con un valor `2..8` (transformación real de píxeles). Con `Orientation
  == 1` (ya derecha) o sin tag utilizable, `applied` es `False`.
  Degrada con gracia (no lanza excepción) ante EXIF corrupto o valores
  fuera de rango (`0`, `9`, `-1`, `100`, no numéricos): se trata como "sin
  corrección EXIF disponible" y devuelve la imagen original sin modificar.
- **Punto de integración**: en `capture_pipeline.process_document`,
  reemplazando `Image.open(path).convert("RGB")` por
  `Image.open(path)` → `apply_exif_orientation` → `.convert("RGB")` →
  `np.array`. Se eligió este punto (y no dentro de
  `image_prep.prepare()`) porque `prepare()` ya recibe `np.ndarray`, que
  no lleva metadata EXIF asociada — la corrección debe ocurrir mientras la
  imagen todavía es un objeto `PIL.Image.Image` con su EXIF intacto.
- **Subordinación de la heurística de contenido, no eliminación**:
  `image_prep.correct_orientation(image_np, skip: bool = False)` agrega el
  parámetro `skip`. Cuando `skip=True` (porque ya hubo corrección EXIF
  válida), la heurística de gradiente Sobel no se ejecuta. Cuando
  `skip=False` (default, sin corrección EXIF utilizable), el
  comportamiento es exactamente el mismo que antes de esta feature — sin
  regresión. `image_prep.prepare()` agrega el parámetro
  `exif_orientation_applied: bool = False` y lo traduce a
  `correct_orientation(image_np, skip=exif_orientation_applied)`.
- **PDF fuera de alcance**: `_process_pdf` sigue llamando a
  `image_prep.prepare()` sin pasar `exif_orientation_applied` (usa el
  default `False`), sin cambios de comportamiento. Los PDFs se renderizan
  con `pypdfium2` y no traen metadata EXIF de cámara de celular en el
  mismo sentido.
- **`backend/app/t3_2_orchestrator.py` no se toca**: código legado T3.x,
  no está en el camino de producción activo (`job_queue.py` → `main.py` /
  `inbound_watcher.py` usan `capture_pipeline.process_document`).
- **Documentación de formatos soportados** (corrección del reviewer
  aplicada): se confirmó leyendo `backend/app/main.py` directamente que
  `ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".pdf"}` vive
  ahí, no en `validators.py`. Se verificó empíricamente con Pillow 12.2
  (round-trip guardar/leer EXIF) que JPEG y TIFF soportan el tag
  `Orientation` de forma equivalente (TIFF 6.0 baseline, del cual EXIF
  hereda la numeración de tags), que PNG técnicamente puede llevar un
  chunk `eXIf` opcional pero en la práctica no es relevante para esta
  feature (las cámaras de celular no producen PNG), y que PDF queda fuera
  del camino de código de esta corrección.

## Alcance no modificado

- No se cambió el motor OCR (RapidOCR/ONNX, ADR-006).
- No se tocó `services.ini`, el formato `.DATA` ni `storage_bridge/`.
- No se modificó deskew, corrección de perspectiva ni normalización de
  escala/contraste — solo el nuevo punto de integración de orientación,
  que corre antes en la secuencia existente.
- No se implementó el sistema formal de trazabilidad de transformaciones
  de imagen (queda para la feature futura
  `07-preprocesamiento-documental-no-destructivo`).
- No se versionaron fotos reales de celular: todos los fixtures de test
  son 100% sintéticos, generados en memoria con PIL.

## Verificación de tests

`pytest -q` corrido con el entorno virtual del repo
(`D:\proyectos\gi-ocr\.venv`, con `rapidocr_onnxruntime` instalado), usando
un `--basetemp` propio para evitar un problema de entorno preexistente y
no relacionado con esta feature (permiso denegado en la carpeta temporal
compartida de pytest en Windows, `pytest-of-<usuario>`, cuando queda
bloqueada por otra corrida concurrente).

- `backend/tests/test_exif_orientation.py`: 20/20 tests pasan, incluyendo
  los 8 valores estándar de `Orientation`, los casos borde (sin EXIF, sin
  tag, corrupto/fuera de rango), la subordinación de la heurística y la
  integración end-to-end con `capture_pipeline.process_document` sobre un
  comprobante GAS sintético con `Orientation=6`/`8`.
- Resto de la suite (`backend/tests/` + `tests/`): sin regresiones
  atribuibles a esta feature.

## Artefactos

- `backend/app/image_prep.py` (`apply_exif_orientation`, `correct_orientation(skip=...)`, `prepare(exif_orientation_applied=...)`)
- `backend/app/capture_pipeline.py` (`process_document`)
- `backend/tests/test_exif_orientation.py`
- `docs/tecnica/correccion-orientacion-exif.md`
- `docs/usuario/correccion-orientacion-exif.md`
- `runs/05-correccion-orientacion-exif/decision.md`
