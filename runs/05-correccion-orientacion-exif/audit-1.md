---
status: approved
attempt: 1
feedback:
  - "Menor, no bloqueante: en 'Casos borde a contemplar' el spec dice
    'revisar backend/app/validators.py para la lista real de
    extensiones/MIME aceptados'. Verificado contra el repo: esa lista
    (ALLOWED_EXTS = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.pdf'})
    vive en backend/app/main.py línea 38, no en validators.py
    (validators.py solo tiene validación semántica de campos: fecha,
    monto, cuenta, medidor, comprobante — nada de formatos de archivo).
    El builder debe corregir esa referencia al documentar el caso borde
    de formatos soportados en docs/tecnica/correccion-orientacion-exif.md,
    y de paso confirmar que .tif/.tiff (aceptados por el endpoint) sí
    soportan tag EXIF Orientation igual que JPEG, mientras que .png no
    (relevante para el criterio 6 de 'sin regresión sin EXIF').
---

# Auditoría — 05-correccion-orientacion-exif (intento 1)

## Verificación de hechos del spec contra el repo

Confirmado, línea por línea, contra el código actual:

- `backend/app/capture_pipeline.py:204` — `img = Image.open(path).convert("RGB")`
  es efectivamente el punto de entrada de imagen (no PDF) en
  `process_document`, tal como describe el spec. Línea 206,
  `image_prep.prepare(arr)` es el siguiente paso — coincide con la
  propuesta de integración del spec (aplicar EXIF entre `Image.open` y
  `np.array`/`prepare()`).
- `backend/app/job_queue.py:16` — `from .capture_pipeline import
  process_document` confirma que `process_document` es el camino activo
  real usado por el job queue (y por extensión `main.py`/
  `inbound_watcher.py`), como afirma el spec.
- `backend/app/image_prep.py` — confirmado que `correct_orientation()`
  usa varianza de gradiente Sobel horizontal/vertical, solo corrige
  90°CW/90°CCW comparando `h < w` / `w < h`, no cubre 180° ni espejado.
  `prepare()` aplica el orden `correct_orientation → deskew →
  (perspectiva opcional) → normalize_scale`, exactamente como describe
  el spec.
- `backend/tests/test_image_prep.py` — confirmado que los tests
  existentes usan `np.zeros(...)` sintéticos sin metadata EXIF y no
  cubren orientación por tag EXIF; no hay duplicación de cobertura con
  lo que propone el spec.
- `backend/app/t3_2_orchestrator.py:22` — `Image.open(img_path)` sin
  `.convert`/EXIF, confirmado como código no tocado por esta feature,
  consistente con la decisión explícita del spec de no ampliar alcance
  a ese archivo legado.
- `docs/tecnica/index.md` y `docs/usuario/index.md` — confirmado el
  formato de lista (`- [Título](slug.md)`) que el criterio 11 pide
  replicar; no hay entrada previa para esta feature (correcto, todavía
  no implementada).
- `ROADMAP.md:124-129` — la entrada `05-correccion-orientacion-exif`
  pide explícitamente cubrir 90/180/270 y espejadas, tests sintéticos
  con EXIF, subordinación de la heurística actual, y evidencia de que
  RapidOCR recibe la imagen ya orientada — el spec cubre los cuatro
  puntos punto por punto (criterios 3, 5, 4 respectivamente).
- `LITORAL_GAS` como fixture de dominio: confirmado que es un proveedor
  real ya usado en `backend/tests/test_benchmark_captura.py`,
  `backend/tests/test_templates.py` y
  `backend/app/templates/providers.py` — no introduce un tercer
  proveedor, tal como afirma el spec.
- `docs/tecnica/arquitectura.md` — ADR-006 confirmado (RapidOCR/ONNX
  two-pass ROI-focalizada), consistente con la mención de contexto del
  spec sin reabrir esa decisión.

Única inexactitud encontrada: la referencia a `backend/app/validators.py`
para la lista de extensiones/MIME aceptadas (ver `feedback` arriba). La
lista real está en `backend/app/main.py:38`
(`ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".pdf"}`).
Es un caso borde secundario (formatos no-JPEG), no un criterio de
aceptación central, y no bloquea la implementación — el builder puede
localizar el archivo correcto en segundos. No amerita rechazo por sí
sola dado el resto del spec, pero se deja como corrección obligatoria a
incorporar en la documentación técnica final.

## Checklist de auditoría

- **Criterios de aceptación verificables por test**: sí. Los criterios
  3, 4, 5, 6 y 7 especifican explícitamente qué test cubre cada uno
  (valores EXIF 1-8 con contenido asimétrico verificable por código,
  test de integración con `raw_ocr_text` no vacío, test de no-doble-
  corrección, test de no-regresión sin EXIF, `pytest -q` completo). Los
  criterios 1 y 2 son de implementación pero quedan validados
  indirectamente por los tests de 3-6. No hay criterios vagos tipo "debe
  funcionar bien".
- **Alcance con límites claros**: sí, sección "Explícitamente NO
  incluye" es específica y remite a features concretas
  (`07-preprocesamiento-documental-no-destructivo`,
  `06-calidad-captura-mobile`) y a ADRs que no se reabren (ADR-006,
  ADR-007). Excluye explícitamente el camino PDF con justificación
  técnica (pypdfium2 renderiza, no trae EXIF de foto de celular en el
  mismo sentido) y justifica por qué no se toca `t3_2_orchestrator.py`
  (código legado no usado en producción, verificado por import).
- **Casos borde del dominio**: cubiertos los obvios y algunos no
  triviales — sin EXIF, EXIF sin tag Orientation, Orientation=1
  explícito, los 8 valores incluyendo espejados, EXIF corrupto/fuera de
  rango (degradación sin romper pipeline), imagen ya correcta con
  Orientation != 1, interacción con `deskew` (cambio de bordes/relleno
  tras flip), imágenes cuadradas, y formatos no-JPEG (con la corrección
  de referencia de archivo pendiente indicada en `feedback`).
- **Supuestos del analyst razonables**: sí, y están señalados
  explícitamente para objeción en "Riesgos / supuestos" en vez de
  decidirse en silencio: uso de `PIL.ImageOps.exif_transpose` en vez de
  reimplementar la tabla EXIF, subordinar (no eliminar) la heurística
  existente, no cubrir 180°/espejado sin EXIF, punto de integración en
  `capture_pipeline.process_document` y no en `image_prep.prepare()`
  (justificado: `prepare()` ya recibe `np.ndarray` sin metadata), y no
  tocar `t3_2_orchestrator.py`. Estas decisiones son razonables y están
  correctamente ancladas en la lectura real del código (confirmado
  arriba). No se objeta ninguna.
- **Falta algo que el implementador necesite**: no se detecta ninguna
  omisión que bloquee el arranque de la implementación. La única brecha
  de precisión es la referencia a `validators.py` (ver `feedback`), que
  no impide implementar sino que exige una corrección menor de
  redacción en la documentación técnica final.
- **Exige `docs/tecnica/<slug>.md` y `docs/usuario/<slug>.md`**: sí,
  criterios 8 y 9, ambos con contenido mínimo específico exigido
  (algoritmo/tabla de transformaciones/punto de integración/relación
  con heurística para técnica; propósito + ejemplo HTTP para usuario).
- **Exige `decision.md` y enlaces exactos en ambos índices**: sí,
  criterio 10 (`decision.md`) y criterio 11 (enlaces en
  `docs/tecnica/index.md` y `docs/usuario/index.md`, "mismo formato de
  lista que las entradas existentes" — formato verificado y correcto
  contra el estado actual de ambos índices).
- **Feature toca extracción/calidad OCR — sección de dominio
  obligatoria**: presente y completa ("Criterios de dominio OCR
  (obligatorios...)"): comportamiento extraído (orientación → texto
  reconocible, no un campo de negocio puntual, justificado
  explícitamente por qué no aplica un campo tradicional), tipo de
  documento/fixture (`GAS`/`LITORAL_GAS`, reuso verificado), fixture
  (sintética, generada en test, sin fotos reales — cumple regla dura de
  `AGENTS.md`), salida esperada (`raw_ocr_text` no vacío +
  `provider_detected == LITORAL_GAS`), validación semántica aplicada
  (geométrica en unitario + pipeline completo en integración), falsos
  positivos evitados (doble corrección EXIF + heurística).

## Veredicto

`approved`. El spec está sólidamente anclado en el código real (todas
las referencias de línea/función verificadas), tiene criterios de
aceptación verificables por test, cubre los casos borde relevantes del
dominio, declara sus supuestos abiertamente para objeción del reviewer
en vez de decidirlos en silencio, y cumple los cuatro requisitos no
negociables de documentación/decisión/índices más la sección de
dominio OCR obligatoria. El único hallazgo (referencia incorrecta a
`validators.py` en vez de `main.py` para `ALLOWED_EXTS`) es menor, no
bloqueante, y se deja como corrección a incorporar por el builder al
redactar `docs/tecnica/correccion-orientacion-exif.md`, sin ameritar
un nuevo ciclo de `analyst-agent`.
