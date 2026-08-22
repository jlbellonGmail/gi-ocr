# Spec: Preprocesamiento documental no destructivo

## Alcance

Incluye:

- Garantizar y verificar por test que el pipeline de preparación de imagen
  (`backend/app/image_prep.py`, invocado desde
  `backend/app/capture_pipeline.py::process_document`) **nunca** modifica,
  sobrescribe ni elimina el archivo fuente persistido en `output/uploads/`
  (el que `job["file_path"]` referencia), en ningún escenario, incluido
  reprocesamiento (`POST /api/v1/jobs/{job_id}/retry`).
- Agregar una traza determinística y ordenada de las transformaciones de
  imagen aplicadas a cada documento procesado a través de
  `image_prep.prepare()` — tanto el camino de imagen (`process_document`)
  como el camino PDF (`_process_pdf`), que llama a la misma función
  `prepare()` sobre la página renderizada (ver más abajo la distinción
  exacta de qué pasos corren y se trazan en cada camino, y el criterio 12)
  — registrando como mínimo: corrección de orientación EXIF (envoltura de
  `image_prep.apply_exif_orientation`, solo camino imagen), heurística de
  orientación por contenido (`correct_orientation`, incluyendo si fue
  subordinada por EXIF), deskew, corrección de perspectiva
  (intentada/aplicada/omitida y motivo), normalización de escala (tamaño
  original vs. final / factor de escala) y un paso nuevo de normalización
  de contraste/iluminación (ver abajo). Cada entrada indica al menos:
  nombre del paso, si se aplicó (`bool`), y parámetros mínimos suficientes
  para razonar qué pasó (ángulo de deskew, factor de escala, método de
  contraste, etc.).
- Esa traza se persiste como parte de la estructura ya existente
  `processing_metadata` del resultado de un job (la misma que hoy ya lleva
  `quality_gate`, `timings`, `engine`), que ya se serializa a JSON en
  `output/jobs/{job_id}.json` vía `JobStore.save_original`. No se crea un
  nuevo endpoint HTTP: la traza queda expuesta a través de los endpoints
  existentes (`GET /api/v1/jobs/{job_id}`,
  `GET /api/v1/jobs/{job_id}/original`).
- Agregar un paso nuevo, explícito y trazado de normalización de
  contraste/iluminación a `image_prep.py` — la transformación "contraste"
  nombrada en el ítem `07` del `ROADMAP.md` que **no existe hoy** como paso
  distinto en el pipeline (`normalize_scale` ya cubre "escala"/
  "normalización" geométrica, ver "Riesgos / supuestos" sobre esta
  interpretación). Debe:
  - ser una función pura, testeable en aislamiento sobre `np.ndarray`;
  - degradar con gracia ante error (mismo patrón defensivo que `deskew`/
    `correct_perspective`: `try/except` que devuelve la imagen sin
    modificar, nunca propaga excepción);
  - incluir una salvaguarda explícita y verificable contra sobre-
    procesamiento: un documento ya bien iluminado/con buen contraste no
    debe degradarse por la normalización (ver criterios de aceptación).
- Garantía de idempotencia: reprocesar el mismo archivo original (mismo
  contenido de bytes) produce la misma traza y el mismo resultado de
  campos, sin aleatoriedad ni acumulación de pasos.
- Documentación técnica y de usuario, y enlaces de índice
  correspondientes.

Explícitamente NO incluye:

- Reabrir o cambiar el motor OCR (ADR-006), el formato `.DATA`/
  `services.ini` (ADR-007), ni la separación OCR/extracción/validación/
  storage (`docs/tecnica/arquitectura.md`).
- Reabrir `05-correccion-orientacion-exif` ni `06-calidad-captura-mobile`
  (ya cerradas): esta feature **envuelve** sus resultados en la traza, no
  cambia su lógica interna ni sus umbrales.
- El expediente único de auditoría por documento (`20-expediente-
  auditoria-documental`: checksums, manifest completo, operador,
  decisiones humanas, vínculo con `.DATA`) — esa feature, todavía no
  iniciada, tiene su propio spec y puede consumir/extender la traza de
  esta feature, pero esta feature no implementa expediente ni checksums de
  todo el ciclo de vida del documento, solo la traza del **pipeline de
  imagen** (`image_prep`).
- Una política formal de retención/almacenamiento nueva
  (`21-politica-almacenamiento-retencion`, no iniciada): esta feature no
  introduce un nuevo tipo de artefacto persistente en disco (no se guarda
  un archivo de imagen "preparada" aparte) precisamente para no requerir
  una decisión de retención nueva sin spec propio (ver "Riesgos /
  supuestos").
- Corrección/mejora de la calidad de captura en sí (blur, resolución,
  reflejos, sombras, encuadre, perspectiva como *veredicto*): eso es
  `06-calidad-captura-mobile`, ya cerrada e intacta. Esta feature no
  cambia sus 8 señales ni su veredicto de tres niveles.
- Scoring de confianza de campos ni enrutamiento a revisión humana por
  confianza: eso es `09-confianza-y-enrutamiento-hitl`.
- Cambiar qué pasos corren sobre el camino PDF (`_process_pdf`/
  `pdf_util.py`): verificado contra el código, `_process_pdf` no invoca
  `apply_exif_orientation` (el paso basado en metadata EXIF de PIL — un
  render de PDF vía `pypdfium2` no trae esa metadata) ni
  `quality_gate.evaluate` (confirmado también en
  `docs/tecnica/correccion-orientacion-exif.md`, "Fuera de alcance", y en
  `docs/tecnica/calidad-captura-mobile.md`, que documentan correctamente
  esta ausencia). Esos dos son los únicos pasos genuinamente ausentes del
  camino PDF, y esta feature no los agrega ahí. Sin embargo, `_process_pdf`
  **sí** llama a `image_prep.prepare(page_to_process["image"])` con los
  valores por defecto — la misma función compartida por el camino imagen
  — por lo que `correct_orientation` (heurística de contenido, con
  `skip=False` porque `_process_pdf` no pasa
  `exif_orientation_applied`), `deskew` (incondicional),
  `correct_perspective` (si se solicita, mismo default
  `apply_perspective=False` que en el camino imagen) y `normalize_scale`
  **sí corren sobre PDFs, igual que sobre imágenes**. No son pasos
  ausentes del camino PDF, y esta feature no cambia ese comportamiento
  existente (no agrega EXIF-por-metadata ni `quality_gate` al camino PDF,
  no altera qué transformaciones corren sobre PDF): solo instrumenta con
  traza lo que `prepare()` ya ejecuta hoy, sea cual sea el camino que lo
  invoque, de forma honesta (ver criterio 12). Caso adicional verificado
  en el código: cuando un PDF trae texto nativo suficiente y no requiere
  OCR sobre ninguna página (`_process_pdf_native`), no se renderiza
  ninguna imagen y `prepare()` nunca se invoca — ese sub-camino no genera
  ninguna entrada de traza de preparación (ver "Casos borde").
- Vista previa en vivo de calidad durante la captura (frontend de cámara):
  sin cambios, fuera de alcance igual que en `06`.
- Nueva dependencia externa de visión por computadora: se usa
  `opencv-python-headless`, ya declarada en `backend/requirements.txt` y
  ya usada en `image_prep.py`.

## Contexto

El pipeline actual (`backend/app/capture_pipeline.py::process_document`,
camino de imagen) es:

```
Image.open(path) -> apply_exif_orientation -> convert("RGB") -> np.array
  -> quality_gate.evaluate (06) -> [si reject: corta acá, sin OCR]
  -> image_prep.prepare (correct_orientation -> deskew ->
     [perspectiva opcional] -> normalize_scale)
  -> process_image (OCR two-pass ROI, ADR-006, + extracción + validación)
```

El camino PDF (`_process_pdf`) es distinto en la parte previa a
`prepare()`, pero converge en la misma función: renderiza la primera
página que necesita OCR con `pdf_util.extract_text_and_render` (sin
metadata EXIF, por eso `apply_exif_orientation` no aplica ahí) y **no**
evalúa `quality_gate` en ningún punto, pero sí llama a
`image_prep.prepare(page_to_process["image"])` con los defaults —
exactamente la misma función que el camino imagen, por lo que
`correct_orientation`, `deskew`, `correct_perspective` (si se pide) y
`normalize_scale` corren igual sobre la imagen renderizada del PDF. Si el
PDF tiene texto nativo suficiente en todas sus páginas
(`_process_pdf_native`), ninguna imagen se renderiza y `prepare()` nunca
se invoca.

El archivo fuente (`output/uploads/<nombre-aleatorio>`, ya anonimizado de
metadata EXIF identificatoria por `14-seguridad-privacidad-documentos`,
ver `backend/app/exif_privacy.py` y `main._save_upload`) **hoy ya no se
sobrescribe** en ningún punto de este camino: `Image.open(path)` solo lee,
y todas las transformaciones (`image_prep.py`) operan sobre copias en
memoria (`np.ndarray`). Es decir, la propiedad "no destructivo" sobre el
archivo en disco ya se cumple de hecho, pero **no está garantizada
explícitamente ni verificada por test**, y sobre todo **no hay ningún
registro de qué transformaciones se aplicaron** a la versión en memoria
que efectivamente vio el motor OCR: hoy, si un campo sale mal, no hay
forma de saber (sin volver a ejecutar el código y loguear a mano) si
hubo o no deskew, si se corrigió perspectiva, cuánto se escaló la imagen,
o si la orientación vino de EXIF o de la heurística de contenido — y esto
aplica tanto al camino imagen como al camino PDF, porque ambos comparten
`image_prep.prepare()`.

`docs/tecnica/correccion-orientacion-exif.md` ("Fuera de alcance") y
`docs/tecnica/calidad-captura-mobile.md` (alcance del spec `06`) ya
declaran explícitamente que "trazabilidad formal de todas las
transformaciones de imagen aplicadas (versión original vs. preparada,
manifest de transformaciones)" es responsabilidad de esta feature, `07`,
todavía no iniciada. Esta feature cierra ese pendiente: formaliza la
garantía de no-destructividad del original y agrega el registro de
transformaciones que faltaba, sin reabrir la lógica de `05`/`06`.

También agrega, porque el ítem `07` del `ROADMAP.md` la nombra
explícitamente entre las transformaciones a registrar y hoy no existe en
el código, un paso nuevo de normalización de contraste/iluminación —
distinto de `normalize_scale` (que solo cambia dimensiones, no brillo ni
contraste).

Encaja en el pipeline así: **captura (frontend) → upload/validación/
anonimización EXIF (`14`, sin cambios) → cola (`job_queue.py`) →
`capture_pipeline.process_document` → EXIF (`05`, solo camino imagen) →
control de calidad (`06`, solo camino imagen) → [NUEVO: preparación
trazada con contraste incluido, tanto camino imagen como camino PDF, vía
`image_prep.prepare()`] → OCR (`ocr_engine`, ADR-006) →
extracción/validación semántica → reporte de campos → revisión humana**.

## Criterios de aceptación

### Generales (obligatorios en todo spec)

1. Debe existir `docs/tecnica/preprocesamiento-documental-no-destructivo.md`,
   no vacío, con el algoritmo/lógica de cada paso trazado (incluido el
   nuevo paso de contraste), el formato exacto de la traza y las
   decisiones de diseño relevantes (incluida la ubicación elegida para
   persistir la traza).
2. Debe existir `docs/usuario/preprocesamiento-documental-no-destructivo.md`,
   no vacío, con el propósito de la feature (garantía de no-destructividad
   + traza de transformaciones) y al menos un ejemplo de uso HTTP completo
   (request + response) mostrando la nueva sección de traza dentro de un
   `GET /api/v1/jobs/{job_id}` de un job `ready`.
3. Debe existir `runs/07-preprocesamiento-documental-no-destructivo/decision.md`,
   con decisiones demostrables desde spec/auditoría/implementación (no
   ornamental).
4. Debe existir un enlace exacto a
   `preprocesamiento-documental-no-destructivo.md` agregado en
   `docs/tecnica/index.md`.
5. Debe existir un enlace exacto a
   `preprocesamiento-documental-no-destructivo.md` agregado en
   `docs/usuario/index.md`.

### No-destructividad del original (invariante central)

6. El archivo fuente persistido en `output/uploads/` para un job dado debe
   ser **byte-idéntico** (verificable por hash, ej. SHA-256) antes y
   después de `capture_pipeline.process_document(path, ...)`, sobre
   fixtures sintéticas de imagen (JPEG y PNG como mínimo). Verificable por
   test unitario que calcula el hash antes de llamar a `process_document`
   y lo vuelve a calcular después.
7. La misma invariante del criterio 6 debe cumplirse también tras
   `POST /api/v1/jobs/{job_id}/retry` (reprocesamiento explícito del mismo
   archivo), verificable con `TestClient` sobre `backend/app/main.py`.
8. Ningún paso de `image_prep.py` (existente o nuevo) debe escribir en
   disco sobre la ruta del archivo original; todos operan exclusivamente
   sobre `np.ndarray` en memoria — verificable por inspección del código y
   por el test de hash de los criterios 6/7 (no requiere mockear
   escritura, alcanza con verificar que el archivo no cambió).

### Traza de transformaciones

9. El resultado de `capture_pipeline.process_document` para un documento
   de tipo imagen procesado normalmente (`quality_gate.verdict` en
   `ok`/`warn`, no `reject`) debe incluir una clave nueva y estable dentro
   de `processing_metadata` (nombre exacto a definir por el builder,
   documentado en `docs/tecnica/`) cuyo valor es una lista ordenada de
   pasos, en el mismo orden en que `image_prep.prepare()` los ejecuta.
   Verificable por test que arma una fixture sintética rotada + con
   ligero skew + con bajo contraste y comprueba que la lista contiene, en
   orden: orientación EXIF, heurística de orientación por contenido
   (marcada como omitida si EXIF ya corrigió), deskew, perspectiva
   (marcada como omitida si `apply_perspective=False`, comportamiento
   default sin cambios), normalización de escala, normalización de
   contraste.
10. Cada entrada de la traza expone como mínimo `{"step": <str>, "applied":
    <bool>}` y, cuando corresponda, parámetros mínimos verificables por
    test: ángulo de rotación para deskew cuando `applied=True`, factor de
    escala (o dimensiones antes/después) para la normalización de escala,
    y un identificador de método para el paso de contraste. No se exige
    guardar el array de píxeles intermedio, solo metadata suficiente para
    reconstruir/auditar qué pasó (ver "Riesgos / supuestos" sobre por qué
    no se persiste la imagen preparada como archivo aparte).
11. Un documento con `quality_gate.verdict == "reject"` (no llega a
    `image_prep.prepare`) no debe generar una traza de preparación
    inventada: el resultado mínimo de `_quality_rejected_result` no debe
    incluir pasos con `applied` mentiroso; debe quedar ausente o con una
    lista vacía documentada explícitamente. Verificable por test.
12. El camino PDF (`_process_pdf`) llama a `image_prep.prepare()` sobre la
    imagen renderizada de la página que necesita OCR — la misma función
    que usa el camino de imagen — por lo que la traza de un documento PDF
    procesado por esa vía debe reflejar **honestamente** los pasos que
    `prepare()` efectivamente ejecuta sobre él: heurística de orientación
    por contenido (`correct_orientation`, con `skip=False` porque
    `_process_pdf` no pasa `exif_orientation_applied`), deskew
    (incondicional), corrección de perspectiva (si se solicita, mismo
    default `apply_perspective=False` que en el camino imagen),
    normalización de escala, y el nuevo paso de contraste una vez
    integrado en `prepare()` (criterio 14) — en el mismo orden y con el
    mismo formato `{"step", "applied", ...}` que en el camino imagen, con
    `applied` reflejando lo que realmente ocurrió sobre esa imagen
    renderizada (no un valor fijo ni omitido por tratarse de un PDF). En
    cambio, la traza de un PDF **no** debe contener una entrada para
    `apply_exif_orientation` (basado en metadata EXIF de PIL; el render de
    un PDF no tiene esa metadata y `_process_pdf` nunca llama a esa
    función) ni para `quality_gate` (`_process_pdf` no invoca
    `quality_gate.evaluate` en ningún punto). Verificable por test que
    procesa un PDF sintético (con imagen renderizada, no el sub-camino de
    texto nativo puro) y comprueba: (a) ausencia de entradas
    `apply_exif_orientation` y `quality_gate` en la traza/
    `processing_metadata`, y (b) presencia de entradas honestas para
    orientación por contenido, deskew, escala y contraste. Adicionalmente,
    para el sub-camino `_process_pdf_native` (PDF con texto nativo
    suficiente en todas sus páginas, sin imagen renderizada, sin llamada a
    `prepare()`), la traza debe quedar ausente o vacía, documentada
    explícitamente — mismo criterio que el caso `reject` de
    `quality_gate` (criterio 11): no se genera traza fantasma para un paso
    que nunca se ejecutó.

### Paso nuevo: normalización de contraste/iluminación

13. Debe existir una función nueva y pública en `image_prep.py` (nombre a
    definir por el builder) que reciba `np.ndarray` y devuelva
    `np.ndarray`, normalizando contraste/iluminación de forma
    determinística (mismo input produce siempre el mismo output),
    verificable por test de determinismo directo sobre la función.
14. La función del criterio 13 debe integrarse en `image_prep.prepare()`
    en un punto documentado explícitamente (antes o después de
    `normalize_scale`, con la justificación por escrito en
    `docs/tecnica/`), sin alterar el comportamiento de los pasos
    existentes (EXIF, heurística de orientación, deskew, perspectiva,
    escala) cuando se aplica sobre las mismas fixtures ya cubiertas por
    `backend/tests/test_image_prep.py` y
    `backend/tests/test_exif_orientation.py` (deben seguir pasando sin
    modificación de expectativas). Como `prepare()` es compartida por el
    camino imagen y el camino PDF, este paso corre y se traza en ambos por
    igual (ver criterio 12); esta feature no introduce una rama de código
    que distinga "viene de PDF" para saltarse el contraste ni ningún otro
    paso de `prepare()`.
15. Salvaguarda contra destrucción de ROI/datos (regla explícita del
    ítem `07` del `ROADMAP.md`: "evitando que una mejora visual destruya
    ROI o datos útiles"): debe existir al menos un test que demuestre que,
    sobre una fixture sintética ya bien iluminada/con buen contraste (por
    ejemplo, el fixture GAS de referencia o equivalente sintético), el
    paso de contraste **no** degrada una métrica proxy verificable (por
    ejemplo, la varianza del Laplaciano no cae por debajo de un umbral
    relativo respecto de la imagen sin normalizar, o el texto extraído por
    OCR sobre la versión normalizada es igual o mejor que sobre la versión
    sin normalizar). Debe existir también un test de degradación
    controlada: sobre una fixture sintética con iluminación deficiente
    (oscurecida o con bajo contraste simulado), el paso mejora
    (o al menos no empeora) esa misma métrica proxy.
16. Regla de dominio OCR (el ítem `07` toca directamente el pipeline que
    alimenta la extracción de campos, aunque no agrega campos nuevos):
    declarar explícitamente, en `docs/tecnica/`, para el paso de
    contraste:
    - **Campo(s) potencialmente afectados**: todos los campos configurados
      del template GAS (n° cliente, nro medidor, periodo, a pagar hasta,
      importe — ver ADR-004), porque el contraste se aplica a la imagen
      completa antes de OCR, no a una ROI específica.
    - **Tipo de documento/servicio probado**: `GAS` (template existente).
    - **Fixture usada**: sintética, generada en memoria o reutilizando
      `backend/tests/fixtures/gas_sample.jpg` si ya es sintética (no se
      suben ni derivan comprobantes reales, ver reglas de dominio OCR de
      `AGENTS.md`).
    - **Salida esperada**: `validated_fields` resultantes de
      `capture_pipeline.process_document` sobre la fixture con el pipeline
      actualizado (contraste incluido) debe ser igual o mejor (mismo
      conjunto de campos válidos, ningún campo antes válido pasa a
      `missing`/`rejected`) que sobre el pipeline sin el paso de
      contraste.
    - **Validación semántica aplicada**: los validadores existentes de
      `backend/app/validators.py`, sin cambios.
    - **Falsos positivos evitados**: la normalización de contraste no debe
      "inventar" dígitos ni deformar números por sobre-procesamiento
      (verificable comparando texto extraído carácter a carácter en los
      campos numéricos entre la versión con y sin el paso de contraste
      sobre la fixture de referencia).

### Idempotencia y no regresión

17. Reprocesar el mismo archivo original (mismos bytes) dos veces produce
    la misma traza (mismo contenido, mismo orden) y el mismo conjunto de
    `validated_fields`/`rejected_fields`/`missing_fields`, sin
    aleatoriedad — verificable por test análogo a
    `test_evaluate_is_deterministic` de `06`.
18. La suite completa de tests existente (`backend/tests/`, `pytest -q`)
    sigue en verde sin modificar expectativas de tests de `05`/`06`
    (`test_exif_orientation.py`, `test_quality_gate.py`,
    `test_image_prep.py`), salvo los cambios estrictamente necesarios para
    reflejar la nueva clave de traza en `processing_metadata` (si algún
    test existente compara el diccionario completo de `processing_metadata`
    por igualdad exacta, debe actualizarse para tolerar la clave nueva,
    documentado en el `test-report`).

## Casos borde a contemplar

- Imagen ya bien orientada (sin tag EXIF o `Orientation == 1`): la
  heurística de contenido no debe rotarla de más, y la traza debe reflejar
  `applied: false` con motivo "no fue necesario" — no `applied: true`
  sobre una transformación nula.
- Documento con baja calidad ya rechazado por `quality_gate` (`verdict ==
  reject`, `06`): no debe llegar a `image_prep.prepare`, no debe gastar
  cómputo del nuevo paso de contraste, y no debe generar traza fantasma
  (ver criterio 11).
- Fallo de una transformación individual (ej. el paso de contraste no
  puede procesar una imagen degenerada, o `deskew` recibe una imagen sin
  suficiente contenido): debe degradar con gracia devolviendo la imagen
  de entrada sin modificar (mismo patrón que `deskew`/`correct_perspective`
  ya existentes), registrando en la traza `applied: false` con una razón,
  **nunca** debe: (a) devolver una imagen corrupta/vacía, (b) tirar
  excepción que tumbe el job a `failed` por un problema exclusivamente del
  paso de mejora visual, ni (c) descartar el original.
- Reprocesamiento idempotente del mismo original (`retry`): mismo trace,
  mismos campos, sin acumular pasos ni duplicar entradas.
- Formato de imagen no soportado o corrupto que ya falla en `Image.open`
  antes de esta feature: sigue fallando igual (`status == "failed"`), sin
  cambios de comportamiento — no se le exige traza a un job que nunca
  llegó a `image_prep`.
- Imagen degenerada que pasa `quality_gate` en `warn` (no `reject`) pero
  es casi toda negra/blanca o de 1 solo píxel tras escalar: el nuevo paso
  de contraste no debe lanzar excepción ni "inventar" señal a partir de
  ruido — debe degradar igual que el resto de pasos.
- Valores ambiguos de traza para perspectiva (opt-out por defecto,
  `apply_perspective=False`): debe distinguirse explícitamente entre
  "omitido porque no se pidió" (`apply_perspective=False`) y "intentado
  pero no se encontró cuadrilátero claro" (`apply_perspective=True` pero
  `find_document_contour` devolvió `None`) — ambos casos existen hoy en el
  código y no deben colapsarse en un mismo significado de `applied:
  false`.
- PDF con imagen renderizada (`_process_pdf`, camino normal): la traza
  **no** debe contener entradas de `apply_exif_orientation` ni de
  `quality_gate` (genuinamente no invocados sobre PDF), pero **sí** debe
  contener entradas honestas de orientación por contenido, deskew,
  perspectiva (si se solicita), escala y contraste, porque esos pasos
  corren igual que sobre imágenes al compartir `image_prep.prepare()` —
  ver criterio 12. No colapsar este caso con "PDF nunca se traza".
- PDF con texto nativo puro (`_process_pdf_native`, sin ninguna página
  que requiera OCR): no se renderiza imagen y `image_prep.prepare()` nunca
  se invoca — la traza de preparación debe quedar ausente o vacía,
  documentada explícitamente, igual que el caso `reject` de
  `quality_gate` (criterio 11). No inventar una traza con `applied: false`
  para pasos que ni siquiera se evaluaron.
- Job cuyo archivo original ya fue purgado por `retention.py` antes de un
  `retry`: comportamiento sin cambios (ya falla con `FileNotFoundError`
  hoy en `job_queue.py::_process`) — no es un caso nuevo introducido por
  esta feature, solo debe verificarse que sigue igual (no debe intentar
  "reconstruir" un original inexistente a partir de la traza).

## Riesgos / supuestos

- **Dónde vive la traza**: se registra como metadata dentro de
  `processing_metadata` (extensión del mismo diccionario que ya usan
  `quality_gate`, `timings`, `engine`), que ya se persiste como JSON en
  `output/jobs/{job_id}.json` vía `JobStore.save_original` — **no** se crea
  un archivo de imagen "preparada" nuevo en disco. "Generando versiones
  preparadas trazables" (texto del ítem `07` del `ROADMAP.md`) se
  interpreta como "la generación de la versión preparada queda
  documentada/trazada en metadata determinística", no como "se persiste un
  binario nuevo por job". Motivo: evita introducir un nuevo tipo de
  artefacto persistente con implicaciones de retención propias (tarea de
  `21-politica-almacenamiento-retencion`, no iniciada, ver
  `backend/app/retention.py` que hoy no conoce ningún directorio
  `prepared/`) y evita duplicar el alcance de `20-expediente-auditoria-
  documental` (expediente completo con checksums/manifest de todo el
  ciclo de vida). Si el reviewer considera que "no destructivo" exige
  persistir la imagen preparada como archivo binario aparte, debe
  objetarlo explícitamente como decisión de arquitectura nueva — no se
  asume en silencio acá.
- **"Contraste" como transformación nueva**: el ítem de `ROADMAP.md` nombra
  "EXIF, deskew, perspectiva, escala, contraste y normalización" como las
  transformaciones a registrar. Se interpreta "normalización" como
  sinónimo de lo que ya hace `image_prep.normalize_scale` (escala/tamaño,
  sin cambios de comportamiento, solo se agrega su trazado), y "contraste"
  como una transformación que **no existe hoy** en el pipeline y que esta
  feature agrega explícitamente, porque no tendría sentido pedir
  "registrar" algo que no ocurre. Si el reviewer prefiere que esta feature
  **no** agregue ninguna transformación de imagen nueva y se limite a
  trazar las 4 ya existentes (EXIF, heurística de orientación, deskew,
  perspectiva, escala), dejando "contraste" fuera para una iteración
  futura, debe objetarlo explícitamente — es una decisión de alcance no
  trivial que cambia el tamaño de esta feature.
- **Nombres exactos de claves/funciones**: el nombre de la clave nueva
  dentro de `processing_metadata` y el nombre de la función de contraste
  en `image_prep.py` quedan como decisión de implementación del builder,
  siempre que sean estables, testeados y documentados en
  `docs/tecnica/preprocesamiento-documental-no-destructivo.md` — no se
  fuerza diseño de código en este spec.
- **Qué significa "original" en esta feature**: se refiere al archivo ya
  persistido en `output/uploads/` **después** de la anonimización de
  metadata EXIF identificatoria de `14-seguridad-privacidad-documentos`
  (`main._save_upload` → `exif_privacy.anonymize_upload_bytes`), no a los
  bytes crudos tal como salieron del dispositivo del usuario antes de
  llegar al servidor. Esa anonimización ya es una decisión de arquitectura
  previa y cerrada (privacidad del titular del documento); esta feature no
  la reabre ni la contradice. "No destructivo" en esta feature significa:
  desde el momento en que el archivo queda persistido en
  `output/uploads/`, el pipeline de OCR/preparación (`image_prep`/
  `capture_pipeline`) nunca vuelve a tocarlo.
- **PDF y `image_prep.prepare()` comparten instrumentación de traza, no
  hay rama nueva por tipo de documento**: dado que `_process_pdf` llama a
  `prepare()` con los mismos defaults que el camino imagen (verificado en
  `backend/app/capture_pipeline.py`), esta feature instrumenta la traza
  **dentro** de `prepare()` una sola vez, y esa instrumentación aplica por
  igual a ambos caminos que la invocan. La feature no introduce un
  parámetro nuevo (ej. `is_pdf`) para que `prepare()` se comporte distinto
  según el llamador — eso sería una decisión de diseño no pedida por
  `ROADMAP.md` ni necesaria para resolver la contradicción entre los
  criterios 12 y 14, y agregaría una superficie de comportamiento
  condicional nueva sin justificación. Si el reviewer o el builder
  consideran que el camino PDF necesita suprimir explícitamente algunas
  entradas de traza (por ejemplo, para no confundir al frontend), debe
  proponerse como decisión de diseño explícita en `docs/tecnica/`, no
  asumirse en silencio.
- **Verificación de imprecisión en docs de features previas (pedido
  explícito de auditoría)**: se revisó `docs/tecnica/correccion-
  orientacion-exif.md` (sección "Fuera de alcance") y
  `docs/tecnica/calidad-captura-mobile.md` (sección "Fuera de alcance" y
  el punto de integración del pipeline) contra el código real de
  `backend/app/capture_pipeline.py` y `backend/app/image_prep.py`. Ambos
  documentos son **precisos**: describen correctamente que
  `apply_exif_orientation` y `quality_gate.evaluate` no se invocan en el
  camino PDF, y que "deskew, corrección de perspectiva, normalización de
  escala/contraste... siguen sin cambios de comportamiento" (es decir,
  siguen corriendo igual, no que estén ausentes). La imprecisión detectada
  por el reviewer existía únicamente en la versión anterior de este spec
  (`07`), no en esos documentos técnicos previos. No se requiere ninguna
  corrección de redacción en `05`/`06`, ni reabrir esas features.
- **Riesgo de calibración de la salvaguarda de contraste**: igual que en
  `06-calidad-captura-mobile`, cualquier umbral/métrica proxy usada para
  verificar que el contraste "no destruye legibilidad" (criterio 15) se
  calibra sobre fixtures sintéticas, no fotos reales de celular — mismo
  riesgo de calibración ya aceptado y documentado en esa feature, no
  exclusivo de esta.
- **Riesgo de regresión sobre el fixture GAS de referencia**: agregar un
  paso de contraste nuevo, aunque conservador y con salvaguardas, introduce
  superficie de regresión sobre la extracción de campos. El criterio 16
  exige verificarlo explícitamente, pero la cobertura será tan buena como
  los fixtures sintéticos disponibles hoy — la suite de regresión
  permanente y sistemática con fixtures/expected outputs por proveedor es
  responsabilidad de `08-regresion-dataset-ocr`, todavía no iniciada.
- **No reabre ADR**: motor OCR (ADR-006), formato `.DATA`/`services.ini`
  (ADR-007), separación OCR/extracción/validación/storage
  (`docs/tecnica/arquitectura.md`) quedan sin cambios; esta feature es
  estrictamente aditiva sobre `image_prep.py`/`capture_pipeline.py`.
