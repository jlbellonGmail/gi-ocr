# Spec: 12-contrato-integracion-legacy-v2

## Alcance

Esta feature formaliza la version 2 del contrato de integración con el sistema externo/legacy vía `storage_bridge/`. Cubre:

**Incluye:**
- Versionado explícito del formato `.DATA` (v2) y JSON confirmado (v2)
- Encoding, separador, orden de campos, nomenclatura de archivos
- Idempotencia: mismo `job_id` + mismo contenido = misma salida en `ready/`
- Detección y manejo de duplicados (basado en hash/contenido + timestamp)
- Política de reintentos con backoff exponencial y límite configurable
- Estados formales `ready`/`failed` con transiciones documentadas
- Reconciliación automática: escaneo de `ready/` vs. registro interno, reporte de desfasajes
- Documentación técnica (`docs/tecnica/contrato-integracion-legacy-v2.md`) y de usuario (`docs/usuario/contrato-integracion-legacy-v2.md`)

**NO incluye:**
- Cambio de motor OCR ni plantillas de extracción (ADR-006, ADR-007)
- Autenticación/TLS/reverse proxy (fuera de alcance por ADR-009)
- Backup/rotación de `storage_bridge/ready/` (responsabilidad del sistema legacy, ADR-001)
- Resiliencia de `JobQueue` ante restart (explícitamente fuera de ADR-009)

## Contexto

El sistema actual genera:
1. **JSON confirmado**: resultado completo del pipeline + correcciones humanas, guardado en `output/confirmed/<job_id>.confirmed.json` y descargable via `/api/v1/jobs/{job_id}/download`
2. **Archivo `.DATA`**: formato legacy plano (header `;` + valores `;`), escrito atómicamente a `storage_bridge/ready/` via `storage_bridge_writer.py`

Hoy el contrato es implícito (código y tests), no versionado formalmente. El sistema legacy consume `storage_bridge/ready/*.DATA` pero no hay:
- Versionado explícito para evoluciones futuras sin romper compatibilidad
- Garantía de idempotencia (re-procesar mismo job puede crear duplicados en `ready/`)
- Política de reintentos documentada para escrituras fallidas
- Reconciliación automática entre estado interno (`output/confirmed/`) y `storage_bridge/ready/`

Esta feature cierra esa brecha para que la integración sea operable en producción con garantías contractuales.

## Criterios de aceptación

1. **Versionado v2 en `.DATA`**: El archivo `.DATA` incluye una línea de versión como primera línea: `VERSION=2` (antes del header de campos). Formato v1 (sin línea VERSION) se sigue aceptando en lectura para compatibilidad, pero toda escritura nueva es v2.
2. **Versionado v2 en JSON confirmado**: El JSON confirmado incluye `"contract_version": 2` en `confirmation_metadata`.
3. **Encoding**: UTF-8 sin BOM para ambos formatos (`.DATA` y JSON). Validado en tests.
4. **Separador**: Punto y coma (`;`) para `.DATA` (ya implementado, ahora contractual). JSON usa estándar RFC 8259.
5. **Orden de campos**: Determinista según orden declarado en `services.ini` (`Fields=...`). Tests verifican orden exacto.
6. **Nombres de archivo**: `SERVICIO_YYYYMMDD_HHMMSS.DATA` (ej. `GAS_20260826_153045.DATA`). Servicio normalizado a mayúsculas, sin caracteres inválidos. Timestamp UTC.
7. **Idempotencia**: `write_atomic_data_file` con mismo `service` + mismo `timestamp` (secuencia) + mismos `fields` + mismos `values` → NO crea duplicado en `ready/`; lanza `FileExistsError` si ya existe archivo con ese nombre exacto. El llamador debe manejar reintentos con nuevo timestamp si corresponde.
8. **Detección de duplicados por contenido**: Nueva función `compute_data_hash(service, fields, values)` que genera hash SHA-256 del contenido normalizado. Antes de escribir, se escanea `ready/` para detectar si ya existe un `.DATA` con mismo hash (mismo contenido lógico). Si existe, se retorna el path existente sin reescribir (idempotencia por contenido, no solo por nombre).
9. **Reintentos**: `write_atomic_data_file_with_retry(service, fields, values, max_retries=3, base_delay_ms=100)` que reintenta con backoff exponencial (100ms, 200ms, 400ms...) ante fallos transitorios (IOError, PermissionError, atomic move failure). Lanza excepción final tras agotar reintentos.
10. **Estados `ready`/`failed`**: 
    - `ready/`: archivo `.DATA` escrito atómicamente + `.CONFIDENCE.json` compañero (feature 09). Estado final exitoso.
    - `failed/`: archivo `.DATA.tmp` movido allí cuando falla el atomic move (ya implementado). Nuevo: registro de error en `failed/<timestamp>_<service>_error.json` con `{service, timestamp, error, attempts, fields, values_hash}`.
11. **Reconciliación**: Script/endpoint `reconcile_storage_bridge()` que:
    - Lista todos `output/confirmed/*.confirmed.json` con `contract_version=2`
    - Lista todos `storage_bridge/ready/*.DATA` v2
    - Compara por `job_id` (extraíble del JSON confirmado) y por hash de contenido
    - Reporta: `missing_in_ready` (confirmados sin `.DATA`), `orphan_in_ready` (`.DATA` sin confirmado correspondiente), `content_mismatch` (mismo job_id, distinto hash)
    - Genera reporte JSON en `output/reconciliation/<timestamp>_report.json`
    - Endpoint admin: `POST /api/v1/admin/reconcile` (requiere role ADMIN)
12. **Documentación técnica**: `docs/tecnica/contrato-integracion-legacy-v2.md` no vacío, con algoritmo, decisiones de diseño, casos borde, matriz de compatibilidad v1/v2.
13. **Documentación de usuario**: `docs/usuario/contrato-integracion-legacy-v2.md` no vacío, con propósito, ejemplos HTTP request/response para confirmación y descarga, formato `.DATA` v2 ejemplificado.
14. **Decision.md**: `runs/12-contrato-integracion-legacy-v2/decision.md` con decisiones demostrables desde spec/auditoría/implementación.
15. **Enlaces en índices**: Enlaces exactos en `docs/tecnica/index.md` y `docs/usuario/index.md` a los nuevos `.md`.

## Casos borde a contemplar

1. **Timestamp collision**: Dos jobs del mismo servicio en el mismo segundo → timestamp incluye microsegundos o secuencia (`_001`, `_002`) en nombre de archivo para evitar colisión.
2. **Servicio nuevo no en `services.ini`**: Validación temprana, error claro antes de escribir.
3. **Campo con separador `;` en valor**: Ya validado en `storage_bridge_writer.py` (lanza ValueError). Contrato lo documenta como regla dura.
4. **Campo con salto de línea**: Igual, validado y documentado.
5. **Archivo `.DATA` v1 legacy en `ready/`**: Lectura tolerante (ignorar ausencia de línea VERSION), pero escritura siempre v2.
6. **Permisos de filesystem**: `secure_dir`/`secure_file` ya aplicados; contrato documenta umask esperada.
7. **Disco lleno / cuota**: Manejo graceful en reintentos, error final claro.
8. **Reconciliación con jobs parciales**: Jobs en estado `ready` pero sin confirmar → no aparecen en reporte de `missing_in_ready` (solo confirmados).
9. **Migración v1→v2**: Script `migrate_data_v1_to_v2.py` opcional para backfill histórico (fuera de scope MVP, documentado como deuda).

## Riesgos / supuestos

1. **Supuesto**: El sistema legacy lee `storage_bridge/ready/*.DATA` y procesa secuencialmente. No modifica ni borra archivos ahí. Si el legacy mueve/borra, la reconciliación detecta `orphan_in_ready` pero no puede recuperarlo.
2. **Supuesto**: `job_id` (32 hex chars) es único global y trazable. Se usa como clave de correlación entre JSON confirmado y `.DATA`.
3. **Decisión**: No se versiona el JSON confirmado en `storage_bridge/` (solo en `output/confirmed/`). El legacy consume solo `.DATA`. Si en futuro se requiere JSON en bridge, será v3.
4. **Decisión**: Hash de contenido (SHA-256) para detección de duplicados lógicos. Costo computacional despreciable vs. beneficio de idempotencia fuerte.
5. **Riesgo**: Reconciliación puede ser lenta si hay miles de archivos en `ready/`. Implementación inicial sincrónica; si supera 5s, mover a job asíncrono (fuera de scope).
6. **Riesgo**: `write_atomic_data_file` hoy lanza `FileExistsError` si archivo existe en `ready/`. Nueva lógica de idempotencia por contenido debe mantener compatibilidad: si nombre existe pero contenido difiere → error (no sobrescribir). Si nombre y contenido iguales → ok, retorna existente.