# Observabilidad Operativa — Guía de Usuario

## Propósito

Esta guía explica cómo monitorear y operar gi-ocr usando logs estructurados, métricas Prometheus y health checks.

## Endpoints de Observabilidad

### Health Check

```
GET /api/v1/health
```

Verifica que el servicio está vivo y el motor OCR cargado.

**Ejemplo:**
```bash
curl http://localhost:8000/api/v1/health
```

**Respuesta exitosa:**
```json
{
  "status": "ok",
  "engine_loaded": true,
  "queue_workers": 2,
  "inbound": {"status": "running", "path": "/app/inbound"}
}
```

**Respuesta degradada (engine OCR no cargado):**
```json
{
  "status": "degraded",
  "engine_loaded": false,
  "queue_workers": 2,
  "inbound": {...}
}
```

### Readiness Check

```
GET /api/v1/ready
```

Verifica que el sistema puede recibir tráfico (útil para load balancers / Kubernetes).

**Checks realizados:**
1. Motor OCR cargado
2. Espacio en disco (>100MB libre)
3. Cola no saturada (< 10 jobs por worker)

**Ejemplo:**
```bash
curl http://localhost:8000/api/v1/ready
```

**Respuesta lista (200):**
```json
{
  "status": "ready",
  "engine_loaded": true,
  "disk_ok": true,
  "queue_size": 3
}
```

**Respuesta no lista (503):**
```json
{
  "status": "not_ready",
  "engine_loaded": true,
  "disk_ok": true,
  "queue_saturated": true,
  "queue_size": 25
}
```

### Métricas Prometheus

```
GET /metrics
```

Expone métricas en formato Prometheus para scraping.

**Ejemplo:**
```bash
curl http://localhost:8000/metrics
```

**Métricas clave:**

| Métrica | Descripción |
|---------|-------------|
| `gi_ocr_jobs_total{status="ready"}` | Jobs completados exitosamente |
| `gi_ocr_jobs_total{status="failed"}` | Jobs fallidos |
| `gi_ocr_job_duration_seconds_bucket{stage="total",le="5.0"}` | Latencia p50/p95/p99 |
| `gi_ocr_fields_total{result="accepted",service="GAS"}` | Campos extraídos correctamente |
| `gi_ocr_fields_total{result="rejected",service="GAS"}` | Campos rechazados por validación |
| `gi_ocr_fields_total{result="missing",service="GAS"}` | Campos no encontrados |
| `gi_ocr_queue_size` | Jobs esperando en cola |
| `gi_ocr_storage_bridge_files{state="ready"}` | Archivos .DATA listos para legacy |
| `gi_ocr_ocr_engine_loaded` | 1 si engine OCR cargado |
| `gi_ocr_readiness_status` | 1=listo para tráfico |

### Correlation ID

Todos los requests incluyen `X-Correlation-ID` en respuesta. Útil para trazar requests en logs.

```bash
# Enviar tu propio ID
curl -H "X-Correlation-ID: mi-trace-123" http://localhost:8000/api/v1/health

# Leer ID de respuesta
curl -v http://localhost:8000/api/v1/health 2>&1 | grep -i correlation
```

## Interpretación de Métricas

### Alertas Recomendadas

| Métrica | Umbral Warning | Umbral Crítico | Acción |
|---------|----------------|----------------|--------|
| `gi_ocr_jobs_total{status="failed"}` | > 5/min | > 20/min | Revisar logs de jobs fallidos |
| `gi_ocr_job_duration_seconds{stage="total",quantile="0.95"}` | > 10s | > 30s | Revisar performance OCR |
| `gi_ocr_queue_size` | > 20 | > 50 | Escalar workers o revisar jobs atascados |
| `gi_ocr_storage_bridge_files{state="failed"}` | > 0 | > 5 | Revisar `storage_bridge/failed/` |
| `gi_ocr_disk_usage_bytes{path="output"}` | > 80% disco | > 90% disco | Limpiar uploads antiguos / expandir disco |
| `gi_ocr_readiness_status` | 0 | 0 | Sistema no recibe tráfico |

### Consultas Prometheus Útiles

**Tasa de éxito de jobs (últimos 5 min):**
```promql
rate(gi_ocr_jobs_total{status="ready"}[5m]) / rate(gi_ocr_jobs_total[5m])
```

**Latencia p95 de procesamiento total:**
```promql
histogram_quantile(0.95, rate(gi_ocr_job_duration_seconds_bucket{stage="total"}[5m]))
```

**Tasa de campos rechazados por servicio:**
```promql
rate(gi_ocr_fields_total{result="rejected"}[5m]) by (service)
```

**Jobs en cola por worker:**
```promql
gi_ocr_queue_size / 2  # asumiendo 2 workers
```

## Logs Estructurados

### Formato

**Producción (JSON):**
```json
{"timestamp":"2026-08-27T10:30:45.123Z","level":"info","logger":"job_queue","message":"job_completed","job_id":"abc123def456","stage":"processing","duration_ms":2341.5}
```

**Desarrollo (Pretty):**
```
10:30:45 [info     ] job_queue        job_completed                    job_id=abc123def456 stage=processing duration_ms=2341.5
```

### Filtrado por Job

```bash
# Buscar todos los logs de un job específico
grep "abc123def456" /var/log/gi-ocr/app.log | jq .

# Solo errores de un job
grep "abc123def456" /var/log/gi-ocr/app.log | jq 'select(.level=="error")'
```

### Campos Clave en Logs

| Campo | Descripción |
|-------|-------------|
| `job_id` | UUID del job (correlaciona con API) |
| `stage` | Etapa: ocr, extraction, validation, confirm, bridge, quality_gate, processing |
| `duration_ms` | Duración en milisegundos |
| `service` | GAS, CEVT, UNKNOWN |
| `accepted` / `rejected` / `missing` | Conteos de campos |

## Runbook Operativo

### Job Atascado en "processing"

1. Verificar `gi_ocr_job_duration_seconds` - si > 60s, posible hang
2. Revisar logs del job: `grep <job_id> app.log`
3. Reintentar: `POST /api/v1/jobs/{job_id}/retry`
4. Si persiste: reiniciar servicio (reinicia cola)

### Disco Lleno

1. Alerta: `gi_ocr_disk_usage_bytes > 90%`
2. Limpiar uploads antiguos: `find output/uploads -mtime +7 -delete`
3. Limpiar jobs antiguos confirmados: `find output/confirmed -mtime +30 -delete`
4. Verificar `storage_bridge/failed/` no crece indefinidamente

### Engine OCR No Carga

1. `/health` muestra `engine_loaded: false`
2. Verificar logs: `grep "ocr_engine" app.log`
3. Causas comunes: modelos ONNX faltantes, memoria insuficiente, versión Python incompatible
4. Reiniciar servicio tras corregir

### Archivos en `storage_bridge/failed/`

1. Revisar archivos `_error.json` para causa
2. Causas típicas: permisos, disco lleno, colisión nombre
3. Re-procesar jobs origen si aplica

### Reconciliación Bridge

```bash
# Ejecutar reconciliación manual
curl -X POST http://localhost:8000/api/v1/admin/reconcile \
  -H "Authorization: Bearer <admin_token>"

# Revisar reporte generado en output/reconciliation/
cat output/reconciliation/reconciliation_*.json
```

## Configuración de Entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `GI_OCR_ENV` | `development` | `development` o `production` (afecta formato logs) |
| `GI_OCR_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `GI_OCR_MAX_UPLOAD_BYTES` | `31457280` | Tamaño máximo upload (30MB) |

## Ejemplo: Dashboard Básico (Grafana)

Paneles sugeridos:
1. **Stat**: `gi_ocr_jobs_total{status="ready"}` (total hoy)
2. **Stat**: `gi_ocr_jobs_total{status="failed"}` (total hoy)
3. **Graph**: `rate(gi_ocr_jobs_total[5m])` by status
4. **Graph**: `histogram_quantile(0.95, rate(gi_ocr_job_duration_seconds_bucket{stage="total"}[5m]))`
5. **Graph**: `gi_ocr_queue_size`
6. **Table**: `gi_ocr_fields_total` by service, result
7. **Stat**: `gi_ocr_readiness_status` (verde/rojo)