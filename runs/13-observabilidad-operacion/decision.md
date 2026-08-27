# Decision: 13-observabilidad-operacion

## Decisiones demostrables desde spec / auditoría / implementación

### 1. Librería de logs: `structlog` + stdlib logging
**Origen**: Spec CA#1
**Decisión**: `structlog` para logs estructurados, wrapper sobre stdlib logging.
**Alternativas**: `loguru` (más simple pero menos estándar), `python-json-logger` (solo JSON, sin contexto).
**Justificación**: `structlog` es estándar en ecosistema Python, soporta contextvars, processors chain, y funciona con stdlib handlers. Compatible con Loki/ELK/Grafana.
**Evidencia**: `backend/app/logging_config.py`

### 2. Formato de logs: JSON en prod, pretty en dev
**Origen**: Spec CA#1, Caso borde #6
**Decisión**: `GI_OCR_ENV=production` → JSON; `development` → pretty console.
**Implementación**: `_is_dev()` check en `configure_logging()`.
**Justificación**: DX en desarrollo (legible), parseabilidad en prod (Loki/ELK).

### 3. Métricas: `prometheus-client` (pull model)
**Origen**: Spec CA#2, Riesgo #1
**Decisión**: Modelo pull estándar Prometheus. Sin Pushgateway.
**Alternativas**: Pushgateway (para batch jobs), OpenTelemetry (overkill para MVP).
**Justificación**: Estándar de facto, compatible con cualquier Prometheus server, sin dependencias extra.
**Evidencia**: `backend/app/metrics.py`, endpoint `/metrics` en `main.py`

### 4. Cardinalidad controlada en métricas
**Origen**: Spec CA#2, Caso borde #2, Riesgo #4
**Decisión**: Labels de baja cardinalidad únicamente:
- `service`: GAS, CEVT, UNKNOWN (3 valores)
- `stage`: ocr_det, classify_rec, ocr_rec, total (4 valores)
- `status`: queued, processing, ready, confirmed, failed, rejected (6 valores)
- `result`: accepted, rejected, missing (3 valores)
- `state`: ready, failed (2 valores)
- `path`: storage_bridge, output, uploads (3 valores)

**NO labels**: `job_id` (alta cardinalidad) → solo en logs.
**Justificación**: Evita explosión de series temporales en Prometheus.

### 5. Health vs Readiness endpoints separados
**Origen**: Spec CA#3
**Decisión**: 
- `/health`: liveness (proceso vivo + engine cargado) → 200/200 degraded
- `/ready`: readiness (puede recibir tráfico) → 200/503

**Checks de readiness**:
1. Engine OCR cargado
2. Disco > 100MB libre
3. Cola no saturada (< 10 jobs/worker)

**Justificación**: Patrón Kubernetes/cloud-native estándar. Load balancers usan `/ready` para quitar tráfico.

### 6. Correlation ID: header `X-Correlation-ID`
**Origen**: Spec CA#4
**Decisión**: Middleware `CorrelationIdMiddleware` genera UUID si no viene en request. Propaga en response header y `request.state`.
**Alternativas**: OpenTelemetry traceparent (W3C), X-Request-ID (nginx).
**Justificación**: Simple, estándar de facto, funciona sin instrumentación distribuida. Compatible con W3C traceparent si se migra futuro.

### 7. Histogram buckets para latencias
**Origen**: Spec CA#2, Obs. menor #1
**Decisión**: Buckets: [0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0] segundos.
**Justificación**: Cubre rango típico OCR (2-5s) + colas + timeouts. Permite p50/p95/p99 precisos.

### 8. Métricas de disco actualizadas en startup + health check
**Origen**: Spec CA#2, Decisión #6
**Decisión**: No en cada request (overhead). Actualizadas en startup, shutdown, y cada `/ready` check.
**Evidencia**: `_update_disk_usage_metrics()` llamado en startup y readiness.

### 9. Métricas de storage bridge
**Origen**: Spec CA#2
**Decisión**: Gauges `ready`/`failed` actualizados en startup y cada reconciliación.
**Evidencia**: `_update_storage_bridge_metrics()` + `reconcile_storage_bridge_endpoint`

### 10. Runbook en `docs/operacion/runbook.md`
**Origen**: Spec CA#5, Caso borde #3
**Decisión**: Carpeta `docs/operacion/` creada para runbook (no existía).
**Contenido**: Alertas recomendadas, procedimientos job atascado/disco lleno/engine caído/bridge failed, comandos útiles.

### 11. No OpenTelemetry en esta fase
**Origen**: Spec Riesgo #3
**Decisión**: Correlation ID manual suficiente para MVP local. OpenTelemetry en fase futura cuando haya necesidad de tracing distribuido (múltiples servicios).
**Justificación**: YAGNI. Añade complejidad y dependencias sin valor inmediato.

### 12. Nivel de log por env var
**Origen**: Spec Caso borde #6
**Decisión**: `GI_OCR_LOG_LEVEL` (default INFO). DEBUG solo bajo flag.
**Evidencia**: `configure_logging()` lee env var.

## Decisiones NO tomadas (fuera de alcance)

- Alerting externo (Alertmanager, PagerDuty, etc.) → feature futura
- Dashboards Grafana predefinidos → feature futura (docs tiene queries sugeridas)
- Trazabilidad distribuida (Jaeger, Zipkin) → feature futura
- Log shipping (Loki, Elasticsearch, Datadog) → configuración de infra, no código
- Métricas de negocio (facturación, SLA cliente) → producto, no observabilidad técnica

## Evidencia de cierre

- Spec: `runs/13-observabilidad-operacion/spec.md` ✅
- Auditoría: `runs/13-observabilidad-operacion/audit-1.md` (approved) ✅
- Implementación: 
  - `backend/app/logging_config.py` ✅
  - `backend/app/metrics.py` ✅
  - `backend/app/correlation.py` ✅
  - `backend/app/main.py` (endpoints + middleware + startup/shutdown) ✅
  - `backend/app/job_queue.py` (logging + métricas) ✅
  - `backend/app/capture_pipeline.py` (métricas campos + duración) ✅
- Doc técnica: `docs/tecnica/observabilidad-operacion.md` ✅
- Doc usuario: `docs/usuario/observabilidad-operacion.md` ✅
- Runbook: `docs/operacion/runbook.md` ✅
- Índices actualizados: `docs/tecnica/index.md`, `docs/usuario/index.md` ✅
- Tests: Pendientes (QA phase) 🔄