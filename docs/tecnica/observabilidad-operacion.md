# Observabilidad Operativa

Arquitectura de logs, métricas y health checks para gi-ocr.

## Logs Estructurados

### Librería: `structlog`

- **Desarrollo** (`GI_OCR_ENV=development`): pretty console con colores
- **Producción** (`GI_OCR_ENV=production`): JSON lines en stdout

### Configuración

```python
# backend/app/logging_config.py
configure_logging()  # llama una vez en startup
logger = get_logger(__name__)
```

### Campos estándar

Todos los logs incluyen:
- `timestamp`: ISO 8601 UTC
- `level`: DEBUG/INFO/WARNING/ERROR
- `logger`: nombre del logger (módulo)
- `message`: mensaje principal

Contexto de job (cuando aplica):
- `job_id`: UUID del job
- `stage`: ocr, extraction, validation, confirm, bridge, quality_gate, processing
- `duration_ms`: duración de la operación (si aplica)
- `error`: mensaje de error (si fallo)

### Ejemplos

**Job encolado:**
```json
{"timestamp":"2026-08-27T10:30:45.123Z","level":"info","logger":"job_queue","message":"job_enqueued","job_id":"abc123","source":"web"}
```

**Job completado:**
```json
{"timestamp":"2026-08-27T10:30:47.456Z","level":"info","logger":"job_queue","message":"job_completed","job_id":"abc123","stage":"processing","duration_ms":2341.5}
```

**Job fallido:**
```json
{"timestamp":"2026-08-27T10:30:47.456Z","level":"error","logger":"job_queue","message":"job_failed","job_id":"abc123","stage":"processing","error":"FileNotFoundError: Archivo no encontrado"}
```

**Campos procesados (por job):**
```json
{"timestamp":"2026-08-27T10:30:47.456Z","level":"info","logger":"capture_pipeline","message":"fields_processed","job_id":"abc123","service":"GAS","accepted":4,"rejected":1,"missing":0}
```

## Métricas Prometheus

### Endpoint: `GET /metrics`

Expone métricas en formato Prometheus text exposition.

### Jobs

| Métrica | Tipo | Labels | Descripción |
|---------|------|--------|-------------|
| `gi_ocr_jobs_total` | Counter | `status` | Total jobs por estado |
| `gi_ocr_queue_size` | Gauge | — | Jobs encolados + procesando |
| `gi_ocr_job_duration_seconds` | Histogram | `stage` | Duración por etapa |

**Estados de job:** `queued`, `processing`, `ready`, `confirmed`, `failed`, `rejected`

**Etapas:** `ocr_det`, `classify_rec`, `ocr_rec`, `total`

### Campos

| Métrica | Tipo | Labels | Descripción |
|---------|------|--------|-------------|
| `gi_ocr_fields_total` | Counter | `result`, `service` | Campos por resultado y servicio |

**Resultados:** `accepted`, `rejected`, `missing`
**Servicios:** `GAS`, `CEVT`, `UNKNOWN`

### Storage Bridge

| Métrica | Tipo | Labels | Descripción |
|---------|------|--------|-------------|
| `gi_ocr_storage_bridge_files` | Gauge | `state` | Archivos en bridge |

**Estados:** `ready`, `failed`

### OCR Engine

| Métrica | Tipo | Labels | Descripción |
|---------|------|--------|-------------|
| `gi_ocr_ocr_engine_loaded` | Gauge | — | 1=cargado, 0=no |

### Health / Readiness

| Métrica | Tipo | Labels | Descripción |
|---------|------|--------|-------------|
| `gi_ocr_health_status` | Gauge | — | 1=healthy, 0=degraded |
| `gi_ocr_readiness_status` | Gauge | — | 1=ready, 0=not ready |

### Disco

| Métrica | Tipo | Labels | Descripción |
|---------|------|--------|-------------|
| `gi_ocr_disk_usage_bytes` | Gauge | `path` | Bytes usados |

**Paths:** `storage_bridge`, `output`, `uploads`

## Health & Readiness

### `GET /api/v1/health`

Verifica que el proceso está vivo y engine OCR cargado.

**Response 200:**
```json
{
  "status": "ok",
  "engine_loaded": true,
  "queue_workers": 2,
  "inbound": {"status": "running", "path": "/path/to/inbound"}
}
```

**Response 200 (degraded):**
```json
{
  "status": "degraded",
  "engine_loaded": false,
  "queue_workers": 2,
  "inbound": {...}
}
```

### `GET /api/v1/ready`

Verifica que el sistema puede recibir tráfico.

**Checks:**
1. Engine OCR cargado
2. Espacio en disco (>100MB libre)
3. Cola no saturada (< 10 jobs/worker encolados)

**Response 200:**
```json
{
  "status": "ready",
  "engine_loaded": true,
  "disk_ok": true,
  "queue_size": 3
}
```

**Response 503:**
```json
{
  "status": "not_ready",
  "engine_loaded": true,
  "disk_ok": true,
  "queue_saturated": true,
  "queue_size": 25
}
```

## Correlation ID

### Header: `X-Correlation-ID`

- Generado automáticamente si no viene en request
- Propagado en response header
- Disponible en `request.state.correlation_id`
- Incluido en todos los logs del request

### Uso en cliente

```bash
# Enviar correlation ID propio
curl -H "X-Correlation-ID: mi-request-123" http://localhost:8000/api/v1/jobs

# Leer correlation ID de respuesta
curl -v http://localhost:8000/api/v1/health
# < X-Correlation-ID: abc123def456
```

## Decisiones de Diseño

1. **Pull vs Push**: Prometheus pull (scraping) estándar. Sin Pushgateway.
2. **Cardinalidad controlada**: Solo labels de baja cardinalidad (`service`, `stage`, `status`, `state`, `path`). `job_id` solo en logs, nunca en métricas.
3. **Sin OpenTelemetry**: Correlation ID manual suficiente para MVP local. OpenTelemetry en fase futura.
4. **Logs JSON vs texto**: JSON en prod (parseable por Loki/ELK), pretty en dev.
5. **Nivel de log**: `INFO` por defecto. `DEBUG` con `GI_OCR_LOG_LEVEL=DEBUG`.
6. **Métricas de disco**: Actualizadas en startup y cada health check. No en cada request (overhead).

## Testing

```bash
# Verificar métricas
curl http://localhost:8000/metrics | grep gi_ocr

# Health check
curl http://localhost:8000/api/v1/health

# Readiness
curl http://localhost:8000/api/v1/ready

# Logs en desarrollo (pretty)
GI_OCR_ENV=development python -m backend.app.main
```