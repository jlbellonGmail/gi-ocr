# Decision: 12-contrato-integracion-legacy-v2

## Decisiones demostrables desde spec / auditoría / implementación

### 1. Formato `.DATA` v2 — línea `VERSION=2` separada
**Origen**: Spec CA#1, Auditoría obs. menor #1
**Decisión**: Primera línea `VERSION=2`, segunda línea header, tercera valores.
**Alternativa descartada**: `VERSION=2;campo1;campo2` en una línea.
**Justificación**: No rompe parsers legacy que esperan `splitlines()[0]=header`. Lectores v2 detectan y saltan línea de versión.
**Evidencia**: `storage_bridge_writer.py:build_data_content` lines 72-75.

### 2. Hash SHA-256 para idempotencia por contenido
**Origen**: Spec CA#8, Auditoría feedback #2
**Decisión**: Hash del contenido normalizado completo (`VERSION=2\nheader\nvalues\n`).
**Implementación**: `compute_data_hash()` + `_find_existing_by_hash()` escanean `ready/` antes de escribir.
**Justificación**: Costo <1ms. Detecta duplicados lógicos aunque nombre de archivo difiera (re-procesamiento con nuevo timestamp).
**Evidencia**: `storage_bridge_writer.py` lines 176-200.

### 3. Correlación job_id ↔ .DATA en reconciliación
**Origen**: Spec CA#11, Auditoría obs. menor #3
**Decisión**: Heurística service+timestamp + verificación hash. `job_id` no está en `.DATA`.
**Implementación**: `reconcile_storage_bridge()` extrae service+timestamp del nombre de archivo `.DATA` y correlaciona con `confirmed_at` del JSON. Si hash coincide → match.
**Limitación conocida**: Si re-procesamiento genera nuevo timestamp, correlación por timestamp falla; fallback a hash cubre caso de mismo contenido.
**Evidencia**: `storage_bridge_writer.py:reconcile_storage_bridge` lines 340-420.

### 4. Reintentos con backoff exponencial simple
**Origen**: Spec CA#9
**Decisión**: 100/200/400/800ms (4 intentos totales), sin jitter.
**Parámetros configurables**: `max_retries=3`, `base_delay_ms=100` en `write_atomic_data_file_with_retry()`.
**Justificación**: Entorno local controlado, sin contienda distribuida. Jitter innecesario.
**Evidencia**: `storage_bridge_writer.py` lines 250-330.

### 5. Registro de errores en `failed/*_error.json`
**Origen**: Spec CA#10
**Decisión**: Además del `.tmp` existente, escribir `{service}_YYYYMMDD_HHMMSS_error.json` con metadata completa.
**Campos**: service, timestamp, error, error_type, attempts, fields, values_hash.
**Justificación**: Permite diagnóstico post-mortem sin logs de aplicación.
**Evidencia**: `storage_bridge_writer.py:_write_error_record` lines 202-248.

### 6. No versionar JSON confirmado en `storage_bridge/`
**Origen**: Spec Riesgo #3
**Decisión**: JSON confirmado solo en `output/confirmed/`. Legacy consume solo `.DATA`.
**Justificación**: Separación de responsabilidades. `.DATA` = contrato legacy estable. JSON = API interna versionada por separado.
**Futuro**: Si legacy requiere JSON → v3 con ambos en bridge.

### 7. Timestamp collision handling
**Origen**: Spec Caso borde #1
**Decisión**: Sufijo `_001`..`_999` en nombre de archivo si `ready/SERVICIO_TS.DATA` ya existe.
**Implementación**: Loop en `write_atomic_data_file_with_retry` lines 285-295.
**Límite**: 999 intentos → `RuntimeError` (prácticamente imposible).

### 8. Lectura tolerante v1, escritura obligatoria v2
**Origen**: Spec Caso borde #5
**Decisión**: `_find_existing_by_hash` y `reconcile_storage_bridge` ignoran archivos sin `VERSION=2`. Escritura siempre v2.
**Justificación**: Migración gradual. Archivos v1 históricos en `ready/` no bloquean ni se cuentan en reconciliación v2.

### 9. Endpoint admin `/api/v1/admin/reconcile`
**Origen**: Spec CA#11
**Decisión**: Requiere role ADMIN. Devuelve reporte completo + path a archivo JSON persistido en `output/reconciliation/`.
**Justificación**: Operación de diagnóstico, no de uso frecuente. Solo admin.

### 10. Contrato v2 en JSON confirmado: `contract_version: 2`
**Origen**: Spec CA#2
**Decisión**: Campo en `confirmation_metadata`.
**Implementación**: `review_service.py` line 118.

## Decisiones de arquitectura NO tomadas (explicitamente fuera de alcance)

- Auth/TLS/reverse proxy (ADR-009)
- Backup/rotación `storage_bridge/ready/` (responsabilidad legacy, ADR-001)
- Resiliencia JobQueue ante restart (ADR-009)
- Migración automática v1→v2 (documentada como deuda, script opcional futuro)

## Evidencia de cierre

- Spec: `runs/12-contrato-integracion-legacy-v2/spec.md` ✅
- Auditoría: `runs/12-contrato-integracion-legacy-v2/audit-1.md` (approved) ✅
- Implementación: `backend/app/storage_bridge_writer.py`, `backend/app/review_service.py`, `backend/app/main.py` ✅
- Doc técnica: `docs/tecnica/contrato-integracion-legacy-v2.md` ✅
- Doc usuario: `docs/usuario/contrato-integracion-legacy-v2.md` ✅
- Índices actualizados: `docs/tecnica/index.md`, `docs/usuario/index.md` ✅
- Tests: Pendientes (QA phase) 🔄