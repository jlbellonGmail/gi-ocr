```yaml
status: approved
attempt: 1
feedback:
  - No bloqueante: los 3 tests HTTP nuevos que usan `TestClient(app)` sin
    context manager (`test_api_job_rejected_by_quality_gate_returns_needs_new_photo_status`,
    `test_api_confirm_on_rejected_job_returns_404`,
    `test_api_retry_on_rejected_job_returns_200_and_requeues`) generan
    `PytestUnraisableExceptionWarning` ("Event loop is closed") al cerrar
    el worker async de `JobQueue` en el teardown. No falla ningún test ni
    afecta el resultado (48/48 pasan igual); es cosmético. Si se quiere
    prolijidad, usar `with TestClient(app) as client:` para disparar los
    eventos de lifespan/shutdown de forma ordenada, igual que otros tests
    HTTP async del repo. Queda a criterio de una iteración futura, no
    bloquea este approve.
```

## Resumen

QA corrida sobre el worktree `D:\proyectos\worktrees\06-calidad-captura-mobile`,
rama `feature/06-calidad-captura-mobile`, commit `6fbdc6b`, usando
`D:\proyectos\gi-ocr\.venv\Scripts\python.exe` (mismo patrón que usó el
builder, sin `.venv` propio en el worktree).

## 1. Suite completa de tests (`pytest`)

### `backend/tests/` (código de producto)

Corrida tal cual (sin `--basetemp` propio, réplica exacta del comando del
builder):

```
281 passed, 7 skipped, 40 warnings, 57 errors in 69.68s
```

Coincide exactamente con lo reportado por el builder en `decision.md`
("281 passed, 7 skipped [...] los mismos ~57 errores de entorno
preexistentes"). Verifiqué independientemente que esos 57 `ERROR` **no**
son fallos de test: son `PermissionError: [WinError 5] Acceso denegado:
'C:\Users\jlbel\AppData\Local\Temp\pytest-of-jlbellon'` al intentar que
pytest liste/gestione su `basetemp` compartido en `%TEMP%`, disparado
antes de que el test siquiera corra (falla en la fixture `tmp_path` de
pytest, en `_pytest/pathlib.py::find_prefixed`, `os.scandir(root)`).
Ningún traceback de esos 57 errores toca `quality_gate.py`,
`image_prep.py`, `capture_pipeline.py` ni `job_queue.py`.

**Confirmación de que es preexistente y no de esta feature**, corriendo el
mismo comando en `D:\proyectos\gi-ocr` (rama `develop`, sin esta feature):

```
237 passed, 2 skipped, 44 warnings, 58 errors in 68.15s
```

Comparé el listado exacto de tests con `ERROR` en ambas ramas
(`sort`+`diff`): son el mismo conjunto de archivos (`test_retention.py`,
`test_storage_bridge_writer.py`, `test_services_config_schema.py`,
`test_inbound_watcher.py`, `test_pdf_util.py`,
`test_document_result_exporter.py`, `test_document_services.py`,
`test_evaluate_ocr_service_data_output.py`, `test_services_admin_api.py`),
con una única diferencia de 1 test
(`test_local_samples_real.py::test_unknown_not_gas`), que investigué
aparte: no es un problema de código, es que la carpeta de muestras
privadas locales (gitignoradas) está presente en el checkout principal
(`gi-ocr`, con 3 passed + 1 error de permisos) pero no en el worktree de
la feature (4 skipped, sin muestras locales) — comportamiento correcto en
ambos casos, solo cambia si el fixture existe en disco.

**Confirmación adicional, ejecutando la suite completa con un
`--basetemp` propio** (evitando el problema de permisos de `%TEMP%` por
completo, para ver el resultado real de esos 57 tests sin el ruido del
entorno):

```
338 passed, 7 skipped, 40 warnings in 45.29s
```

`281 + 57 = 338`. Los 57 tests que fallaban por `PermissionError` pasan
todos limpiamente cuando pytest puede crear su directorio temporal. Esto
confirma sin ambigüedad que es un problema de entorno Windows local (una
ACL o un proceso reteniendo el handle de
`C:\Users\jlbel\AppData\Local\Temp\pytest-of-jlbellon`), no relacionado
con el código de esta feature ni con ninguna otra. No bloquea el approve.

### `tests/` (scripts del circuito agéntico)

```
51 passed, 1 skipped in 411.86s
```

(1 skip: `tests/e2e/test_e2e_playwright.py`, `playwright` no instalado —
preexistente, no relacionado con esta feature). Sin fallos.

### `backend/tests/test_quality_gate.py` en aislamiento

```
48 passed, 10 warnings in 28.21s
```

Las 10 advertencias son `PytestUnraisableExceptionWarning` ("Event loop is
closed") al cerrar el worker async de `JobQueue` en el teardown de los 3
tests HTTP nuevos que usan `TestClient(app)` sin `with`. No son fallos:
los 48 tests pasan. Ver nota no bloqueante en el veredicto.

## 2. Verificación específica del riesgo de calibración (brillo sobreexpuesto)

Verifiqué directamente que `backend/tests/fixtures/gas_sample.jpg` mide un
brillo medio global de `254.1054...` (calculado con
`cv2.cvtColor(..., COLOR_RGB2GRAY).mean()`), exactamente como afirma
`decision.md`. Con los umbrales por defecto
(`BRIGHT_WARN_ABOVE=250.0`, `BRIGHT_REJECT_ABOVE=254.5`):

- `quality_gate.evaluate()` sobre `gas_sample.jpg` da `verdict: "warn"`
  (no `"ok"`, y no `"reject"`) — la señal `poor_lighting` sí se activa en
  `warn` sobre este documento de referencia (254.1 > 250), pero al ser
  `warn` el pipeline sigue normal (no bloquea OCR). El umbral de `254.5`
  solo evita el `reject`, no el `warn`, sobre este fixture — comportamiento
  correcto y coherente con el spec (criterio 16: `warn` no bloquea).
- Confirmé que `backend/tests/test_exif_orientation.py` (20 tests) y
  `backend/tests/test_process_document_cli.py` (7 tests), que ejercitan
  `process_document` de punta a punta sobre fixtures con ese mismo perfil
  de brillo, siguen pasando 27/27 sin ninguna regresión, con o sin el
  bloque `quality_gate` en `processing_metadata`.
- **El punto crítico del criterio de esta tarea de QA — que exista al
  menos un test que demuestre que la señal SÍ dispara `reject`/`warn` con
  una imagen realmente sobreexpuesta — se cumple**:
  `test_illumination_overexposed_reject` (línea 350) construye una imagen
  con `+210` de offset uniforme (no multiplicativo, justificado en el
  docstring del propio test: la suma sí desplaza el texto hacia blanco,
  perdiendo contraste como una sobreexposición real) y verifica
  explícitamente `verdict == "reject"` para la señal `poor_lighting`. Es
  decir, el umbral no deja la señal "inutilizable": sí dispara para casos
  de sobreexposición real, y el ajuste fino a `254.5` (en vez de, por
  ejemplo, `240`) fue necesario específicamente para no generar un falso
  positivo de `reject` contra el propio comprobante de referencia del
  repo, tal como documenta `docs/tecnica/calidad-captura-mobile.md`
  ("Justificación del umbral claro"), que además reconoce explícitamente
  la limitación resultante (baja sensibilidad para sobreexposición leve
  sobre documentos de fondo muy claro) como riesgo de calibración conocido
  — no una limitación oculta. Esto es coherente con el resto del riesgo de
  calibración ya declarado y no bloqueante, según `decision.md` y
  `audit-1.md`.
- No hay un test explícito de `warn` específico para el lado
  "sobreexpuesto" (solo `reject` para ese lado, y `warn`/`reject` para el
  lado oscuro), pero no es un vacío real: `gas_sample.jpg` en sí mismo ya
  ejercita el camino `warn` por brillo alto vía los tests de integración
  end-to-end (`test_exif_orientation.py`,
  `test_process_document_cli.py`), aunque no lo aserten explícitamente
  como tal. No bloqueante.

**Conclusión sobre este punto**: la calibración cerca del techo (254.5)
está justificada, documentada, y verificada por test para el caso más
importante (que dispare `reject` ante sobreexposición real). No deja la
señal inutilizable.

## 3. Contrato común (`scripts/feature-contract.ps1`)

Ejecuté `Assert-FeatureContract -Slug '06-calidad-captura-mobile' -Title
'Calidad de Captura Mobile'` desde el worktree. Único hallazgo: faltaba
`test-report-N.md` (el archivo que esta misma verificación produce) — todo
lo demás pasa:

- `runs/06-calidad-captura-mobile/spec.md`: presente.
- `runs/06-calidad-captura-mobile/decision.md`: presente, no ornamental
  (decisiones demostrables con referencias a código/tests concretos).
- `runs/06-calidad-captura-mobile/audit-1.md`: presente (`approved`).
- `docs/tecnica/calidad-captura-mobile.md`: presente, no vacío (533
  líneas), cubre las 8 señales, umbrales, justificación, casos borde y
  riesgo de calibración.
- `docs/usuario/calidad-captura-mobile.md`: presente, no vacío (291
  líneas), con ejemplos HTTP completos (request+response) para los tres
  veredictos `ok`/`warn`/`reject`, incluyendo `confirm` (404) y `retry`
  (200) sobre un job rechazado.
- `docs/tecnica/index.md`: enlace exacto `[Calidad de Captura
  Mobile](calidad-captura-mobile.md)` presente.
- `docs/usuario/index.md`: enlace exacto `[Calidad de Captura
  Mobile](calidad-captura-mobile.md)` presente.

## 4. Verificación de código contra criterios de aceptación del spec

Leí `backend/app/quality_gate.py`, el punto de integración en
`backend/app/capture_pipeline.py::process_document`/
`_quality_rejected_result`, y el manejo de estado en
`backend/app/job_queue.py`. Confirmo, cruzando contra `spec.md`:

- Las 8 señales (blur, baja resolución, glare, sombras, corte, mala
  perspectiva, mala iluminación, encuadre insuficiente) están
  implementadas con las métricas descriptas en el spec y cubiertas por
  test individual (ok/warn/reject y falso positivo evitado por señal).
- El veredicto agregado toma el peor sub-veredicto y lista todas las
  razones (`test_verdict_worst_subverdict_wins_with_all_reasons_listed`,
  `test_verdict_mixed_severity_reject_wins_but_both_listed`).
- La deduplicación de causa raíz corte/perspectiva está implementada sin
  caso especial (contorno abierto → `find_document_contour` devuelve
  `None` → `_perspective_signal` no evalúa) y verificada por test
  (`test_cut_document_deduplicates_perspective_reason`).
- `reject` no invoca OCR, verificado con spy sobre
  `ocr_engine.detect_page` (`test_process_document_reject_does_not_invoke_ocr`).
- `warn` sigue el pipeline normal
  (`test_process_document_warn_still_runs_ocr_and_flags_metadata`).
- Estado `needs_new_photo`: `confirm` → 404, `retry` → 200 y determinístico,
  verificados tanto a nivel `JobQueue` puro como HTTP real con `TestClient`.
- Casos borde: imágenes degeneradas (negro, blanco, 1x1) no lanzan
  excepción y degradan a `reject`; archivo corrupto sigue el camino
  `failed` existente, no el de rechazo por calidad
  (`test_process_document_corrupt_file_raises_not_quality_reject`); PDF
  no pasa por el chequeo (`test_pdf_path_bypasses_quality_gate`, con spy).
- `image_prep.correct_perspective` fue refactorizado para reutilizar
  `find_document_contour` sin cambiar comportamiento — confirmado por
  `backend/tests/test_image_prep.py` (5/5, sin cambios en el archivo de
  test, sigue pasando igual que antes de la feature).

No se tocó `backend/config/services.ini` ni se agregó dependencia nueva
(`opencv-python-headless` ya estaba declarada). No se versionaron imágenes
reales (todas las fixtures de `test_quality_gate.py` son sintéticas,
generadas en memoria con PIL/NumPy/OpenCV).

## Veredicto final

`approved`. La implementación cumple los 19 criterios de aceptación
específicos, los 5 criterios generales (incluyendo documentación técnica y
de usuario), y los casos borde declarados en el spec. La suite completa de
tests pasa sin fallos reales (los 57 "errores" en `backend/tests/` son un
problema de entorno Windows preexistente en `%TEMP%`, verificado
independientemente como no relacionado con el código de esta feature, y
confirmado también presente en `develop`). El punto de calibración
señalado como riesgoso (`BRIGHTNESS_BRIGHT_REJECT_ABOVE = 254.5`) está
documentado, justificado, y verificado por test para el caso central
(dispara `reject` ante sobreexposición real). El contrato común de
artefactos pasa en su totalidad salvo este mismo reporte, que ya queda
resuelto con este archivo.
