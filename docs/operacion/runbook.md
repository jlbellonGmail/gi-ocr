# Runbook Operativo: gi-ocr

Guía de procedimientos para operación diaria y resolución de incidentes.

## Métricas Clave y Alertas

### Dashboard Básico (Grafana/Prometheus)

| Panel | Query | Alerta Warning | Alerta Crítica |
|-------|-------|----------------|----------------|
| Jobs exitosados/min | `rate(gi_ocr_jobs_total{status="ready"}[5m])` | < 1 | = 0 por 10min |
| Jobs fallidos/min | `rate(gi_ocr_jobs_total{status="failed"}[5m])` | > 1 | > 5 |
| Latencia p95 total | `histogram_quantile(0.95, rate(gi_ocr_job_duration_seconds_bucket{stage="total"}[5m]))` | > 10s | > 30s |
| Cola size | `gi_ocr_queue_size` | > 20 | > 50 |
| Readiness | `gi_ocr_readiness_status` | 0 | 0 |
| Disco output | `gi_ocr_disk_usage_bytes{path="output"} / gi_ocr_disk_usage_bytes{path="output"} + gi_ocr_disk_usage_bytes{path="output"}` | > 80% | > 90% |

## Procedimientos

### 1. Job Atascado en "processing"

**Síntomas:**
- Job en estado `processing` > 60s
- `gi_ocr_job_duration_seconds` creciendo sin bound
- Logs muestran `job_processing_started` pero no `job_completed`/`job_failed`

**Pasos:**
```bash
# 1. Identificar job_id
grep "job_processing_started" /var/log/gi-ocr/app.log | tail -5

# 2. Ver logs completos del job
grep "<job_id>" /var/log/gi-ocr/app.log | jq .

# 3. Reintentar (si no es hang permanente)
curl -X POST http://localhost:8000/api/v1/jobs/<job_id>/retry \
  -H "Authorization: Bearer <token>" \
  -H "X-Operator-Id: admin" \
  -H "X-Operator-Role: admin"

# 4. Si persiste tras 2 reintentos → reiniciar servicio
sudo systemctl restart gi-ocr
```

**Causas comunes:**
- Archivo corrupto / formato no soportado
- Memoria insuficiente (OOM kill silencioso)
- Engine OCR hang (modelo ONNX corrupto)

### 2. Disco Lleno / Espacio Bajo

**Alerta:** `gi_ocr_disk_usage_bytes > 80%` (warning), `> 90%` (crítico)

**Pasos:**
```bash
# 1. Ver uso actual
df -h /app/output

# 2. Limpiar uploads antiguos (>7 días)
find /app/output/uploads -type f -mtime +7 -delete

# 3. Limpiar jobs confirmados antiguos (>30 días)
find /app/output/confirmed -type f -mtime +30 -delete

# 4. Limpiar originales de jobs confirmados (>30 días)
find /app/output/jobs -type f -mtime +30 -delete

# 5. Verificar storage_bridge/failed no crece
ls -la /app/storage_bridge/failed/
# Si hay muchos *_error.json antiguos → limpiar
find /app/storage_bridge/failed -name "*_error.json" -mtime +7 -delete

# 6. Verificar que no hay jobs "zombie" en processing
curl http://localhost:8000/api/v1/jobs | jq '.jobs[] | select(.status=="processing")'
```

### 3. Engine OCR No Carga

**Síntomas:**
- `/health` → `"engine_loaded": false`
- `/ready` → 503 con `"engine_loaded": false`
- Logs: `ocr_engine_warmed_up` no aparece, o error en `warmup()`

**Pasos:**
```bash
# 1. Ver logs de arranque
grep -E "ocr_engine|warmup|ONNX|RapidOCR" /var/log/gi-ocr/app.log | tail -20

# 2. Verificar modelos ONNX existen
ls -la /app/.cache/rapidocr/  # o ruta configurada

# 3. Verificar memoria disponible
free -h

# 3. Verificar versión Python compatible (3.12+)
python --version

# 4. Reinstalar dependencias si modelos corruptos
pip install --force-reinstall rapidocr-onnxruntime onnxruntime

# 5. Reiniciar servicio
sudo systemctl restart gi-ocr
```

### 4. Archivos en `storage_bridge/failed/`

**Síntomas:**
- `gi_ocr_storage_bridge_files{state="failed"}` > 0
- Archivos `*_error.json` en `storage_bridge/failed/`

**Pasos:**
```bash
# 1. Inspeccionar errores
cat /app/storage_bridge/failed/*_error.json | jq .

# 2. Causas típicas:
# - "Permission denied" → permisos carpeta ready/
# - "No space left on device" → disco lleno (ver procedimiento 2)
# - "File exists" → colisión nombre (reintento automático debería manejar)

# 3. Si error transitorio → re-procesar job origen
# Buscar job_id en logs por timestamp del error
grep "<timestamp_del_error>" /var/log/gi-ocr/app.log | grep job_id

# 4. Reintentar job
curl -X POST http://localhost:8000/api/v1/jobs/<job_id>/retry ...
```

### 5. Cola Saturada / Jobs No Procesan

**Síntomas:**
- `gi_ocr_queue_size` creciendo
- `/ready` → 503 `"queue_saturated": true`
- Jobs en `queued` mucho tiempo

**Pasos:**
```bash
# 1. Ver estado cola
curl http://localhost:8000/api/v1/jobs | jq '.jobs[] | {job_id, status, created_at}'

# 2. Verificar workers vivos
grep "job_queue_started" /var/log/gi-ocr/app.log | tail -1

# 3. Si workers muertos → reiniciar servicio
sudo systemctl restart gi-ocr

# 4. Si workers vivos pero lentos → ver latencia p95
# histogram_quantile(0.95, rate(gi_ocr_job_duration_seconds_bucket{stage="total"}[5m]))

# 5. Escalar workers temporalmente (requires restart con config)
# Editar backend/app/main.py: JobQueue(store, workers=4)
```

### 6. Reconciliación Bridge Manual

**Cuándo:** Alerta `gi_ocr_storage_bridge_files` inconsistente, o auditoría periódica.

```bash
# Ejecutar reconciliación (requiere ADMIN)
curl -X POST http://localhost:8000/api/v1/admin/reconcile \
  -H "Authorization: Bearer <admin_token>" \
  -H "X-Operator-Id: admin" \
  -H "X-Operator-Role: admin"

# Revisar reporte
cat /app/output/reconciliation/reconciliation_*.json | jq .

# Interpretación:
# - missing_in_ready: Jobs confirmados sin .DATA en ready/ → re-procesar/confirmar
# - orphan_in_ready: .DATA sin job confirmado → limpiar o investigar
# - content_mismatch: Mismo job, contenido distinto → posible race condition
```

## Comandos Útiles

```bash
# Ver logs en vivo (pretty)
tail -f /var/log/gi-ocr/app.log | jq .

# Filtrar por job_id
grep "abc123def456" /var/log/gi-ocr/app.log | jq .

# Solo errores
grep '"level":"error"' /var/log/gi-ocr/app.log | jq .

# Métricas rápidas
curl -s http://localhost:8000/metrics | grep gi_ocr_jobs_total
curl -s http://localhost:8000/metrics | grep gi_ocr_queue_size
curl -s http://localhost:8000/metrics | grep gi_ocr_readiness_status

# Health/Readiness
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/ready

# Ver jobs en cola
curl http://localhost:8000/api/v1/jobs | jq '.jobs[] | select(.status=="queued" or .status=="processing")'

# Reintentar job
curl -X POST http://localhost:8000/api/v1/jobs/<job_id>/retry \
  -H "Authorization: Bearer <token>" \
  -H "X-Operator-Id: admin" -H "X-Operator-Role: admin"
```

## Escalamiento

| Nivel | Condición | Acción |
|-------|-----------|--------|
| 1 | Warning alerta | Revisar en < 30 min, aplicar procedimiento |
| 2 | Crítico activo > 15 min | Reiniciar servicio, notificar equipo |
| 3 | Servicio caído / data loss risk | Escalar a on-call, restaurar backup si aplica |

## Contactos

- **On-call**: Ver rota en wiki/ops
- **Repositorio**: https://github.com/jlbellonGmail/gi-ocr
- **Issues**: GitHub Issues para bugs/features