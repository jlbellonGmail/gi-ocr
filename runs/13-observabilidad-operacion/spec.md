# Spec: 13-observabilidad-operacion

## Alcance

Esta feature agrega observabilidad completa al sistema: logs estructurados, métricas y trazabilidad por job/documento.

**Incluye:**
- Logs estructurados (JSON) en stdout/stderr con campos consistentes
- Métricas Prometheus expuestas en `/metrics` (tiempos OCR, estados de cola, errores por etapa, campos aceptados/rechazados/no encontrados)
- Health/readiness endpoints (`/health`, `/ready`) con checks reales
- Trazabilidad por job: correlation_id propagado en logs y métricas
- Runbook operativo documentado

**NO incluye:**
- Sistema de alerting externo (Prometheus Alertmanager, Grafana, etc.)
- Dashboards Grafana (solo métricas expuestas)
- Trazabilidad distribuida tipo OpenTelemetry/Jaeger (solo correlation_id local)

## Contexto

Hoy el sistema tiene:
- `JobQueue` con estados: queued, processing, ready, confirmed, failed, needs_new_photo
- `capture_pipeline.py` con `timings` por etapa (ocr_det_s, classify_rec_s, ocr_rec_s, total_s)
- `field_report` con accepted/rejected/missing/summary_counts
- `quality_gate` con veredictos ok/warn/reject
- `storage_bridge` con ready/failed

Pero no hay:
- Logs estructurados parseables
- Métricas expuestas para scraping
- Health checks que validen dependencias (OCR engine, disco, cola)
- Correlation ID para trazar un job end-to-end
- Runbook de operación

## Criterios de aceptación

1. **Logs estructurados**: Todos los logs de `backend/app/` usan `structlog` o `logging` con formatter JSON. Campos mínimos: `timestamp`, `level`, `logger`, `message`, `job_id` (cuando aplica), `stage` (ocr, extraction, validation, confirm, bridge), `duration_ms` (cuando aplica). No logs en formato texto plano en producción.

2. **Endpoint `/metrics`**: Expone métricas Prometheus:
   - `gi_ocr_jobs_total{status="queued|processing|ready|confirmed|failed|rejected"}` (counter)
   - `gi_ocr_job_duration_seconds{stage="ocr_det|classify_rec|ocr_rec|total",quantile="0.5|0.95|0.99"}` (histogram)
   - `gi_ocr_fields_total{result="accepted|rejected|missing",service="GAS|CEVT"}` (counter)
   - `gi_ocr_queue_size` (gauge)
   - `gi_ocr_storage_bridge_files{state="ready|failed"}` (gauge)
   - `gi_ocr_ocr_engine_loaded` (gauge 0/1)
   - `gi_ocr_disk_usage_bytes{path="storage_bridge|output|uploads"}` (gauge)

3. **Health/Readiness endpoints**:
   - `GET /api/v1/health` → 200 si proceso vivo, engine OCR cargado, cola funcional
   - `GET /api/v1/ready` → 200 si listo para recibir tráfico (engine cargado, disco escribible, cola no saturada), 503 en caso contrario

4. **Correlation ID**: Cada job genera `correlation_id` (UUID) al encolar. Se propaga en:
   - Logs de todas las etapas del job
   - Métricas con label `job_id`
   - Headers de respuesta HTTP (`X-Correlation-ID`)
   - Archivos `.DATA`/`.CONFIDENCE.json` en `confirmation_metadata`

5. **Runbook operativo**: `docs/operacion/runbook.md` con:
   - Cómo interpretar métricas clave
   - Alertas recomendadas (umbrales)
   - Procedimientos: job atascado, disco lleno, OCR engine caído, reconciliación bridge
   - Comandos útiles (reintentar job, forzar reconciliación, ver logs)

6. **Documentación técnica**: `docs/tecnica/observabilidad-operacion.md` no vacío, con arquitectura de logs/métricas, decisiones de diseño, campos de log, métricas expuestas.

7. **Documentación de usuario**: `docs/usuario/observabilidad-operacion.md` no vacío, con propósito de endpoints, ejemplos de consulta Prometheus/Grafana, salud del sistema.

8. **Decision.md**: `runs/13-observabilidad-operacion/decision.md` con decisiones demostrables.

9. **Enlaces en índices**: Exactos en `docs/tecnica/index.md` y `docs/usuario/index.md`.

## Casos borde a contemplar

1. **Job sin correlation_id** (legacy): fallback a job_id, log warning
2. **Métricas con cardinalidad alta**: `service` y `stage` son labels de baja cardinalidad; `job_id` NO es label (usar solo en logs)
3. **Disco lleno al escribir métricas/logs**: no bloquear procesamiento, log error rate-limited
4. **OCR engine no cargado**: `/ready` devuelve 503, `/health` devuelve degraded
5. **Cola saturada**: `/ready` devuelve 503 si `queue_size > max_workers * 10`
6. **Logs en desarrollo vs producción**: desarrollo = pretty console; producción = JSON stdout

## Riesgos / supuestos

1. **Supuesto**: Métricas Prometheus son pull (scraping), no push. No hay Gateway.
2. **Supuesto**: `prometheus-client` librería estándar Python. No añade dependencias pesadas.
3. **Decisión**: No OpenTelemetry en esta fase. Correlation ID manual es suficiente para MVP local.
4. **Riesgo**: Cardinalidad de métricas. Control: solo labels `service` (GAS/CEVT/UNKNOWN), `stage` (fijos), `status` (fijos). `job_id` solo en logs.
5. **Riesgo**: Logs JSON pueden ser verbosos. Control: nivel INFO default, DEBUG solo bajo flag env.
6. **Compatibilidad**: No rompe API existente. Endpoints nuevos `/metrics`, `/ready` son aditivos.