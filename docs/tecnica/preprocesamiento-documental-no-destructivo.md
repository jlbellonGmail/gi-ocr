# Preprocesamiento documental no destructivo

## Propósito

`backend/app/image_prep.py`/`backend/app/capture_pipeline.py` ya
preparaban cada documento antes de OCR (corrección de orientación EXIF,
heurística de orientación por contenido, deskew, perspectiva opcional,
normalización de escala), y ya operaban de hecho sin modificar el archivo
original en disco — pero ninguna de esas dos propiedades estaba **probada
explícitamente** ni **registrada**: si un campo salía mal, no había forma
de saber, sin reinstrumentar el código a mano, qué transformaciones se
aplicaron realmente sobre la imagen que vio el motor OCR.

Esta feature agrega dos cosas, sin reabrir la lógica de `05-correccion-
orientacion-exif` ni `06-calidad-captura-mobile`:

1. **Garantía verificada por test** de que el archivo persistido en
   `output/uploads/` nunca se modifica, en ningún camino (imagen, PDF,
   incluido `POST /api/v1/jobs/{job_id}/retry`).
2. **Traza determinística** de las transformaciones efectivamente
   aplicadas, dentro de `processing_metadata.preparation_trace`, más un
   paso nuevo de normalización de contraste/iluminación que no existía en
   el pipeline.

## No-destructividad del original

`capture_pipeline.process_document` sólo **lee** el archivo
(`Image.open(path)` en el camino imagen, `pdfium.PdfDocument(path)` en el
camino PDF): ninguna de las dos rutas vuelve a abrir `path` en modo
escritura. Todas las transformaciones de `image_prep.py` (existentes y la
nueva) reciben y devuelven `np.ndarray` en memoria — no hay ningún
`cv2.imwrite`/`Image.save` sobre la ruta de entrada en todo el módulo.

Esto ya era así **antes** de esta feature (confirmado en el spec contra el
código); lo que agrega esta feature es la verificación explícita:

- `backend/tests/test_preparation_trace.py::test_process_document_does_not_modify_original_file`
  (parametrizado `.jpg`/`.png`) y
  `test_process_document_does_not_modify_original_pdf`: hash SHA-256 del
  archivo antes y después de `capture_pipeline.process_document(path)`.
- `test_retry_endpoint_does_not_modify_original_file`: mismo hash
  antes/después, pero disparado vía `TestClient` real sobre
  `POST /api/v1/jobs/{job_id}/retry` (no una llamada directa a Python). Se
  usa un job en estado `needs_new_photo` (rechazado por `quality_gate`)
  porque `JobQueue.retry()` sólo bloquea los estados `ready`/`confirmed`
  (no se puede reintentar un job ya `ready` para este test) — el archivo
  original (`job["file_path"]`, bajo `output/uploads/`) se hashea antes y
  después del `retry`.

## Dónde vive la traza

`processing_metadata.preparation_trace`: una lista ordenada de dicts
`{"step": <str>, "applied": <bool>, ...parámetros}`, agregada al mismo
diccionario `processing_metadata` que ya llevaba `quality_gate`, `timings`
y `engine` — se serializa igual, sin cambios, en `output/jobs/{job_id}.json`
vía `JobStore.save_original`, y se expone sin ningún endpoint nuevo a
través de `GET /api/v1/jobs/{job_id}` y `GET /api/v1/jobs/{job_id}/original`.

No se persiste una imagen "preparada" nueva como archivo aparte (ver
`runs/07-preprocesamiento-documental-no-destructivo/spec.md`, "Riesgos /
supuestos"): la traza es metadata suficiente para auditar qué pasó, sin
introducir un tipo de artefacto persistente nuevo con implicaciones de
retención propias (responsabilidad futura de
`21-politica-almacenamiento-retencion`, no iniciada).

## Formato de cada paso

Cada entrada tiene como mínimo `{"step": str, "applied": bool}`, más
parámetros específicos por paso:

| Paso | Cuándo aparece | Parámetros además de `step`/`applied` |
|---|---|---|
| `apply_exif_orientation` | Sólo camino imagen (nunca en PDF) | `reason` |
| `correct_orientation` | Siempre que corre `image_prep.prepare()` | `reason`, y `rotation` (`"90_cw"`/`"90_ccw"`) o `angle_deg` cuando aplica; `error: true` si degradó por excepción |
| `deskew` | Siempre que corre `prepare()` | `reason`, `angle_deg` (estimado, aplicado o no) |
| `correct_perspective` | Siempre que corre `prepare()` | `reason`, `requested` (bool: se pidió `apply_perspective=True`), `width`/`height` cuando `applied=True` |
| `normalize_scale` | Siempre que corre `prepare()` | `reason`, `original_size: [w, h]`, `final_size: [w, h]`, `scale_factor` |
| `normalize_contrast` | Siempre que corre `prepare()` | `reason`, `method` (`"clahe_lab_l_channel"`), `std_before`/`std_after`, y `sharpness_before`/`sharpness_after` cuando se llegó a evaluar la salvaguarda |

`apply_exif_orientation` se agrega **fuera** de `image_prep.prepare()`, en
`capture_pipeline.process_document` (camino imagen), justo después de
llamarlo — es un paso previo a `prepare()`, no interno a esa función (ver
`docs/tecnica/correccion-orientacion-exif.md`). Los demás cinco pasos
corren **dentro** de `prepare()` y se registran ahí mismo.

## Implementación: `_*_impl` internas + `prepare(..., trace=...)`

Las funciones públicas ya existentes (`correct_orientation`, `deskew`,
`correct_perspective`, `normalize_scale`) y la nueva (`normalize_contrast`)
**mantienen su firma exacta** (`np.ndarray -> np.ndarray`, más los
parámetros que ya tenían): quien ya las llama directo (otros tests,
scripts) no se ve afectado. Cada una delega en una función interna
`_*_impl(...)` que calcula la misma transformación y además devuelve un
`dict` de metadata:

```python
def _deskew_impl(image_np: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
    ...
    return rotated, {"applied": True, "reason": "...", "angle_deg": 2.3}

def deskew(image_np: np.ndarray) -> np.ndarray:
    img, _meta = _deskew_impl(image_np)
    return img
```

`image_prep.prepare(image_np, ..., trace: Optional[list] = None)` invoca
directamente las `_*_impl` (no las funciones públicas envolventes), agrega
cada `meta` a `trace` en el orden de ejecución, y devuelve únicamente la
imagen final — sin cambiar su tipo de retorno respecto de antes de esta
feature. Si `trace` es `None` (comportamiento por defecto, sin cambios
para quien no pide traza), no se construye ninguna lista ni se paga costo
extra de metadata más allá de lo que ya calculaba cada paso. Esto evita
duplicar cómputo entre "hacer la transformación" y "calcular qué
reportar", y evita agregar una rama de comportamiento condicional nueva
por tipo de llamador (ver más abajo, "Camino PDF").

`capture_pipeline.process_document` arma la lista `trace`, agrega primero
la entrada de `apply_exif_orientation` (sólo camino imagen) y se la pasa a
`image_prep.prepare(..., trace=trace)`; al terminar, adjunta
`result["processing_metadata"]["preparation_trace"] = trace`.

## Camino PDF: misma función, misma traza honesta

`capture_pipeline._process_pdf` llama a **la misma** `image_prep.prepare()`
sobre la imagen renderizada de la página que necesita OCR
(`pdf_util.extract_text_and_render`), con los mismos valores por defecto
que el camino imagen (`apply_perspective=False`,
`exif_orientation_applied=False` porque nunca se pasa ese argumento). Esto
significa que `correct_orientation` (con `skip=False`, la heurística de
contenido corre igual), `deskew` (incondicional), `correct_perspective`
(si se pide) y `normalize_scale`/`normalize_contrast` **sí corren y se
trazan igual que sobre una imagen**, porque comparten la misma función.

Los únicos dos pasos que genuinamente **nunca** se invocan en el camino
PDF son `apply_exif_orientation` (basado en metadata EXIF de PIL — un
render de PDF vía `pypdfium2` no trae esa metadata) y `quality_gate.evaluate`
(`_process_pdf` no lo llama en ningún punto). La traza de un PDF, entonces,
tiene exactamente 5 entradas (`correct_orientation`, `deskew`,
`correct_perspective`, `normalize_scale`, `normalize_contrast`), nunca 6,
y `processing_metadata` de un PDF nunca tiene clave `quality_gate`.

Esta feature **no** introduce un parámetro `is_pdf` (o similar) en
`prepare()` para que se comporte distinto según quién la llama: la
instrumentación de traza vive una sola vez dentro de `prepare()` y aplica
por igual a ambos caminos que la invocan, tal como ya declaraba el spec en
"Riesgos / supuestos" (evita una superficie de comportamiento condicional
nueva no pedida por `ROADMAP.md`).

## Paso nuevo: normalización de contraste/iluminación

### Por qué después de `normalize_scale`

`prepare()` ejecuta `normalize_contrast` **después** de `normalize_scale`
(orientación → deskew → perspectiva opcional → escala → contraste), en
línea con el orden que el propio criterio 9 del spec describe. Motivo:
opera sobre la imagen ya en su tamaño final (≤1600px de lado mayor), tanto
por costo de cómputo (CLAHE sobre una imagen más chica es más rápido) como
porque es exactamente la imagen que efectivamente ve el motor OCR — no
tiene sentido reportar contraste sobre una resolución intermedia que luego
se reescala.

### Algoritmo: CLAHE sobre el canal L de LAB

`image_prep.normalize_contrast(image_np: np.ndarray) -> np.ndarray`
(función pública, pura, misma firma que `deskew`/`correct_perspective`):

1. Convierte a LAB (`cv2.COLOR_RGB2LAB`), separa el canal `L`
   (luminosidad) de los canales de color `a`/`b`.
2. Aplica `cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))` sólo sobre
   `L` — CLAHE (Contrast Limited Adaptive Histogram Equalization) mejora
   contraste local por bloques con un límite de amplificación, mucho más
   conservador que una ecualización de histograma global (que sí puede
   "inventar" contraste falso o quemar zonas).
3. Recompone LAB → RGB con los canales de color originales intactos
   (`normalize_contrast` nunca cambia el balance de color, sólo
   luminosidad/contraste).

Es **determinístico** por construcción (sin aleatoriedad en ningún paso):
`normalize_contrast(x) == normalize_contrast(x)` siempre, verificado por
`test_normalize_contrast_is_deterministic`.

### Salvaguarda contra sobre-procesamiento (criterio 15 del spec)

En vez de decidir "aplicar o no" en base a un umbral fijo sobre el
contraste global de la imagen completa, la implementación usa un patrón
**intentar-y-verificar**: siempre calcula la versión mejorada, mide una
métrica proxy de nitidez/legibilidad antes y después (varianza del
Laplaciano, `cv2.Laplacian(gray, cv2.CV_64F).var()` — la misma métrica
que ya usa `quality_gate._blur_signal`), y sólo **acepta** la mejora si no
degrada esa métrica más de un margen de seguridad (`_CONTRAST_SHARPNESS_SAFETY_MARGIN
= 0.9`, tolera hasta un 10 % de caída). Si la degradaría más, descarta el
resultado de CLAHE y devuelve la imagen de entrada sin modificar
(`applied: False`, con el motivo explícito).

**Por qué no un umbral de "contraste global" (desvío estándar) como único
criterio**: se calibró inicialmente contra `backend/tests/fixtures/gas_sample.jpg`
y se descubrió que esa fixture (fondo blanco dominante con texto disperso,
como la mayoría de comprobantes reales) tiene un desvío estándar de
intensidad global **bajo** (`~12.3` sobre 0-255) *aunque el documento está
perfectamente iluminado* — el fondo blanco domina la mayoría de los
píxeles, así que la dispersión global no es un buen proxy de "qué tan bien
iluminado está el texto". Un umbral fijo sobre ese valor habría disparado
CLAHE sistemáticamente sobre documentos ya buenos. La varianza del
Laplaciano, en cambio, mide nitidez de bordes donde efectivamente hay
contenido (texto), y funciona igual de bien sobre fondos dominantemente
blancos que sobre imágenes más densas.

Sólo se mantiene un chequeo adicional, barato, antes de intentar CLAHE:
si el desvío estándar global es menor a `_CONTRAST_MIN_STD_TO_ATTEMPT =
1.0` (imagen casi perfectamente plana, sin ninguna variación de
intensidad — por ejemplo, una página de PDF completamente en blanco), no
se intenta nada: no hay ninguna estructura real que mejorar, e intentarlo
arriesgaría amplificar ruido de compresión JPEG sobre una superficie
uniforme e "inventar" textura donde no la hay.

Calibración empírica del margen de seguridad (`0.9`), medida sobre
fixtures de este repo:

| Fixture | Nitidez antes | Nitidez después de CLAHE | Variación |
|---|---|---|---|
| `gas_sample.jpg` (ya bien iluminado) | 1093.7 | 1073.5 | **-1.8 %** (dentro del margen, se acepta) |
| `gas_sample.jpg` oscurecido artificialmente (`*0.4 + 60`) | 175.9 | 232.5 | **+32 %** (mejora, se acepta) |
| Documento sintético de bajo contraste (fondo 140, texto 120) | 29.7 | 81.7 | **+175 %** (mejora, se acepta) |

Sobre el fixture ya bien iluminado la variación real es una caída leve
(-1.8 %), muy por debajo del 10 % tolerado — CLAHE con `clipLimit=2.0` es
en la práctica un cambio conservador incluso cuando se aplica sin
necesidad real; la salvaguarda existe para el caso (verificado por test
con `unittest.mock.patch` sobre `image_prep._apply_clahe`,
`test_normalize_contrast_safety_guard_discards_degrading_enhancement`) en
que una mejora sí degradaría la nitidez de forma medible.

### Parámetros reportados en la traza

```json
{
  "step": "normalize_contrast",
  "applied": true,
  "method": "clahe_lab_l_channel",
  "reason": "contraste normalizado (CLAHE sobre canal L de LAB)",
  "std_before": 4.94,
  "std_after": 6.02,
  "sharpness_before": 175.89,
  "sharpness_after": 232.49
}
```

Cuando `applied: false`, el `reason` distingue explícitamente los tres
motivos posibles: `"imagen casi uniforme..."` (caso degenerado, no se
intentó nada), `"mejora habría degradado la nitidez..."` (se intentó, la
salvaguarda la descartó) y `"sin cambios efectivos sobre los píxeles"`
(se intentó, pasó la salvaguarda, pero el resultado fue bit-a-bit idéntico
al original).

## Regla de dominio OCR (paso de contraste)

- **Campo(s) potencialmente afectados**: todos los campos configurados del
  template `LITORAL_GAS`/`GAS` (`provider`, `comprobante`, `fecha_emision`,
  `vencimiento`, `cliente`, `periodo`, `total`, ver
  `backend/app/templates/providers.py`), porque `normalize_contrast` se
  aplica sobre la imagen completa antes de OCR, no sobre una ROI
  específica.
- **Tipo de documento/servicio probado**: `GAS`, usando
  `backend/tests/fixtures/gas_sample.jpg` (ya sintético, reutilizado de
  `05`/`06`) — no se sube ni deriva ningún comprobante real.
- **Salida esperada**: comparado con el pipeline sin el paso de contraste
  (reconstruido manualmente llamando `correct_orientation` → `deskew` →
  `normalize_scale`, sin `normalize_contrast`, replicando el orden previo
  a esta feature), el pipeline con contraste produce **el mismo texto OCR
  en las secuencias de dígitos** (`\d+` extraídos de `raw_ocr_text`) y la
  misma forma de `validated_fields`/`rejected_fields`/`missing_fields`.
  Nota: `gas_sample.jpg` en particular no incluye el texto "Litoral Gas"
  necesario para que `classify_keywords` lo asigne a un proveedor conocido
  (queda `provider_detected: "UNKNOWN"` con o sin el paso de contraste,
  comportamiento **preexistente e inalterado** por esta feature, verificado
  contra el código sin este cambio) — por eso la comparación relevante
  para la regla de dominio es sobre el texto/dígitos reconocidos
  (`raw_ocr_text`), no sobre `validated_fields` (que ya estaban vacíos
  antes de esta feature sobre este fixture puntual, por un motivo
  independiente y anterior a esta feature).
- **Validación semántica aplicada**: `backend/app/validators.py`, sin
  cambios de código.
- **Falsos positivos evitados**: verificado por
  `test_gas_fixture_contrast_step_preserves_fields_and_digits`, que extrae
  todas las secuencias de dígitos (`re.findall(r"\d+", ...)`) de
  `raw_ocr_text` con y sin el paso de contraste sobre el mismo fixture, y
  exige que sean **exactamente iguales, en el mismo orden** — el paso de
  contraste no debe inventar ni deformar ningún dígito (número de cliente,
  medidor, importe, fechas).

## Casos borde

- **`quality_gate.verdict == "reject"`** (camino imagen): corta **antes**
  de `image_prep.prepare()`. `_quality_rejected_result` no incluye la
  clave `preparation_trace` en absoluto (ausente, no una lista vacía ni
  con pasos `applied` inventados) — verificado por
  `test_quality_reject_result_has_no_preparation_trace`.
- **PDF con imagen renderizada** (`_process_pdf`, camino normal): la traza
  tiene 5 entradas honestas (`correct_orientation`, `deskew`,
  `correct_perspective`, `normalize_scale`, `normalize_contrast`), nunca
  `apply_exif_orientation` ni ninguna referencia a `quality_gate` —
  verificado por `test_pdf_with_rendered_image_trace_excludes_exif_and_quality_gate`.
- **PDF con texto nativo puro** (`_process_pdf_native`, ninguna página
  requiere OCR): nunca se renderiza imagen, `image_prep.prepare()` nunca
  se invoca, la clave `preparation_trace` queda ausente — mismo criterio
  que el caso `reject` — verificado por
  `test_pdf_native_text_has_no_preparation_trace` sobre un PDF sintético
  construido a mano (sintaxis PDF cruda con fuente estándar Helvetica, sin
  depender de una API de autoría de texto que esta versión de `pypdfium2`
  no expone).
- **Fallo individual de un paso** (por ejemplo, `normalize_contrast` sobre
  una imagen degenerada): cada `_*_impl` está envuelta en su propio
  `try/except` y degrada devolviendo la imagen de entrada sin modificar,
  con `applied: False` y `error: true` en la traza — nunca propaga la
  excepción hacia `capture_pipeline`/`job_queue` (el job no cae a
  `failed` por un problema exclusivo de un paso de mejora visual). Cubierto
  por `test_normalize_contrast_never_raises_on_degenerate_input` (imagen
  `1x1` y superficie perfectamente uniforme).
- **Perspectiva: "omitido" vs. "intentado sin encontrar cuadrilátero"**:
  distinguidos explícitamente en la traza mediante la clave `requested`
  (`False` cuando `apply_perspective=False`, no se llama a la
  implementación en absoluto; `True` cuando sí se pidió, sin importar si
  `applied` terminó siendo `True` o `False`) — verificado por
  `test_trace_perspective_not_requested_is_distinct_from_attempted_not_found`
  y `test_trace_perspective_applied_when_requested_and_quad_detected`.
- **Orientación ya correcta**: la heurística de contenido no rota de más;
  la traza refleja `applied: false` con motivo `"no fue necesario"`, nunca
  `applied: true` sobre una transformación nula.
- **Idempotencia / reprocesamiento**: reprocesar el mismo archivo original
  produce la misma traza (mismo contenido, mismo orden) y el mismo
  conjunto de `validated_fields`/`rejected_fields`/`missing_fields`, sin
  aleatoriedad — verificado por `test_reprocessing_same_original_is_idempotent`,
  análogo a `test_evaluate_is_deterministic` de `06`.
- **Job cuyo original ya fue purgado por `retention.py` antes de un
  `retry`**: sin cambios de comportamiento respecto de antes de esta
  feature (`FileNotFoundError` en `job_queue.py::_process`, no relacionado
  con `image_prep`).

## Ubicación del código

- `backend/app/image_prep.py`: `_correct_orientation_impl`,
  `_deskew_impl`, `_correct_perspective_impl`, `_normalize_scale_impl`,
  `_normalize_contrast_impl` (metadata + transformación); `deskew`,
  `correct_perspective`, `normalize_scale`, `normalize_contrast`,
  `correct_orientation` (envoltorios públicos sin cambio de firma);
  `_apply_clahe`, `_contrast_metric`, `_sharpness_metric` (helpers del
  paso de contraste); `_append_step` (helper de traza); `prepare(...,
  trace=None)`.
- `backend/app/capture_pipeline.py::process_document`: arma la entrada
  `apply_exif_orientation` y pasa `trace=` a `image_prep.prepare()` en el
  camino imagen; adjunta `preparation_trace` al resultado sólo cuando
  `prepare()` efectivamente corrió.
- `backend/app/capture_pipeline.py::_process_pdf`: mismo patrón para el
  camino PDF (sin entrada de EXIF).
- `backend/tests/test_preparation_trace.py`: toda la cobertura de esta
  feature (no-destructividad, traza, contraste, idempotencia).

## Ver también

- [docs/tecnica/correccion-orientacion-exif.md](correccion-orientacion-exif.md):
  detalle de `apply_exif_orientation`/`correct_orientation` (sin cambios
  de lógica en esta feature, sólo instrumentados con traza).
- [docs/tecnica/calidad-captura-mobile.md](calidad-captura-mobile.md):
  `quality_gate.evaluate`, veredicto `reject` (sin cambios de lógica en
  esta feature).
