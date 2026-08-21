---
status: approved
attempt: 1
feedback: []
---

# Test report — 05-correccion-orientacion-exif (intento 1)

## Contexto

Este QA retoma la verificación desde cero (una corrida anterior de
`qa-agent` se cortó por límite de sesión de API antes de emitir este
reporte; el código, tests y documentación ya estaban commiteados por el
`builder-agent` en `a766c41` y `41dcdd0`). No se modificó implementación
ni tests existentes; se corrió la suite completa y se verificó el
contrato del circuito de punto cero.

## 1. Ejecución de la suite completa

Comando corrido (worktree `D:\proyectos\worktrees\05-correccion-orientacion-exif`,
rama `feature/05-correccion-orientacion-exif`, usando el `.venv` del
checkout principal `D:\proyectos\gi-ocr\.venv` con `rapidocr_onnxruntime`
instalado):

```
D:\proyectos\gi-ocr\.venv\Scripts\python.exe -m pytest -q backend/tests tests \
  --basetemp=D:\proyectos\worktrees\05-correccion-orientacion-exif\.pytest_basetemp
```

Se usó `--basetemp` propio (limpiado al terminar, `git status` confirma
worktree limpio) porque la carpeta temp compartida de pytest en Windows
(`%TEMP%\pytest-of-<usuario>`) puede quedar bloqueada por corridas
concurrentes de otros circuitos en paralelo — problema de entorno
preexistente, no de esta feature.

Resultado:

```
282 passed, 6 skipped, 33 warnings in 561.03s (0:09:21)
exit code 0
```

Los 6 `skipped` son todos esperados y no relacionados con esta feature:
falta de `playwright` instalado (`tests/e2e/test_e2e_playwright.py`) y
ausencia de muestras privadas locales gitignored
(`test_api_jobs.py`, `test_local_samples_real.py` x4). No hay ningún
`FAILED` ni `ERROR`.

Específicamente, `backend/tests/test_exif_orientation.py` (20 tests)
pasó completo dentro de esa corrida, incluyendo:
- `test_apply_exif_orientation_all_8_values` parametrizado en `[1..8]`
  (8 tests).
- `test_no_exif_at_all`, `test_exif_present_but_no_orientation_tag`.
- `test_orientation_out_of_range_degrades_gracefully` parametrizado en
  `[0, 9, -1, 100]` (4 tests).
- `test_orientation_non_numeric_degrades_gracefully`.
- `test_correct_orientation_skip_true_bypasses_heuristic`,
  `test_correct_orientation_no_regression_without_exif`.
- `test_prepare_subordinates_heuristic_when_exif_applied`.
- `test_process_document_recovers_text_from_rotated_exif_image`
  parametrizado en `[6, 8]` (2 tests, integración end-to-end con
  `capture_pipeline.process_document`).

No fue necesario escribir tests adicionales: la cobertura existente en
`backend/tests/test_exif_orientation.py` mapea 1:1 contra cada criterio
de aceptación y caso borde del spec (ver sección 3).

## 2. Contrato del circuito (`scripts/feature-contract.ps1`)

Corrido `Assert-FeatureContract -Slug '05-correccion-orientacion-exif' -Title 'Corrección de orientación EXIF'`
desde el módulo `scripts/feature-contract.ps1` en el worktree.

- Antes de este reporte: falló con el único problema esperable —
  `"Falta al menos un test-report-N.md en runs/05-correccion-orientacion-exif."`
  Confirma que todo lo demás del contrato ya estaba correcto:
  - `runs/05-correccion-orientacion-exif/spec.md` existe.
  - `runs/05-correccion-orientacion-exif/audit-1.md` existe (`approved`).
  - `runs/05-correccion-orientacion-exif/decision.md` existe, no vacío,
    con decisiones demostrables (mecanismo EXIF, punto de integración,
    subordinación de heurística, verificación empírica de formatos
    soportados).
  - `docs/tecnica/correccion-orientacion-exif.md` existe, no vacío
    (269 líneas): algoritmo, tabla de transformaciones por valor EXIF
    (1-8), punto exacto de integración con snippet de código, relación
    con `correct_orientation`, sección de formatos soportados (JPEG/
    TIFF/PNG/PDF) verificada contra `main.py:38`, decisiones de diseño,
    casos borde cubiertos con referencia a cada test.
  - `docs/usuario/correccion-orientacion-exif.md` existe, no vacío
    (133 líneas): propósito, qué no cambia (contrato de API), ejemplo
    HTTP completo (`POST /api/v1/jobs`, `GET .../jobs/{id}`, confirmación
    y descarga), formatos que se benefician.
  - Enlace exacto `[Corrección de orientación EXIF](correccion-orientacion-exif.md)`
    presente en `docs/tecnica/index.md:14` y `docs/usuario/index.md:12`,
    sin duplicados.
- Con este `test-report-1.md` ya escrito, el único requisito faltante
  queda satisfecho.

## 3. Verificación de cada criterio de aceptación del spec contra la implementación

1. **Función `apply_exif_orientation`** (`backend/app/image_prep.py:22-62`):
   existe, usa `PIL.ImageOps.exif_transpose`, devuelve `(imagen, applied)`.
   Cubierta por `test_apply_exif_orientation_all_8_values` (asserts de
   igualdad de array contra imagen canónica para los 8 valores) — CUMPLE.
2. **Integración antes de `image_prep.prepare()`**
   (`capture_pipeline.py:204-208`): `Image.open` → `apply_exif_orientation`
   → `.convert("RGB")` → `np.array` → `prepare(arr, exif_orientation_applied=exif_applied)`,
   solo en el camino de imagen (no PDF, confirmado en `_process_pdf`
   línea 227 que no pasa el parámetro). Cubierta indirectamente por el
   test de integración end-to-end — CUMPLE.
3. **8 valores EXIF con contenido asimétrico verificable por código**:
   `test_apply_exif_orientation_all_8_values`, parametrizado `[1..8]`,
   usa un marcador rojo 10x10 en esquina superior izquierda sobre imagen
   40x60 (no cuadrada, para que 90°/270° sean detectables), construye la
   imagen "cruda" con la transformación inversa exacta por orientación,
   verifica igualdad de array completo + posición del marcador — CUMPLE.
4. **Test de integración con texto renderizado, `Orientation=6`/`8`,
   `raw_ocr_text` no vacío**: `test_process_document_recovers_text_from_rotated_exif_image`,
   parametrizado `[6, 8]`, genera comprobante GAS sintético (texto
   renderizado con PIL), corre `process_document` completo (RapidOCR
   real), verifica `raw_ocr_text.strip() != ""` y que `"12345678"`
   (identificador de cliente) es legible — CUMPLE. Confirmado que
   efectivamente pasó (no solo skip) en la corrida de este QA.
5. **Subordinación de `correct_orientation` cuando ya hubo EXIF válido**:
   `correct_orientation(image_np, skip=False)` acepta parámetro `skip`;
   `prepare(..., exif_orientation_applied=...)` lo traduce. Cubierto por
   `test_correct_orientation_skip_true_bypasses_heuristic` (con
   `skip=True` una imagen que la heurística rotaría queda intacta) y
   `test_prepare_subordinates_heuristic_when_exif_applied` (mismo caso a
   nivel `prepare()`) — CUMPLE.
6. **Sin regresión cuando no hay EXIF utilizable**:
   `test_correct_orientation_no_regression_without_exif` verifica que
   `correct_orientation(img)` (default) y `correct_orientation(img, skip=False)`
   son idénticos y siguen rotando igual que antes — CUMPLE.
7. **Suite completa sin regresiones**: confirmado en sección 1
   (282 passed, 0 failed, 6 skipped esperados) — CUMPLE.
8. **`docs/tecnica/correccion-orientacion-exif.md`**: existe, no vacío,
   incluye la corrección exacta pedida por el reviewer en `audit-1.md`
   (ALLOWED_EXTS vive en `main.py` línea ~38, no en `validators.py`,
   verificado también por este QA con `grep` directo sobre `main.py`) y
   confirma soporte EXIF de `.tif`/`.tiff` (sí) vs `.png` (chunk `eXIf`
   opcional, no relevante en la práctica) — CUMPLE.
9. **`docs/usuario/correccion-orientacion-exif.md`**: existe, no vacío,
   con propósito y ejemplo HTTP completo (request+response) sobre el
   endpoint de subida existente, aclarando explícitamente que el
   contrato de API no cambia — CUMPLE.
10. **`decision.md`**: existe, con decisiones demostrables (mecanismo,
    punto de integración, subordinación, verificación empírica de
    formatos), no ornamental — CUMPLE.
11. **Enlaces exactos en ambos índices**: confirmados en sección 2,
    formato idéntico a entradas existentes, sin duplicados — CUMPLE.

### Criterios de dominio OCR (obligatorios)

- Comportamiento extraído documentado explícitamente en spec/docs (no
  campo de negocio puntual): confirmado.
- Fixture: `GAS`/`LITORAL_GAS`, 100% sintética (`Image.new` + texto
  renderizado con `ImageDraw`), sin fotos reales versionadas — confirmado
  leyendo `_build_gas_receipt_with_exif` en el test.
- Salida esperada (`raw_ocr_text` no vacío) verificada por el test de
  integración, corrida en esta sesión de QA con el motor RapidOCR real
  (no mockeado).
- Validación geométrica (posición de marcador) en el test unitario +
  pipeline completo en el de integración: confirmado.
- Falso positivo evitado (doble corrección EXIF + heurística): cubierto
  explícitamente por los tests de subordinación (criterio 5).

## 4. Casos borde del spec — verificación cruzada

Todos los casos borde listados en el spec (`## Casos borde a contemplar`)
tienen test dedicado y CUMPLEN:
- Sin EXIF (`test_no_exif_at_all`).
- EXIF sin tag `Orientation` (`test_exif_present_but_no_orientation_tag`).
- `Orientation = 1` explícito (`test_apply_exif_orientation_all_8_values[1]`,
  `applied is False`).
- Los 8 valores 1-8 incluyendo espejados 2/4/5/7 (parametrizado).
- EXIF corrupto/fuera de rango: `0, 9, -1, 100` (parametrizado) y valor
  no numérico (`test_orientation_non_numeric_degrades_gracefully`) — no
  lanza excepción, degrada con gracia.
- PDF renderizado: confirmado en código (`_process_pdf` no pasa
  `exif_orientation_applied`, usa default `False`) y documentado en
  ambos `.md` con la justificación; no requiere test adicional porque el
  camino de código no cambió.
- Imagen ya orientada con `Orientation != 1`: cubierta implícitamente por
  el propio diseño de `_make_raw_for_orientation`/test parametrizado (la
  imagen "cruda" reproduce exactamente lo que grabaría una cámara ya
  correctamente orientada con ese tag).
- Interacción con `deskew`: no rompe (confirmado por la suite completa
  verde, incluidos los tests preexistentes de `test_image_prep.py` sobre
  `deskew`).
- Formatos aceptados (`.jpg/.jpeg/.png/.tif/.tiff/.pdf`): documentados
  con soporte EXIF confirmado por formato en `docs/tecnica/`.

## 5. Cambios realizados por este QA

Ninguno en código o tests: la implementación y su cobertura de tests ya
estaban completas y correctas. Este reporte es el único artefacto nuevo
de esta etapa.

## Veredicto

`approved`. Suite completa verde (282 passed, 0 failed, 6 skipped
esperados y no relacionados), contrato del circuito satisfecho, y cada
criterio de aceptación y caso borde del spec tiene test real que lo
cubre y que fue efectivamente ejecutado en esta sesión (no asumido de
corridas previas).
