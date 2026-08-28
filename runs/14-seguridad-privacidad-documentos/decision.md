# Decision: 14-seguridad-privacidad-documentos - Seguridad y Privacidad de Documentos

## Estado

Implementación completa del spec aprobado (intento 3,
`runs/14-seguridad-privacidad-documentos/audit-3.md`, veredicto
`approved`). Lista para que `qa-agent` corra el contrato completo
(`Assert-FeatureContract`) y la suite de tests.

## Evidencias revisadas

- `runs/14-seguridad-privacidad-documentos/spec.md` (14 criterios de
  aceptación, casos borde y riesgos/supuestos).
- `runs/14-seguridad-privacidad-documentos/audit-1.md`,
  `audit-2.md`, `audit-3.md` (historial de correcciones: gap de
  anonimización EXIF agregado en audit-1, riesgo de recompresión JPEG y
  cobertura TIFF agregados en audit-2, `approved` en audit-3).
- Código implementado (ver "Decisiones demostrables").
- Suite de tests nueva: `backend/tests/test_upload_security.py`,
  `backend/tests/test_exif_privacy.py`, `backend/tests/test_retention.py`
  (28 tests nuevos, todos en verde localmente).

## Decisiones demostrables

- **Validación de firma (magic bytes) sin dependencia nueva**
  (`backend/app/upload_validation.py::SIGNATURES`): tabla estática para
  JPEG/PNG/TIFF/PDF, verificada con `detect_signature`. Un `.txt`
  renombrado a `.jpg` se rechaza con `signature_mismatch` (415) sin dejar
  archivo en `output/uploads/` — test:
  `test_upload_rejects_signature_mismatch_and_leaves_no_file`.
- **Content-Type vs. firma real**
  (`upload_validation.validate_upload_content`): Content-Type ausente,
  vacío o `application/octet-stream` nunca se trata como mismatch (confía
  solo en la firma); cualquier otro valor inconsistente con la familia
  detectada se rechaza como `content_type_mismatch` (415) — tests:
  `test_content_type_mismatch_rejected`,
  `test_content_type_absent_accepted_for_tiff`.
- **Tamaño máximo configurable** (`upload_validation.max_upload_bytes`,
  `GI_OCR_MAX_UPLOAD_BYTES`, default 30 MB) — test:
  `test_max_upload_bytes_configurable_via_env`,
  `test_max_upload_bytes_defaults_to_30mb_when_unset`.
- **Nombre de archivo aleatorio** (`upload_validation.random_upload_name`,
  `secrets.token_hex(16)`, 128 bits): reemplaza el esquema previo
  `{timestamp}_{nombre_sanitizado}` en `main._save_upload` — test:
  `test_uploaded_filename_is_random_not_derived_from_original`.
- **Permisos de filesystem restrictivos** (`backend/app/fs_permissions.
  py::secure_file/secure_dir`, no-op documentado en Windows): aplicado en
  `main._save_upload`, `job_store.JobStore` (init + save_original/
  save_confirmed), `storage_bridge_writer.write_atomic_data_file`,
  `inbound_watcher.InboundWatcher.__init__` — tests gateados a POSIX
  (`skipif os.name != "posix"`) más un test cross-platform del no-op en
  Windows (`test_fs_permissions_is_noop_on_non_posix`).
- **Purga/retención configurable** (`backend/app/retention.py`):
  `GI_OCR_UPLOAD_RETENTION_DAYS` (7), `GI_OCR_JOB_RETENTION_DAYS` (90),
  `GI_OCR_FAILED_RETENTION_DAYS` (30), `inbound/` de raíz comparte umbral
  con uploads. `storage_bridge/ready/` nunca es target (decisión ya
  justificada en el spec, ver "Riesgos/supuestos"). Jobs `queued`/
  `processing` protegidos por diseño en `output/jobs/`/`confirmed/` (esos
  archivos solo existen para jobs ya terminados) y vía `JobStore` opcional
  para `output/uploads/` — tests: `backend/tests/test_retention.py` (11
  tests).
- **Helper de redacción reutilizable** (`backend/app/redaction.py`),
  aplicado en `job_queue.JobQueue._process` (`job["error"]` y payload SSE)
  — reemplaza rutas absolutas por su nombre base, sin filtrar el nombre
  original del cliente ni la estructura de directorios del servidor —
  test: `test_job_error_redacts_absolute_path_marker`.
- **Anonimización EXIF** (`backend/app/exif_privacy.py`): JPEG vía Pillow
  (`quality="keep"`, fallback documentado `quality=95`); TIFF vía edición
  directa del IFD0 a nivel de bytes (sin decodificar píxeles), decisión
  tomada tras verificar empíricamente que `TiffImagePlugin.load_end()`
  aplica y descarta el tag `Orientation` automáticamente en cualquier
  `.load()` de Pillow (`Pillow==12.2.0`, dentro de `Pillow>=10.2.0` de
  `requirements.txt`) — documentado en detalle en
  `docs/tecnica/seguridad-privacidad-documentos.md`, sección 5. Tests:
  `backend/tests/test_exif_privacy.py` (10 tests, JPEG + TIFF + no-op +
  corrupto).
- **Límite documentado, no resuelto en esta ronda**: la firma detectada no
  se contrasta contra la extensión declarada de forma independiente del
  Content-Type (un tipo soportado subido con extensión de otro tipo
  soportado, con Content-Type coherente con la firma real, pasa la
  validación). El criterio 1 del spec exige rechazar únicamente firmas que
  no correspondan a ninguno de los 4 tipos soportados; ampliar ese
  chequeo queda fuera de esta ronda — documentado explícitamente en
  `docs/tecnica/seguridad-privacidad-documentos.md`, sección 1.

## Resultado

La feature queda apta para integrarse/cerrarse cuando GitHub confirme
merge contra `develop` y el cierre automático marque `ROADMAP.md`.
