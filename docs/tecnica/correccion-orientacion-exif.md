# Corrección de orientación EXIF

## Propósito

Antes de esta feature, `capture_pipeline.process_document` abría la imagen
subida con `Image.open(path).convert("RGB")` y la convertía directo a
`np.ndarray`, **sin** interpretar el tag EXIF `Orientation`. Una foto de
celular guardada por la cámara "derecha" para el usuario pero con
`Orientation != 1` (muy común: casi todas las cámaras de celular escriben
el tag en vez de rotar físicamente los píxeles, para no perder tiempo de
captura) llegaba a OCR efectivamente rotada o espejada, degradando la
detección de campos.

Esta feature agrega un paso previo, específico y aislado, que interpreta
ese tag y corrige los píxeles antes de que la imagen entre al pipeline de
preparación (`image_prep.prepare`) y a OCR (`ocr_engine`).

## Algoritmo

### Lectura del tag EXIF `Orientation`

`backend/app/image_prep.py::apply_exif_orientation(image: Image.Image) ->
Tuple[Image.Image, bool]` usa `PIL.ImageOps.exif_transpose`, la utilidad
estándar de Pillow para este problema, en vez de reimplementar a mano la
tabla de 8 valores. `exif_transpose`:

1. Lee el tag EXIF `Orientation` (id `0x0112` / `274`) desde
   `image.getexif()`.
2. Si el valor es uno de los 8 estándar (1–8), devuelve una nueva imagen
   con la transformación de píxeles correspondiente ya aplicada y **borra**
   el tag `Orientation` de la imagen resultante (para que no se vuelva a
   aplicar dos veces si algo más adelante mira el EXIF).
3. Si no hay EXIF, no hay tag `Orientation`, o el valor no es interpretable,
   `exif_transpose` no modifica nada y devuelve la imagen tal cual (o
   `None` en casos límite de Pillow, contemplado explícitamente).

Tabla de transformaciones por valor de `Orientation` (según especificación
EXIF/TIFF, aplicada internamente por `exif_transpose`):

| Orientation | Significado                                   | Transformación aplicada       |
|:-----------:|------------------------------------------------|--------------------------------|
| 1           | Ya "de pie", sin corrección necesaria           | ninguna                        |
| 2           | Espejada horizontalmente                        | `FLIP_LEFT_RIGHT`              |
| 3           | Rotada 180°                                     | `ROTATE_180`                   |
| 4           | Espejada verticalmente                          | `FLIP_TOP_BOTTOM`              |
| 5           | Espejada + rotada 90° (transpose)               | `TRANSPOSE`                    |
| 6           | Rotada 90° (la cámara se sostuvo de lado)       | `ROTATE_90` (real: -90° visual)|
| 7           | Espejada + rotada 270° (transverse)             | `TRANSVERSE`                   |
| 8           | Rotada 270°                                     | `ROTATE_270`                   |

`apply_exif_orientation` además:

- Lee el valor crudo del tag **antes** de llamar a `exif_transpose`
  (guardado en `orientation_tag`), exclusivamente para poder reportar si
  hubo o no corrección efectiva.
- Devuelve `(imagen_corregida, se_aplico_correccion)`. `se_aplico_correccion`
  es `True` únicamente si el tag estaba presente, era un entero (no `bool`,
  que en Python es subclase de `int`) y estaba en el rango `2..8` (es decir,
  si `exif_transpose` efectivamente transformó píxeles). Con
  `Orientation == 1` no se considera "aplicada" porque no hubo
  transformación real, aunque el tag estuviera presente y fuera válido.
- Degrada con gracia ante EXIF corrupto: cualquier excepción al leer
  `getexif()` o al llamar `exif_transpose` se captura y se trata como "sin
  corrección EXIF disponible", devolviendo la imagen original sin
  modificar. Esto cubre valores fuera de rango (`0`, `9`, `-1`, `100`,
  etc.) y valores no numéricos (p. ej. un tag `Orientation` con un string),
  que Pillow o el propio código descartan sin lanzar excepción hacia el
  llamador.

### Punto de integración en el pipeline

`backend/app/capture_pipeline.py::process_document`, en el camino de
imagen (no PDF):

```python
img = Image.open(path)
img, exif_applied = image_prep.apply_exif_orientation(img)
img = img.convert("RGB")
arr = np.array(img)
prepared = image_prep.prepare(arr, exif_orientation_applied=exif_applied)
return process_image(prepared, src)
```

Puntos clave de este orden:

- `apply_exif_orientation` se llama **antes** de `.convert("RGB")`, porque
  necesita la imagen PIL original con su metadata EXIF intacta
  (`convert("RGB")` no destruye el EXIF por sí solo, pero conceptualmente
  el paso de corrección de orientación debe ocurrir sobre la imagen tal
  como llegó, antes de cualquier otra transformación).
- El resultado (`exif_applied: bool`) viaja como parámetro explícito
  `exif_orientation_applied` hacia `image_prep.prepare()`, que es el único
  punto de entrada de preparación de imagen antes de OCR. `prepare()` en sí
  mismo ya no ve ninguna metadata EXIF (recibe `np.ndarray`), por eso el
  booleano se calcula aguas arriba y se pasa explícitamente.
- El camino PDF (`_process_pdf` / `pdf_util`) no se toca: los PDFs se
  renderizan a imagen con `pypdfium2` y no traen tag EXIF de cámara en el
  mismo sentido (ver "Fuera de alcance").

### Relación con `image_prep.correct_orientation` (heurística de contenido)

`image_prep.correct_orientation()` es una heurística preexistente basada en
varianza de gradiente Sobel horizontal/vertical: compara cuánto "borde"
horizontal vs. vertical tiene la imagen y, si la relación es fuerte,
asume que está rotada 90°/270° y la rota. Limitaciones conocidas y ya
existentes antes de esta feature:

- Solo cubre 90°/270° (no 180°, no espejado).
- Es una heurística de contenido, no de metadata: puede equivocarse con
  documentos de layout atípico.

Esta feature **subordina** (no elimina) esa heurística: agrega un
parámetro `skip: bool = False` a `correct_orientation(image_np, skip=False)`.
Cuando `skip=True`, la función devuelve la imagen tal cual (solo aplica
`to_rgb`), sin ejecutar la heurística de gradiente. `image_prep.prepare()`
recibe `exif_orientation_applied: bool = False` y llama internamente a
`correct_orientation(image_np, skip=exif_orientation_applied)`.

Justificación de la decisión (documentada también en
`runs/05-correccion-orientacion-exif/decision.md`): si la corrección EXIF
ya dejó la imagen "de pie" de forma confiable (metadata explícita de la
cámara), volver a pasarla por una heurística de contenido que puede
rotarla de nuevo sería, en el mejor caso, redundante y, en el peor, una
doble corrección que la desorienta otra vez. Cuando no hubo corrección EXIF
utilizable (`exif_orientation_applied=False`, el default), el comportamiento
es exactamente el mismo que antes de esta feature — sin regresión.

### Orden final en `image_prep.prepare()`

Sin cambios de orden respecto a antes, solo el nuevo parámetro:

```
correct_orientation(skip=exif_orientation_applied) -> deskew -> (perspectiva opcional) -> normalize_scale
```

`deskew` sigue operando sobre la imagen ya en la orientación correcta
(gracias a EXIF o a la heurística, según el caso), sin cambios de
comportamiento.

## Formatos de imagen soportados por el endpoint de subida

La lista real de extensiones aceptadas vive en `backend/app/main.py`
(línea ~38), **no** en `validators.py`:

```python
ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".pdf"}
```

Soporte de tag EXIF `Orientation` por formato, verificado directamente con
Pillow 12.2 (versión usada en este repo, ver `backend/requirements.txt`):

- **JPEG (`.jpg`/`.jpeg`)**: soporte estándar y es, en la práctica, el
  formato relevante para esta feature — es el que producen las cámaras de
  celular, casi siempre con el tag `Orientation` presente (las cámaras
  escriben el tag en vez de rotar físicamente los píxeles, por velocidad
  de captura).
- **TIFF (`.tif`/`.tiff`)**: soporta el tag `Orientation` igual que JPEG.
  El tag `Orientation` (`0x0112`) es en realidad un tag baseline de TIFF
  6.0 del cual EXIF hereda su numeración; Pillow expone ambos casos por
  `Image.getexif()` de forma equivalente, y `ImageOps.exif_transpose`
  funciona igual sobre TIFF que sobre JPEG (verificado con un round-trip
  `Image.new(...).save(..., format="TIFF", exif=exif)` seguido de
  `exif_transpose`).
- **PNG (`.png`)**: el spec PNG moderno admite un chunk `eXIf` opcional
  (soportado por Pillow desde hace varias versiones; en Pillow 12.2,
  `Image.getexif()` también lo lee si está presente), por lo que
  técnicamente `apply_exif_orientation` no ignora ni rechaza PNG. Sin
  embargo, en la práctica **no es un caso relevante para esta feature**:
  las cámaras de celular no producen PNG para fotos (usan JPEG), y las
  fuentes típicas de PNG en este flujo (capturas de pantalla, imágenes
  editadas/exportadas) casi nunca llevan el chunk `eXIf` con
  `Orientation`. El comportamiento es correcto por construcción: si un PNG
  trajera ese chunk, se corregiría igual que un JPEG; si no lo trae (caso
  normal), `apply_exif_orientation` no hace nada, igual que antes de esta
  feature.
- **PDF (`.pdf`)**: fuera de alcance de esta feature (ver más abajo). El
  camino PDF no pasa por `apply_exif_orientation`.

## Decisiones de diseño

- **Usar `PIL.ImageOps.exif_transpose` en vez de reimplementar la tabla de
  8 valores a mano**: es la utilidad estándar y ya probada de una
  dependencia existente (Pillow), reduce superficie de bugs propios en un
  problema ya resuelto por la librería.
- **Punto de integración en `capture_pipeline.process_document`, no dentro
  de `image_prep.prepare()`**: `prepare()` recibe `np.ndarray`, que ya no
  tiene metadata EXIF asociada. La corrección debe ocurrir sobre la imagen
  PIL original, antes de la conversión a array, así que vive en el único
  lugar del pipeline donde todavía existe el objeto `Image.Image` con su
  EXIF intacto.
- **Booleano explícito (`exif_orientation_applied`) en vez de reinspeccionar
  metadata más abajo**: como el array `np.ndarray` no lleva EXIF, la única
  forma de que `image_prep.prepare()`/`correct_orientation()` sepan que ya
  hubo una corrección confiable aguas arriba es que se les diga
  explícitamente. Se prefirió un parámetro explícito y booleano antes que
  una variable global o un efecto colateral implícito.
- **Subordinar, no eliminar, la heurística de contenido**: sigue siendo la
  única red de contención para imágenes sin EXIF utilizable (por ejemplo,
  imágenes editadas que perdieron su metadata, o escaneadas desde un
  scanner de mesa que no escribe `Orientation`). Eliminarla habría
  reintroducido una regresión para ese caso.
- **`applied = True` solo si `Orientation` estaba en `2..8`, no en
  `1..8`**: con `Orientation == 1` no hay transformación real de píxeles
  (la imagen ya estaba "de pie"), así que no tiene sentido subordinar la
  heurística de contenido en ese caso — de hecho, no importa, porque la
  imagen ya está correcta, pero se documenta la distinción para que el
  booleano refleje fielmente "hubo una transformación de píxeles" y no
  simplemente "había un tag presente".
- **No tocar `backend/app/t3_2_orchestrator.py`**: es código legado T3.x,
  no está en el camino de producción activo (`job_queue.py` → `main.py` /
  `inbound_watcher.py` usan `capture_pipeline.process_document`).

## Fuera de alcance (explícitamente no cubierto)

- **PDFs renderizados** (`backend/app/pdf_util.py`, `_process_pdf`): los
  PDFs se renderizan a imagen con `pypdfium2`, no llegan con un tag EXIF de
  cámara de celular en el mismo sentido que una foto. El camino PDF sigue
  llamando a `image_prep.prepare()` directamente, sin
  `apply_exif_orientation` ni el parámetro `exif_orientation_applied`
  (usa el default `False`, comportamiento sin cambios respecto a antes de
  esta feature).
- **Deskew, corrección de perspectiva, normalización de escala/contraste**:
  sin cambios de comportamiento, salvo el nuevo punto de integración de
  orientación que corre antes en la secuencia.
- **Trazabilidad formal de transformaciones de imagen** (registro de qué
  transformaciones se aplicaron, versiones intermedias, preservación
  garantizada del original): responsabilidad de la feature futura
  `07-preprocesamiento-documental-no-destructivo`, todavía no iniciada.
- **Control de calidad de captura** (blur, baja resolución, mala
  iluminación): es `06-calidad-captura-mobile`, no esta feature.

## Casos borde cubiertos (y dónde)

Todos cubiertos por test automatizado en
`backend/tests/test_exif_orientation.py`:

- Imagen sin EXIF en absoluto (`test_no_exif_at_all`).
- Imagen con EXIF presente pero sin el tag `Orientation`
  (`test_exif_present_but_no_orientation_tag`).
- `Orientation == 1` explícito, no debe alterar nada
  (`test_apply_exif_orientation_all_8_values[1]`, `applied is False`).
- Los 8 valores válidos 1–8, incluyendo espejados (2, 4, 5, 7)
  (`test_apply_exif_orientation_all_8_values`, parametrizado).
- `Orientation` fuera de rango (`0`, `9`, `-1`, `100`): degrada con gracia,
  sin excepción (`test_orientation_out_of_range_degrades_gracefully`).
- `Orientation` no numérico (EXIF corrupto): degrada con gracia
  (`test_orientation_non_numeric_degrades_gracefully`).
- Subordinación de la heurística de contenido cuando ya se aplicó EXIF
  (`test_correct_orientation_skip_true_bypasses_heuristic`,
  `test_prepare_subordinates_heuristic_when_exif_applied`).
- Sin regresión de la heurística cuando no hay corrección EXIF
  (`test_correct_orientation_no_regression_without_exif`).
- Integración end-to-end con `capture_pipeline.process_document` sobre un
  comprobante GAS sintético con `Orientation=6`/`8`, verificando
  `raw_ocr_text` no vacío y con el identificador de cliente legible
  (`test_process_document_recovers_text_from_rotated_exif_image`).
- PDF renderizado: no aplica esta corrección (ver "Fuera de alcance"); no
  requiere test adicional porque el camino de código no cambia (usa el
  default `exif_orientation_applied=False` de `prepare()`, igual que
  antes de esta feature).

## Ubicación del código

- `backend/app/image_prep.py`: `apply_exif_orientation`, cambios en
  `correct_orientation` (parámetro `skip`) y `prepare` (parámetro
  `exif_orientation_applied`).
- `backend/app/capture_pipeline.py`: `process_document`, punto de
  integración.
- `backend/tests/test_exif_orientation.py`: cobertura de tests.
