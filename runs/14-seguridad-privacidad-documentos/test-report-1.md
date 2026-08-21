```yaml
status: rejected
attempt: 1
feedback:
  - qué falló: "docs/tecnica/seguridad-privacidad-documentos.md, sección
    5, subsección \"TIFF: por qué se edita el IFD a nivel de bytes...\"
    afirma: \"Esto garantiza preservación byte a byte de los datos de
    imagen (verificado en test comparando pixel arrays antes/después vía
    numpy)\". Qué esperaba: que esa afirmación de verificación tenga un
    test real correspondiente (comparación de pixel arrays vía numpy
    antes/después de la anonimización TIFF), tal como la propia
    documentación técnica declara que existe. Qué obtuve: revisé
    `backend/tests/test_exif_privacy.py` completo (los 8 tests del
    archivo) y no existe ningún test que compare pixel arrays vía numpy
    para el caso TIFF (ni para JPEG). El único test TIFF de
    "no degradación" es `test_exif_anonymization_tiff_preserves_size_and_mode`,
    que compara únicamente `.size` y `.mode` — exactamente lo que el
    propio `spec.md` (criterio 9, párrafo TIFF) pide como verificación
    suficiente para ese formato ("la verificación de ausencia de
    degradación para este formato se hace comparando dimensiones (size) y
    modo de color (mode)"). El spec NO exige una comparación de pixel
    arrays por numpy para TIFF; la implementación cumple el spec
    correctamente. El problema es exclusivamente que el texto de
    `docs/tecnica/` sobreclama un método de verificación (test con numpy)
    que no fue escrito, lo cual es una afirmación fáctica incorrecta en
    documentación técnica que otros mantenedores usarán como referencia
    de qué está realmente probado. Corrección esperada (a elección de
    builder-agent, cualquiera de las dos es aceptable): (a) corregir esa
    oración para que describa con precisión el método de verificación
    real usado (size/mode, como efectivamente hace el test existente), o
    (b) si se prefiere mantener la afirmación, agregar el test real de
    comparación de pixel arrays vía numpy que la respalde. No se requiere
    ningún otro cambio de código: el resto de la implementación, todos
    los demás criterios de aceptación y el resto de la documentación
    fueron verificados y están correctos (ver evidencia abajo).
```

# Reporte QA — intento 1 — `14-seguridad-privacidad-documentos`

## Resumen del veredicto

**Rejected**, por un único hallazgo: una afirmación fáctica incorrecta en
`docs/tecnica/seguridad-privacidad-documentos.md` (sección 5, TIFF) que
declara la existencia de un test (comparación de pixel arrays vía numpy)
que no existe en `backend/tests/test_exif_privacy.py`. No es un problema
de código, de cobertura de tests contra el spec, ni de comportamiento de
seguridad: es una inexactitud de documentación técnica que debe
corregirse porque es exactamente el tipo de detalle que un mantenedor
futuro usaría para confiar (equivocadamente) en una garantía de
verificación que no existe hoy. Todo lo demás — código, tests reales,
contrato del circuito, ambos documentos, índices, `decision.md` — está en
orden y se detalla como evidencia abajo. La corrección esperada es
mínima (una oración de doc, o agregar el test que esa oración describe) y
no requiere reabrir spec ni auditoría.

## 1. Suite de tests completa (`pytest`)

Comando ejecutado (worktree `D:\proyectos\worktrees\14-seguridad-privacidad-documentos`,
intérprete `D:\proyectos\gi-ocr\.venv\Scripts\python.exe`, `--basetemp`
propio para evitar el `PermissionError` conocido de entorno por
circuitos en paralelo):

```
python -m pytest -v backend/tests tests --basetemp="C:\Users\jlbel\AppData\Local\Temp\pytest-qa-feature14"
```

Resultado: **290 passed, 8 skipped, 0 errors** (497.57s). Los 8 skips son
todos justificados y esperados en este entorno:
- 1 `playwright` no instalado (E2E, no relacionado con esta feature).
- 4 "muestras privadas locales no disponibles" (gitignored, no relacionado).
- 2 tests de permisos POSIX (`test_uploaded_file_has_owner_only_permissions`,
  `test_uploads_dir_has_owner_only_permissions`) — gateados con
  `@pytest.mark.skipif(os.name != "posix", ...)`, tal como exige el spec
  (criterio 6 y caso borde "Entorno Windows de desarrollo").

Tests nuevos de esta feature, todos en verde:
- `backend/tests/test_upload_security.py` — 11 tests (criterios 1, 3, 4,
  5, 6, 8).
- `backend/tests/test_exif_privacy.py` — 8 tests (criterio 9, JPEG + TIFF).
- `backend/tests/test_retention.py` — 11 tests (criterio 7).

Ningún test nuevo usa mocks/stubs sobre la lógica de negocio: todos los
tests de `test_upload_security.py` y `test_exif_privacy.py` ejercitan el
flujo real completo `POST /api/v1/jobs` → `_save_upload` → validación →
anonimización → escritura en `output/uploads/`, vía `TestClient(app)`
real y contenido binario real (JPEG/TIFF/PNG/PDF generados con Pillow o
bytes crudos), verificando el archivo resultante en disco con
`PIL.Image.open`. `test_retention.py` ejercita `purge_directory`/
`purge_all` contra archivos reales en `tmp_path` con `mtime` manipulado
vía `os.utime`, no contra dobles de prueba.

## 2. Contrato común (`Assert-FeatureContract`)

```
Import-Module ./scripts/feature-contract.ps1 -Force
Assert-FeatureContract -Slug '14-seguridad-privacidad-documentos' -Title 'Seguridad y Privacidad de Documentos'
```

Antes de este reporte: fallaba con `Falta al menos un test-report-N.md en
runs/14-seguridad-privacidad-documentos` — esperado, es el artefacto que
este mismo reporte provee. El resto del contrato (spec, decision.md,
auditoría, docs/tecnica, docs/usuario, enlaces en ambos índices) ya
estaba satisfecho antes de este test-report, verificado manualmente:

- `docs/tecnica/seguridad-privacidad-documentos.md`: 379 líneas, no vacío.
- `docs/usuario/seguridad-privacidad-documentos.md`: 159 líneas, no vacío.
- `docs/tecnica/index.md:14` → `- [Seguridad y Privacidad de Documentos](seguridad-privacidad-documentos.md)`.
- `docs/usuario/index.md:12` → `- [Seguridad y Privacidad de Documentos](seguridad-privacidad-documentos.md)`
  (mismo título exacto en ambos índices).
- `runs/14-seguridad-privacidad-documentos/decision.md` existe, no vacío,
  con decisiones demostrables trazadas a código/tests concretos.
- `ROADMAP.md:166` sigue en `[ ]` (correcto: todavía no corresponde
  `READY_FOR_PR`, eso es un paso posterior del orquestador).

Una vez agregado este `test-report-1.md`, `Assert-FeatureContract`
solo debería fallar (si se re-corriera) por el estado de `ROADMAP.md`
cuando se pase `-RequireReadyRoadmap`, que no aplica todavía en este
paso del circuito.

## 3. Verificación de los 14 criterios de aceptación contra el código real

1. **Rechazo por firma real (magic bytes)** — `upload_validation.py`,
   tabla `SIGNATURES` (JPEG/PNG/TIFF/PDF) + `detect_signature`. Integrado
   en `main._save_upload` antes de escribir a disco. Test real:
   `test_upload_rejects_signature_mismatch_and_leaves_no_file` (sube un
   `.jpg` con contenido de texto plano, confirma 400/415,
   `signature_mismatch` en el cuerpo, y que `output/uploads/` no cambió).
   **Cumple.**
2. **Regresión de rechazo por extensión** — `_validate_upload` en
   `main.py` conserva `ALLOWED_EXTS` sin cambios de comportamiento;
   `test_upload_rejects_bad_ext` (test preexistente) sigue en verde.
   **Cumple.**
3. **Tamaño máximo configurable** — `upload_validation.max_upload_bytes()`
   lee `GI_OCR_MAX_UPLOAD_BYTES`, default 30MB si ausente/vacío/no entero/
   `<=0`. Tests: `test_max_upload_bytes_configurable_via_env` (baja el
   límite a 2048 bytes vía `monkeypatch.setenv`, confirma 413 sobre un PNG
   ruidoso >2048 bytes) y `test_max_upload_bytes_defaults_to_30mb_when_unset`.
   **Cumple.**
4. **Content-Type vs. firma real** —
   `upload_validation.validate_upload_content`: Content-Type ausente/
   vacío/`application/octet-stream` (`GENERIC_CONTENT_TYPES`) nunca es
   mismatch; cualquier otro valor inconsistente con la familia detectada
   se rechaza (`content_type_mismatch`, 415). Tests:
   `test_content_type_mismatch_rejected` (jpg declarado con bytes de PDF
   → rechazo) y `test_content_type_absent_accepted_for_tiff` (TIFF real
   con Content-Type `""` → 200, sin falso positivo). **Cumple**, incluido
   el caso borde de navegadores que no infieren MIME de `.tif`/`.tiff`.
5. **Nombre de archivo aleatorio** —
   `upload_validation.random_upload_name` usa `secrets.token_hex(16)`
   (128 bits, criptográficamente seguro), no timestamp ni nombre del
   cliente. `main._save_upload` lo usa como único componente de la ruta
   de destino; `name`/`original_name` sanitizado se conserva solo como
   metadato del job. Test:
   `test_uploaded_filename_is_random_not_derived_from_original` (dos
   subidas del mismo nombre original → dos nombres de archivo distintos,
   ninguno contiene el nombre sanitizado ni fragmentos identificables del
   original como substring). **Cumple.**
6. **Permisos de filesystem restrictivos** — `fs_permissions.py`
   (`secure_file`/`secure_dir`, `0o600`/`0o700`, no-op en Windows,
   `os.chmod` en `try/except OSError` best-effort). Integrado en
   `main._save_upload`, `job_store.py` (init de directorios +
   `save_original`/`save_confirmed`), `storage_bridge_writer.py`
   (`inbound`/`ready`/`failed` + archivo temporal/final/failed) e
   `inbound_watcher.py` (directorio + `.gitkeep`) — los 5 puntos de
   escritura que el spec exige. Tests gateados a POSIX
   (`skipif os.name != "posix"`, ambos `SKIPPED` en este entorno Windows,
   como corresponde) más `test_fs_permissions_is_noop_on_non_posix`, que
   sí corre en Windows y confirma que ningún `os.chmod` se invoca cuando
   `IS_POSIX` es falso. **Cumple.**
7. **Retención/purga configurable** — `retention.py`: 4 variables de
   entorno con los defaults exactos del spec (`GI_OCR_UPLOAD_RETENTION_DAYS`=7,
   `GI_OCR_JOB_RETENTION_DAYS`=90, `GI_OCR_FAILED_RETENTION_DAYS`=30,
   `inbound/` de raíz = mismo valor que uploads), basada en `mtime` (no en
   formato de nombre, cubre el caso borde de archivos con el esquema
   `{timestamp}_{nombre}` anterior), nunca borra `.gitkeep`/`README.md`/
   `.gitignore`, nunca purga `storage_bridge/ready/` (ni siquiera aparece
   como target en `purge_all`), protege archivos de jobs
   `queued`/`processing` vía `JobStore` opcional, y valores `<=0` deshabilitan
   en vez de purgar todo. 11 tests en `test_retention.py` cubren cada una
   de estas ramas contra archivos reales en `tmp_path` con `mtime`
   manipulado, incluyendo el caso borde de `ready/` intocado y el de job
   activo protegido. **Cumple.**
8. **Helper de redacción** — `redaction.py::redact_message`/
   `redact_exception`, regex de rutas absolutas POSIX/Windows/UNC,
   reemplaza por el nombre base. Integrado en
   `job_queue.py::_process` (`job["error"]` y el payload SSE). Test:
   `test_job_error_redacts_absolute_path_marker` (fuerza un
   `FileNotFoundError` real con un marcador único embebido en una ruta
   absoluta, confirma que ni el marcador ni la ruta completa aparecen en
   `GET /api/v1/jobs/{job_id}`). **Cumple**, incluyendo la nota del spec
   sobre que jobs `failed` no se persisten a disco (no cambiado por esta
   feature, documentado).
9. **Anonimización EXIF (JPEG + TIFF)** — ver sección dedicada abajo.
   **Cumple funcionalmente; hallazgo de documentación, ver veredicto.**
10. **Cobertura de tests dedicada + suite completa en verde** —
    `test_upload_security.py` + `test_exif_privacy.py` cubren 1, 3, 4, 5,
    6, 8, 9 (JPEG y TIFF); `test_retention.py` cubre 7. Suite completa:
    290 passed, 8 skipped, 0 errors. **Cumple.**
11. **`docs/tecnica/seguridad-privacidad-documentos.md`** — existe, 379
    líneas, cubre tabla de firmas, criterio Content-Type/magic-bytes
    (incluyendo el caso genérico/ausente), esquema de nombre aleatorio,
    permisos por plataforma, diseño de purga, diseño de redacción con
    ejemplos, y diseño de anonimización EXIF con la justificación
    JPEG/TIFF. **Cumple en estructura y cobertura de temas; contiene la
    inexactitud señalada en el veredicto** (afirmación de un test numpy
    que no existe).
12. **`docs/usuario/seguridad-privacidad-documentos.md`** — existe, 159
    líneas, no vacío, con propósito de los controles, variables de
    entorno configurables y sus defaults, y ejemplo HTTP de rechazo de
    upload inválido (confirmado presente en el archivo). **Cumple.**
13. **`decision.md` + enlaces en índices** — `runs/14-seguridad-privacidad-documentos/decision.md`
    existe y no está vacío (decisiones trazadas a código/tests concretos,
    ver contenido citado arriba); enlaces exactos y con el mismo título
    (`Seguridad y Privacidad de Documentos`) en `docs/tecnica/index.md` y
    `docs/usuario/index.md`. **Cumple.**
14. **`Assert-FeatureContract` pasa** — pasaba todo salvo el
    `test-report-N.md` faltante, que este mismo artefacto provee. **Cumple**
    una vez agregado este reporte (a re-verificar por el orquestador tras
    el commit).

## 4. Foco especial: criterio 9 (anonimización EXIF)

### JPEG

`_anonymize_jpeg` (`backend/app/exif_privacy.py`) usa
`Image.getexif()`, borra todos los tags salvo `Orientation` (274),
reinserta `Orientation` explícitamente por si el borrado in-place lo
afectó, y re-guarda con `quality="keep"` (reutiliza las tablas de
cuantización JPEG originales, evitando una segunda pasada de compresión
con pérdida). Fallback documentado (`quality=95` si `quality="keep"`
falla; devuelve el original sin tocar si todo falla).

Tests reales (vía `POST /api/v1/jobs` real, no mocks):
- `test_exif_anonymization_jpeg_strips_identifying_tags_preserves_orientation`:
  fixture JPEG con `Make`/`Model`/`Orientation=6`/`GPSInfo` reales
  (seteados con `img.getexif()` + `get_ifd`), sube vía la API, abre el
  archivo resultante en `output/uploads/` con `PIL.Image.open(dest).getexif()`
  y confirma `Orientation == 6` y ausencia de `Make`/`Model`/`GPSInfo`.
- `test_exif_anonymization_jpeg_does_not_recompress_pixel_data`: compara
  `Image.open(...).quantization` del archivo fuente contra el resultante
  — verificación directa de no-recompresión, tal como exige el criterio 9
  del spec (no solo tamaño de archivo).
- `test_exif_anonymization_jpeg_without_exif_is_noop`: imagen sin EXIF no
  se modifica.

### TIFF

`_anonymize_tiff`/`_strip_tiff_ifd0` edita el IFD0 a nivel de bytes
(`struct`, sin `Image.open`/`Image.save` en el camino principal): parsea
header (`II`/`MM`, magic 42, offset IFD0), filtra las entradas cuyo tag
está en `TIFF_IDENTIFYING_TAG_IDS` (no incluye 274/`Orientation`, que
queda preservado), escribe la tabla reducida al final del archivo
original y actualiza solo el puntero del header — deja todos los demás
bytes, incluidos los de píxel, sin tocar. Verifiqué directamente en el
código (no solo en la documentación) que esta implementación:
- Nunca decodifica píxeles (no hay ninguna llamada a `Image.load()`/
  `Image.save()` en el camino principal `_strip_tiff_ifd0`) — evita el
  problema real que la propia doc documenta: `TiffImagePlugin.load_end()`
  aplica `exif_transpose` y borra `Orientation` en cualquier
  `Image.open().load()`, lo cual haría inviable preservar `Orientation`
  intacto si se usara el mismo camino que JPEG.
- El fallback (estructura no parseable) sí pasa por Pillow y acepta
  explícitamente la limitación de perder `Orientation` en ese caso
  borde — documentado como último recurso, consistente con el caso borde
  del spec ("eliminar el bloque EXIF entero en vez de fallar").

Tests reales (vía `POST /api/v1/jobs`, no mocks/stubs):
- `test_exif_anonymization_tiff_strips_identifying_tags_preserves_orientation`:
  misma fixture con `Make`/`Model`/`Orientation=6`/`GPSInfo`, verifica
  sobre el archivo persistido en disco que `Orientation == 6` y que
  `Make`/`Model`/`GPSInfo` fueron eliminados. Ejercita el camino de bytes
  real (`_strip_tiff_ifd0`), no un stub.
- `test_exif_anonymization_tiff_preserves_size_and_mode`: compara `.size`
  y `.mode` del archivo fuente contra el resultante — exactamente el
  método de verificación que el spec pide para TIFF (criterio 9,
  párrafo TIFF: "comparando dimensiones (size) y modo de color (mode)").
- `test_exif_anonymization_tiff_without_exif_is_noop` y
  `test_exif_anonymization_corrupt_content_does_not_raise` (TIFF con
  firma válida pero cuerpo truncado, `garbage = b"II*\x00" + b"\x00"*4`):
  cubren los casos borde de no-op seguro y de EXIF/estructura corrupta
  sin romper el upload.

**Conclusión del foco especial:** el mecanismo de TIFF es real (edición
de bytes verificable en el código, no un mock), preserva `Orientation`
intacto y no toca píxeles, y los tests correspondientes ejercitan el
flujo real de subida contra archivos TIFF genuinos generados con Pillow,
verificando el resultado en el archivo persistido en disco — no hay
ningún test dummy que no pruebe nada. El único defecto encontrado es la
oración de `docs/tecnica/` que reclama un método de verificación (numpy)
distinto y más fuerte del que efectivamente se implementó, lo cual es una
inexactitud de documentación, no una falla de test ni de código.

## 5. Commit de este artefacto

Se agrega `runs/14-seguridad-privacidad-documentos/test-report-1.md` en
un commit propio en la rama `feature/14-seguridad-privacidad-documentos`,
sin tocar `ROADMAP.md` (paso posterior del orquestador).
