# Spec: Corrección de orientación EXIF

> Producida por `analyst-agent` desde `ROADMAP.md` (ítem
> `05-correccion-orientacion-exif`) y lectura directa de
> `backend/app/image_prep.py`, `backend/app/capture_pipeline.py`,
> `backend/tests/test_image_prep.py` y `docs/tecnica/arquitectura.md`.

## Alcance

Incluye:

- Leer el tag EXIF `Orientation` (valores estándar 1–8: rotaciones
  90/180/270 y variantes espejadas) de las imágenes de entrada (JPEG
  principalmente, cualquier formato que PIL exponga EXIF) **antes** de que
  la imagen entre al pipeline de OCR, y aplicar la transformación de
  píxeles correspondiente para que la imagen quede en orientación "de
  pie" tal como la vería una persona.
- Reemplazar el punto de entrada actual `Image.open(path).convert("RGB")`
  en `backend/app/capture_pipeline.py::process_document` (único punto de
  entrada real usado por `job_queue.py` → `main.py`/`inbound_watcher.py`)
  por una lectura que aplique EXIF Orientation de forma confiable (p.ej.
  `PIL.ImageOps.exif_transpose`) antes de convertir a `np.ndarray`.
- Decidir explícitamente la relación entre esta corrección EXIF y la
  heurística existente `image_prep.correct_orientation` (basada en
  varianza de gradiente Sobel, solo cubre 90/270, no cubre 180 ni
  espejado, ver "Riesgos / supuestos" para la decisión tomada y su
  justificación).
- Tests sintéticos: imágenes generadas en el test (no fotos reales) con
  el tag EXIF `Orientation` seteado explícitamente a cada uno de los 8
  valores estándar, verificando que la imagen resultante que llega a OCR
  queda en la orientación correcta en cada caso.
- Evidencia verificable (test automatizado, no inspección manual) de que
  la imagen que recibe `ocr_engine.detect_page`/`recognize_selected`
  (RapidOCR) ya está orientada correctamente cuando la imagen de entrada
  traía metadata EXIF de rotación.
- Actualizar `backend/app/image_prep.py` únicamente en lo necesario para
  que la heurística existente no contradiga ni deshaga la corrección EXIF
  ya aplicada aguas arriba (ver criterios de aceptación).

Explícitamente **NO** incluye (fuera de alcance de esta feature):

- Deskew (corrección de inclinación leve), corrección de perspectiva
  (`image_prep.correct_perspective`), normalización de escala, contraste
  o cualquier otro preprocesamiento — eso sigue como está, sin cambios de
  comportamiento salvo el punto de integración de la orientación EXIF.
- El sistema formal de trazabilidad de transformaciones de imagen
  (registro de qué transformaciones se aplicaron, versiones intermedias,
  preservación garantizada del original) — eso es responsabilidad de la
  feature `07-preprocesamiento-documental-no-destructivo`, todavía no
  iniciada. Esta feature no debe anticipar ni bloquear ese diseño.
- Cambiar el motor OCR (RapidOCR/ONNX, ADR-006), el formato `.DATA`/
  `services.ini` (ADR-007), ni la separación OCR/extracción/
  validación/storage (ver `docs/tecnica/arquitectura.md`). No se reabre
  ninguna de esas decisiones.
- Corrección de orientación para PDFs renderizados
  (`backend/app/pdf_util.py` → `_process_pdf`): los PDFs no traen tag
  EXIF de foto de celular en el mismo sentido (son renderizados a imagen
  por `pypdfium2`); esta feature no modifica el camino PDF.
- Control de calidad de captura (blur, baja resolución, mala
  iluminación) — eso es `06-calidad-captura-mobile`.

## Contexto

El pipeline de captura (`backend/app/capture_pipeline.py::process_document`)
abre la imagen subida con `PIL.Image.open(path).convert("RGB")` y la
convierte directo a `np.ndarray`, **sin** aplicar el tag EXIF
`Orientation`. Esto significa que hoy, si un celular guarda una foto
"derecha" para el usuario pero con `Orientation != 1`, el array de
píxeles que recibe OCR está efectivamente rotado/espejado.

El pipeline tiene una heurística de corrección de orientación,
`image_prep.correct_orientation()` (`backend/app/image_prep.py`), basada
en varianza de gradiente Sobel horizontal/vertical, que solo corrige 90°
CW/CCW, no cubre 180° ni espejado, y no es confiable frente a metadata
EXIF cuando esta existe.

`image_prep.prepare()` es el punto único de preparación de imagen antes
de OCR. El orden actual es: `correct_orientation → deskew → (perspectiva
opcional) → normalize_scale`.

## Criterios de aceptación

1. Existe una función (ubicación sugerida: `backend/app/image_prep.py`,
   nombre sugerido `apply_exif_orientation` o equivalente) que recibe una
   imagen abierta con PIL (o el path) y devuelve los píxeles ya
   orientados según el tag EXIF `Orientation`, usando una lectura
   confiable del tag (p.ej. `PIL.ImageOps.exif_transpose`, no
   reimplementar a mano la tabla de 8 valores salvo justificación
   explícita).
2. `capture_pipeline.process_document` aplica esa corrección EXIF
   **antes** de que la imagen entre a `image_prep.prepare()`/OCR, para el
   camino de imagen (no PDF).
3. Para cada uno de los 8 valores estándar de EXIF `Orientation` (1 a 8),
   un test genera una imagen sintética en memoria (PIL, sin fixtures
   binarias versionadas) con contenido asimétrico verificable por código
   (p.ej. un rectángulo de color en una esquina específica, no texto) y
   el tag EXIF correspondiente seteado, y verifica que después de la
   corrección el contenido asimétrico queda en la posición esperada
   (equivalente a "orientación 1").
4. Existe al menos un test de integración que arma una imagen sintética
   con texto renderizado (o un fixture existente reutilizado del
   pipeline) con tag EXIF `Orientation=6` o `Orientation=8` y verifica,
   corriendo `capture_pipeline.process_document` completo, que RapidOCR
   devuelve texto reconocible/no vacío en `raw_ocr_text`.
5. La heurística `image_prep.correct_orientation()` queda subordinada a
   la corrección EXIF: no se ejecuta (o se documenta explícitamente por
   qué sigue corriendo) cuando ya se aplicó una corrección EXIF válida
   sobre la misma imagen, para evitar doble corrección. Un test cubre
   este caso.
6. Cuando la imagen no trae tag EXIF `Orientation` utilizable, el
   comportamiento de `image_prep.correct_orientation()` sigue
   funcionando igual que antes — sin regresión. Un test cubre este caso.
7. Todos los tests existentes (`pytest -q`) siguen pasando sin
   modificación de su comportamiento esperado (salvo cambios
   estrictamente necesarios para el nuevo punto de integración).
8. Debe existir `docs/tecnica/correccion-orientacion-exif.md`, no vacío,
   con el algoritmo/lógica usada, tabla de transformaciones por valor
   EXIF, punto exacto de integración en el pipeline, y relación con la
   heurística existente. IMPORTANTE (corrección del reviewer en
   audit-1.md): al documentar formatos de imagen soportados, la lista
   real de extensiones/MIME aceptados por el endpoint de subida
   (`ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".pdf"}`)
   vive en `backend/app/main.py` línea ~38, NO en `validators.py`.
   Confirmar además si `.tif`/`.tiff` soportan tag EXIF Orientation igual
   que JPEG, y que `.png` no.
9. Debe existir `docs/usuario/correccion-orientacion-exif.md`, no vacío,
   con el propósito del flujo y al menos un ejemplo de uso HTTP (request
   + response) sobre el endpoint de subida existente, mostrando que el
   contrato de la API no cambia.
10. Debe existir `runs/05-correccion-orientacion-exif/decision.md` con
    las decisiones demostrables tomadas durante la implementación.
11. Debe existir un enlace exacto a `correccion-orientacion-exif.md` en
    `docs/tecnica/index.md` y otro en `docs/usuario/index.md` (usar
    `scripts/update-doc-indexes.ps1 05-correccion-orientacion-exif "Corrección de orientación EXIF"`
    para esto, sin duplicados).

### Criterios de dominio OCR (obligatorios)

- Comportamiento extraído: no es un campo de negocio puntual, es el
  comportamiento correcto del pipeline OCR completo (orientación de
  entrada → texto reconocido no vacío en `raw_ocr_text`/`field_report`).
- Tipo de documento/fixture: `GAS` (`LITORAL_GAS`), ya usado en features
  previas.
- Fixture: 100% sintética, generada en el propio test (PIL `Image.new` +
  texto renderizado, o reuso de fixture sintético existente en
  `backend/tests/fixtures/`), con tag EXIF seteado por código. NO
  versionar fotos reales de celular.
- Salida esperada: `raw_ocr_text` no vacío y `provider_detected ==
  "LITORAL_GAS"` tras aplicar la corrección EXIF sobre imagen rotada.
- Validación aplicada: geométrica (posición de contenido asimétrico) en
  el test unitario + pipeline completo en el de integración.
- Falso positivo evitado: doble corrección (EXIF + heurística de
  contenido) que termine en orientación incorrecta.

## Casos borde a contemplar

- Imagen sin EXIF en absoluto.
- Imagen con EXIF presente pero sin el tag `Orientation`.
- Imagen con `Orientation = 1` explícito (no debe alterar nada).
- Los 8 valores válidos de `Orientation` (1–8), incluyendo espejados (2,
  4, 5, 7).
- Imagen con EXIF corrupto o `Orientation` fuera de rango (`0`, > 8, no
  numérico): no debe romper el pipeline, debe degradar con gracia
  (tratar como si no hubiera tag).
- PDF renderizado a imagen (`pdf_util`): confirmar en test/documentación
  que esta corrección no aplica a ese camino y por qué.
- Imagen ya orientada correctamente con `Orientation != 1`: el resultado
  tras `exif_transpose` debe seguir siendo correcto, sin rotación
  adicional no deseada.
- Interacción con `image_prep.deskew`: verificar que sigue operando bien
  sobre la imagen ya en orientación correcta.
- Imágenes cuadradas o casi cuadradas.
- Formatos de imagen aceptados por el endpoint (`.jpg`, `.jpeg`, `.png`,
  `.tif`, `.tiff`, `.pdf` según `main.py`) — confirmar cuáles soportan
  EXIF y cuáles no, sin cambiar el comportamiento en los que no.

## Riesgos / supuestos (decisiones ya tomadas y aprobadas, no reabrir sin justificación fuerte)

- Usar `PIL.ImageOps.exif_transpose` (Pillow, ya es dependencia) como
  mecanismo de lectura confiable del tag EXIF.
- Subordinar (no eliminar) `image_prep.correct_orientation()`: sigue
  siendo la red de contención para imágenes sin EXIF utilizable.
- No se resuelve 180°/espejado con la heurística de contenido cuando no
  hay EXIF (limitación conocida y aceptada, fuera de alcance).
- Punto de integración: en `capture_pipeline.process_document`, mismo
  lugar donde hoy se hace `Image.open(path).convert("RGB")`, NO dentro de
  `image_prep.prepare()` (que ya recibe `np.ndarray` sin metadata EXIF).
- No tocar `backend/app/t3_2_orchestrator.py` (código legado T3.x, no
  está en el camino de producción activo).
- No versionar fotos reales rotadas de celular como fixture — todo
  sintético generado en el propio test.
