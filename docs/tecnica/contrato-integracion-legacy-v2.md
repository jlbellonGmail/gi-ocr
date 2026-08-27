# Contrato de Integración Legacy v2

Versión 2 del contrato de intercambio de archivos entre gi-ocr y el sistema externo/legacy vía `storage_bridge/`.

## Resumen

- **Formato salida legacy**: `.DATA` (plano, separador `;`, UTF-8)
- **Formato confirmado interno**: JSON (RFC 8259, UTF-8)
- **Versión contractual**: 2 (línea `VERSION=2` en `.DATA`, campo `contract_version: 2` en JSON)
- **Ubicación**: `storage_bridge/ready/` (éxito), `storage_bridge/failed/` (errores)
- **Escritura**: Atómica (tmp → rename) con idempotencia y reintentos

## Formato `.DATA` v2

### Estructura

```
VERSION=2
campo1;campo2;campo3
valor1;valor2;valor3
```

### Reglas

1. **Primera línea**: `VERSION=2` (obligatorio en escritura v2; lectura tolerante a v1 sin esta línea)
2. **Segunda línea**: Nombres de campos separados por `;` — orden exacto según `Fields=` en `services.ini`
3. **Tercera línea en adelante**: Valores correspondientes, mismo orden, separados por `;`
4. **Encoding**: UTF-8 sin BOM
5. **Fin de línea**: LF (`\n`) únicamente
6. **Valores vacíos**: Campo presente pero vacío entre separadores (`;;`)
7. **Prohibido en valores**: `;`, `\n`, `\r` (validado en escritura, lanza `ValueError`)

### Ejemplo (GAS)

```
VERSION=2
importe;cliente;nro_medidor;a_pagar_hasta;periodo
23.345,56;045-987654;34572;20/06/2026;01/2026
```

### Nomenclatura de archivo

`SERVICIO_YYYYMMDD_HHMMSS[.seq].DATA`

- `SERVICIO`: Normalizado a mayúsculas, solo alfanumérico/guión/underscore (ver `normalize_service_name`)
- Timestamp: UTC, formato `YYYYMMDD_HHMMSS`
- `.seq`: Sufijo opcional `_001`, `_002`... para resolver colisiones en el mismo segundo

Ejemplos:
- `GAS_20260826_153045.DATA`
- `CEVT_20260826_153045_001.DATA`

## Formato JSON Confirmado v2

El JSON confirmado se genera en `output/confirmed/<job_id>.confirmed.json` y se expone vía `/api/v1/jobs/{job_id}/download`.

### Campos contractuales v2

```json
{
  "job_id": "abc123...",
  "document_type": "GAS",
  "confirmed_fields": { "importe": "23.345,56", "cliente": "045-987654", ... },
  "validated_fields": { ... },
  "corrections": ["importe"],
  "summary": { "confirmed_count": 4, "corrected_count": 1, "unresolved_count": 0 },
  "confirmation_metadata": {
    "final_filename": "GAS_abc12345.json",
    "confirmed_at": "2026-08-26T15:30:45.123456+00:00",
    "original_source": "/path/to/upload.jpg",
    "confidence_at_review": { ... },
    "decision_at_review": { "importe": "corrected", "cliente": "confirmed", ... },
    "correction_reasons": { "importe": "OCR leyó 23.345,66" },
    "audit_trail": [ { "field": "importe", "operator_id": "op1", "original_value": "23.345,66", "final_value": "23.345,56", "action": "corrected", "reason": "OCR leyó 23.345,66", "timestamp": "..." } ],
    "contract_version": 2,
    "data_file": "storage_bridge/ready/GAS_20260826_153045.DATA",
    "confidence_file": "storage_bridge/ready/GAS_20260826_153045.CONFIDENCE.json",
    "data_hash": "sha256:abc123..."
  },
  "original_result_ref": "abc123..."
}
```

### Archivo `.CONFIDENCE.json` compañero

Se genera junto al `.DATA` en `storage_bridge/ready/`:

```json
{
  "service": "GAS",
  "timestamp": "2026-08-26T15:30:45.123456+00:00",
  "field_confidence": {
    "importe": { "ocr_score": 0.92, "extraction_score": 1.0, "final_score": 0.95, "decision": "auto_accepted", ... },
    "cliente": { ... }
  }
}
```

## Idempotencia

Dos niveles:

1. **Por nombre de archivo**: `write_atomic_data_file` lanza `FileExistsError` si `ready/SERVICIO_TS.DATA` ya existe.
2. **Por contenido (hash SHA-256)**: `write_atomic_data_file_with_retry` calcula hash del contenido normalizado (`VERSION=2\nheader\nvalues\n`) y escanea `ready/` antes de escribir. Si existe archivo con mismo hash → retorna el existente sin reescribir.

Esto permite re-procesar el mismo job (mismo contenido lógico) sin crear duplicados en `ready/`.

## Detección de duplicados

Hash SHA-256 del contenido normalizado completo. Normalización incluye:
- Servicio uppercase
- Campos en orden declarado
- Valores normalizados (vacío → `""`, sin `;`, sin saltos de línea)

## Reintentos

`write_atomic_data_file_with_retry(max_retries=3, base_delay_ms=100)`:

| Intento | Delay |
|---------|-------|
| 1       | 100ms |
| 2       | 200ms |
| 3       | 400ms |
| 4       | 800ms (fallo final) |

Reintenta ante: `IOError`, `OSError`, `PermissionError`, `RuntimeError` (atomic move failure).
Tras agotar reintentos: registra error en `failed/` y lanza la última excepción.

## Estados `ready` / `failed`

### `storage_bridge/ready/`
- Archivo `.DATA` v2 escrito atómicamente
- Archivo `.CONFIDENCE.json` compañero
- Estado final exitoso — listo para consumo por sistema legacy

### `storage_bridge/failed/`
- Archivo `.DATA.tmp` movido allí cuando falla el atomic move (comportamiento existente)
- **Nuevo**: Archivo `{SERVICIO}_YYYYMMDD_HHMMSS_error.json` con:
```json
{
  "service": "GAS",
  "timestamp": "2026-08-26T15:30:45.123456+00:00",
  "error": "Permission denied",
  "error_type": "PermissionError",
  "attempts": 4,
  "fields": ["importe", "cliente", ...],
  "values_hash": "sha256:abc123..."
}
```

## Reconciliación

Función `reconcile_storage_bridge(confirmed_dir, ready_dir, output_dir)` y endpoint `POST /api/v1/admin/reconcile` (requiere ADMIN).

### Algoritmo

1. Carga todos `output/confirmed/*.confirmed.json` con `contract_version=2`
2. Carga todos `storage_bridge/ready/*.DATA` v2 (con línea `VERSION=2`)
3. Correlaciona por `job_id` → service + timestamp + hash de contenido
4. Genera reporte:

```json
{
  "generated_at": "2026-08-26T15:35:00.000000+00:00",
  "contract_version": 2,
  "missing_in_ready": [
    { "job_id": "...", "service": "GAS", "expected_timestamp": "20260826_153045" }
  ],
  "orphan_in_ready": [
    { "ready_key": "GAS_20260826_153045", "service": "GAS", "timestamp": "20260826_153045", "path": "..." }
  ],
  "content_mismatch": [
    { "job_id": "...", "service": "GAS", "ready_key": "GAS_20260826_153045", "expected_hash": "...", "actual_hash": "..." }
  ],
  "summary": { "total_confirmed_v2": 100, "total_ready_v2": 98, "missing_count": 2, "orphan_count": 1, "mismatch_count": 0 },
  "report_path": "output/reconciliation/reconciliation_20260826_153500.json"
}
```

### Categorías

- **missing_in_ready**: Job confirmado v2 sin `.DATA` correspondiente en `ready/`
- **orphan_in_ready**: `.DATA` v2 en `ready/` sin job confirmado v2 correspondiente
- **content_mismatch**: Mismo job_id (correlacionado), pero hash de contenido difiere

## Compatibilidad v1 → v2

| Aspecto | v1 (actual) | v2 (nuevo) |
|---------|-------------|------------|
| `.DATA` primera línea | Header campos | `VERSION=2` |
| Lectura `.DATA` | Solo header+valores | Tolera v1 (sin VERSION), escribe v2 |
| JSON confirmado | Sin `contract_version` | `contract_version: 2` |
| Hash duplicados | No | SHA-256 contenido |
| Reintentos | No (fallo inmediato) | Backoff exponencial |
| Errores en `failed/` | Solo `.tmp` | `.tmp` + `_error.json` |
| Reconciliación | No | Sí (función + endpoint) |

Migración v1→v2: Script `migrate_data_v1_to_v2.py` (deuda documentada, fuera de scope MVP).

## Decisiones de diseño

1. **Versión en `.DATA` como primera línea**: No rompe parsers legacy que esperan header en línea 1 (legacy debe saltar primera línea si empieza con `VERSION=`). Alternativa considerada: header `VERSION=2;` en misma línea que campos — descartada por romper parsing simple `splitlines()`.

2. **Hash SHA-256 completo**: Costo computacional despreciable (<1ms). Alternativa: hash solo de valores — descartada porque cambios en orden de campos o nombres también deben detectarse.

3. **Reconciliación por `job_id` + timestamp + hash**: `job_id` no está en `.DATA`; correlación heurística por service+timestamp. Si timestamp no coincide exactamente (re-procesamiento), fallback a hash. Builder documenta decisión final en `decision.md`.

4. **No versionar JSON en bridge**: Legacy consume solo `.DATA`. JSON confirmado queda en `output/confirmed/`. Si futuro requiere JSON en bridge → v3.

5. **Backoff exponencial simple**: 100/200/400/800ms. Sin jitter (entorno controlado local). Configurable por parámetros.

## Casos borde

- **Timestamp collision**: Sufijo `_001`, `_002`... hasta 999 intentos.
- **Servicio no en `services.ini`**: Error temprano en `normalize_service_name` / validación de campos.
- **Valor con `;` o salto de línea**: `ValueError` en `_normalize_value` / `_validate_token`.
- **Permisos filesystem**: `secure_dir`/`secure_file` aplicados (umask restrictiva).
- **Disco lleno**: `OSError` capturado en reintentos, error final claro.
- **Jobs parciales (ready sin confirmar)**: No aparecen en `missing_in_ready` (solo confirmados v2).
- **Lectura `.DATA` v1 legacy**: Tolerada (ignora ausencia `VERSION=2`), pero escritura siempre v2.

## Testing

Ver `backend/tests/test_storage_bridge_writer.py` y nuevos tests:
- `test_build_data_content_includes_version_line`
- `test_compute_data_hash_deterministic`
- `test_write_atomic_data_file_with_retry_idempotent_by_hash`
- `test_write_atomic_data_file_with_retry_backoff`
- `test_write_error_record_on_exhausted_retries`
- `test_reconcile_storage_bridge_missing_orphan_mismatch`