```yaml
status: approved
attempt: 1
feedback:
  - "Inconsistencia menor no bloqueante: decision.md dice '25 tests' nuevos, pero backend/tests/test_preparation_trace.py contiene 22 funciones test_ (una parametrizada x2 -> 23 tests recolectados, confirmado con `pytest --collect-only`). No afecta ningun criterio de aceptacion ni la cobertura real; se deja registrado para que builder lo corrija si vuelve a tocar este archivo."
```

## Entorno

- Worktree: `D:\proyectos\worktrees\07-preprocesamiento-documental-no-destructivo`
- Rama confirmada: `feature/07-preprocesamiento-documental-no-destructivo`
- `git log --oneline -5`:
  ```
  4f1e1ec docs(07-preprocesamiento-documental-no-destructivo): documentar traza de preparacion, paso de contraste y decisiones
  67f437c test(07-preprocesamiento-documental-no-destructivo): cubrir no-destructividad, traza y salvaguarda de contraste
  f499aa1 feat(07-preprocesamiento-documental-no-destructivo): trazar transformaciones de image_prep y agregar normalizacion de contraste
  08ba659 docs(07-preprocesamiento-documental-no-destructivo): agregar spec aprobado y auditorias
  1ed743c docs: cerrar 06-calidad-captura-mobile en ROADMAP.md
  ```
- `.venv` ya existia en el worktree con dependencias instaladas (`import cv2, fastapi, rapidocr_onnxruntime` sin error). No hizo falta recrearlo.

## Suite completa (`pytest -q`)

Comando corrido (con `--basetemp` propio por el problema de permisos conocido en `%TEMP%/pytest-of-<user>` en Windows, ya documentado en `runs/06-calidad-captura-mobile/decision.md`):

```
python -m pytest -q --basetemp=<worktree>/.pytest-basetemp backend/tests tests
```

Resultado real:

```
412 passed, 8 skipped, 52 warnings in 470.91s (0:07:50)
```

Skips verificados, mismos motivos ya documentados en el proyecto, ninguno nuevo:
- `tests/e2e/test_e2e_playwright.py` (playwright no instalado)
- `backend/tests/test_api_jobs.py` (muestra privada local no disponible)
- `backend/tests/test_local_samples_real.py` x4 (muestras privadas locales no disponibles, gitignored)
- `backend/tests/test_upload_security.py` x2 (permisos POSIX no aplican en Windows)

Los warnings son `PytestUnraisableExceptionWarning`/`RuntimeError: Event loop is closed` en el cierre de `JobQueue._worker` durante teardown de tests de `test_services_admin_api.py` — preexistentes al ciclo de vida asyncio en Windows, no relacionados con esta feature (no aparecen en ningún assert fallido).

Conteo exacto confirmado por el builder (412 passed / 8 skipped, baseline previo 389 passed/8 skipped = exactamente +23 tests nuevos, sin regresiones). Confirmado con `pytest --collect-only -q backend/tests/test_preparation_trace.py` → `23 tests collected`.

`git diff 08ba659..HEAD --stat` confirma que **no se tocó** ningún archivo de test existente (`test_image_prep.py`, `test_exif_orientation.py`, `test_quality_gate.py`, etc.) — solo se agregó `backend/tests/test_preparation_trace.py`. Esto cumple el criterio 18 sin necesidad de la excepción que el spec habilitaba ("salvo los cambios estrictamente necesarios..., documentado en el test-report"): no hizo falta ningún cambio.

## Verificación criterio por criterio

**1-5 (generales/documentación/índices):**
- `docs/tecnica/preprocesamiento-documental-no-destructivo.md` (365 líneas): no vacío, documenta el algoritmo de cada paso (incluido CLAHE sobre canal L de LAB para contraste), el formato exacto de la traza (tabla paso→parámetros), el punto de integración (después de `normalize_scale`, con justificación), y decisiones de diseño (salvaguarda "intentar y verificar", por qué no un umbral fijo de std, calibración empírica con tabla de nitidez antes/después).
- `docs/usuario/preprocesamiento-documental-no-destructivo.md` (257 líneas): no vacío, propósito claro (no-destructividad + traza), y **tres** ejemplos HTTP completos (`GET /api/v1/jobs/{job_id}` con traza completa camino imagen, camino PDF con imagen renderizada, camino PDF con texto nativo sin traza) — supera el mínimo de un ejemplo exigido por el criterio 2.
- `runs/07-preprocesamiento-documental-no-destructivo/decision.md`: presente, con decisiones demostrables (nombres de clave/función, orden de integración, por qué se descartó el umbral fijo, hallazgo sobre `gas_sample.jpg`/UNKNOWN verificado explícitamente).
- `docs/tecnica/index.md` línea 21: `- [Preprocesamiento Documental No Destructivo](preprocesamiento-documental-no-destructivo.md)` — enlace exacto presente.
- `docs/usuario/index.md` línea 19: mismo enlace exacto presente.

**6-8 (no-destructividad):** verificado en código (`image_prep.py` solo recibe/devuelve `np.ndarray`, ningún `cv2.imwrite`/`Image.save` sobre la ruta de entrada en todo el módulo) y en tests reales, corridos en la suite completa:
- `test_process_document_does_not_modify_original_file` (parametrizado `.jpg`/`.png`): hash SHA-256 antes/después de `process_document` directo — passed.
- `test_process_document_does_not_modify_original_pdf`: mismo hash sobre PDF sintético — passed.
- `test_retry_endpoint_does_not_modify_original_file`: hash antes/después de `POST /api/v1/jobs/{job_id}/retry` vía `TestClient` real (usa un job `needs_new_photo`, ya que `retry()` bloquea `ready`/`confirmed` por diseño preexistente) — passed. Cumple criterio 7 con `TestClient`, tal como exige el spec.

**9-10 (traza ordenada, formato):** `test_process_document_image_path_trace_order_and_shape` verifica el orden exacto `["apply_exif_orientation", "correct_orientation", "deskew", "correct_perspective", "normalize_scale", "normalize_contrast"]` sobre una fixture con densidad de texto suficiente para pasar `quality_gate` en `ok`/`warn`, y que cada entrada tiene `{"step": str, "applied": bool}`. Parámetros adicionales verificados en tests dedicados: ángulo de deskew (`test_trace_deskew_reports_angle_when_applied`), factor de escala/dimensiones (`test_trace_normalize_scale_reports_factor_and_sizes_when_downscaled`, `..._no_upscale_reports_not_applied`), método de contraste (`CONTRAST_METHOD = "clahe_lab_l_channel"`, expuesto en cada entrada de contraste). Revisé el código de `_append_step`/`prepare()`: la traza se arma en el mismo orden de ejecución real, no hay reordenamiento posterior.

**11 (reject sin traza fantasma):** `test_quality_reject_result_has_no_preparation_trace` confirma que `"preparation_trace" not in result["processing_metadata"]` cuando `quality_gate.verdict == "reject"`. Confirmado en código: `process_document` retorna `_quality_rejected_result(...)` antes de construir la lista `trace`.

**12 (camino PDF honesto):** `test_pdf_with_rendered_image_trace_excludes_exif_and_quality_gate` verifica que la traza de un PDF con imagen renderizada tiene exactamente `["correct_orientation", "deskew", "correct_perspective", "normalize_scale", "normalize_contrast"]` (5 entradas, sin `apply_exif_orientation` ni `quality_gate` en `processing_metadata`). Revisé `_process_pdf` en el código: llama a `image_prep.prepare(page_to_process["image"], trace=trace)` con los mismos defaults que el camino imagen — no hay ninguna rama `is_pdf` dentro de `prepare()` (confirmado leyendo `image_prep.py` completo: la función no recibe ningún parámetro que distinga el llamador).

**13-14 (función de contraste, integración):** `normalize_contrast(image_np: np.ndarray) -> np.ndarray` es pública, pura, y se integra dentro de `prepare()` después de `normalize_scale` (confirmado leyendo el cuerpo de `prepare()` línea por línea). `test_normalize_contrast_is_deterministic` verifica `normalize_contrast(x) == normalize_contrast(x)` bit a bit. Ningún test de `test_image_prep.py`/`test_exif_orientation.py` fue modificado y ambos siguen en verde dentro de la corrida completa (412 passed).

**15 (salvaguarda anti sobre-procesamiento):** revisé `_normalize_contrast_impl`: usa un patrón "intentar y verificar" (calcula CLAHE, mide varianza del Laplaciano antes/después, descarta si cae >10%) en vez de un umbral fijo — decisión documentada y justificada con datos reales (`gas_sample.jpg`: -1.8%, dentro de margen; fixture oscurecida: +32%; fixture sintética de bajo contraste: +175%). Tests reales, todos passed:
- `test_normalize_contrast_does_not_degrade_well_lit_synthetic_fixture` (no degrada sobre imagen ya bien iluminada).
- `test_normalize_contrast_safety_guard_discards_degrading_enhancement` (fuerza degradación vía `unittest.mock.patch` sobre `_apply_clahe`, confirma que se descarta con `applied=False` y motivo explícito).
- `test_normalize_contrast_improves_low_contrast_synthetic_fixture` y `test_normalize_contrast_improves_darkened_gas_fixture` (mejora verificable sobre fixtures de bajo contraste/oscurecidas).

**16 (regla de dominio OCR):** declarado en `docs/tecnica/` con los 5 puntos exigidos (campos afectados, tipo de documento GAS, fixture `gas_sample.jpg`, salida esperada, validadores sin cambios, falsos positivos evitados). Verifiqué el hallazgo del builder sobre `gas_sample.jpg`/`provider_detected: UNKNOWN` de forma independiente (no confié en su `git stash`): creé un `git worktree` temporal en el commit base `08ba659` (antes de esta feature), corrí `capture_pipeline.process_document('backend/tests/fixtures/gas_sample.jpg')` ahí, y obtuve el mismo resultado (`provider_detected: UNKNOWN`, mismo texto OCR sin la palabra "litoral") que con el código de esta feature. **Es un comportamiento preexistente, no una regresión introducida por esta feature** — confirmado independientemente, worktree temporal ya eliminado (`git worktree remove --force`). El test `test_gas_fixture_contrast_step_preserves_fields_and_digits` compara correctamente dígitos extraídos por regex (`\d+`) del `raw_ocr_text` con/sin el paso de contraste, exactamente iguales — passed.

**17 (idempotencia):** `test_reprocessing_same_original_is_idempotent` compara `preparation_trace`, `validated_fields`, `rejected_fields`, `missing_fields` entre dos llamadas consecutivas a `process_document` sobre el mismo archivo — passed, sin aleatoriedad.

**18 (suite completa en verde, sin modificar expectativas de 05/06):** confirmado arriba — `git diff` muestra que ningún archivo de test existente fue tocado, y la suite completa da 412 passed/8 skipped sin fallos.

## Revisión de honestidad del código (no solo tests)

- Ningún paso de `image_prep.py` escribe a disco: revisé el archivo completo, no hay `cv2.imwrite`/`.save(` sobre ninguna ruta de entrada.
- `prepare()` no tiene ninguna rama `is_pdf` ni parámetro equivalente: es literalmente la misma función invocada desde `process_document` (camino imagen) y `_process_pdf` (camino PDF) con distintos argumentos por defecto, no con lógica condicional interna nueva.
- La distinción "perspectiva no solicitada" (`requested: False`) vs. "intentada sin cuadrilátero" (`requested: True, applied: False`) está implementada correctamente en `prepare()` (líneas ~532-542) y verificada por dos tests distintos.
- `_process_pdf_native` nunca llama a `image_prep.prepare` (confirmado leyendo `_process_pdf`: retorna antes si `page_to_process is None`), por lo que nunca genera `preparation_trace` — coincide con `test_pdf_native_text_has_no_preparation_trace`.

## Contrato común (`scripts/feature-contract.ps1`)

Corrí `Assert-FeatureContract -Slug '07-preprocesamiento-documental-no-destructivo' -Title 'Preprocesamiento Documental No Destructivo'` **antes** de escribir este `test-report-1.md`: falló únicamente por la ausencia esperada de `test-report-N.md` en esa etapa ("Falta al menos un test-report-N.md en runs/07-preprocesamiento-documental-no-destructivo"), confirmando que todo el resto del contrato (docs, decision.md, índices, auditoría) ya estaba satisfecho antes de este artefacto. Con este archivo creado, el contrato queda completo para esta etapa.

## ROADMAP.md

`grep -n "07-preprocesamiento" ROADMAP.md` → sigue en `[ ]` (pendiente), tal como corresponde: el builder no lo tocó y no se corrió `ready-for-pr.ps1` todavía. Ese paso queda para después de esta aprobación de QA, según el circuito.

## Conclusión

Los 18 criterios de aceptación del spec están verificados contra código real y tests reales corridos (no solo inspección de que "existe un test"). La suite completa pasa (412 passed, 8 skipped, mismos motivos de skip ya documentados). El hallazgo sobre `gas_sample.jpg`/`UNKNOWN` fue verificado independientemente como preexistente, no como regresión introducida por esta feature. La documentación técnica y de usuario cumple los criterios generales, con enlaces de índice exactos. El único hallazgo es una inconsistencia cosmética en el conteo de tests dentro de `decision.md` (25 vs. 23 reales), que no afecta ningún criterio de aceptación ni la cobertura real y no amerita rechazo.

**Veredicto: `approved`.**
