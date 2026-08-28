status: approved
attempt: 1
feedback: []

# Auditoría: 13-observabilidad-operacion (spec.md)

## Veredicto: APPROVED

El spec cumple con todos los requisitos del circuito y las reglas de dominio OCR.

## Análisis por criterio

### 1. Criterios de documentación obligatorios (AGENTS.md) ✅
- **docs/tecnica/observabilidad-operacion.md**: Exigido explícitamente en CA #6
- **docs/usuario/observabilidad-operacion.md**: Exigido explícitamente en CA #7
- **runs/13-observabilidad-operacion/decision.md**: Exigido explícitamente en CA #8
- **Enlaces en índices**: Exigido explícitamente en CA #9

### 2. Criterios de aceptación concretos y verificables ✅
Cada CA es testeable:
- CA #1: Logs estructurados JSON → test que verifica formato de log output
- CA #2: `/metrics` con métricas específicas → test que scrapea endpoint y valida métricas presentes
- CA #3: `/health` y `/ready` con checks reales → test que verifica códigos de respuesta y payloads
- CA #4: Correlation ID propagado → test de integración que traza job end-to-end
- CA #5: Runbook → verificación existencia archivo
- CA #6-9: Documentación → verificación existencia y enlaces

### 3. Reglas de dominio OCR (AGENTS.md) ✅
- No altera pipeline OCR/extracción/validación/storage
- No cambia motor OCR ni formato `.DATA`/`services.ini`
- Respeta separación de responsabilidades

### 4. Arquitectura y ADRs ✅
- ADR-001 (filesystem bridge): métricas de bridge añadidas
- ADR-002 (FastAPI): endpoints nuevos en mismo framework
- ADR-009 (Docker): métricas expuestas en puerto 8000, compatible
- No introduce dependencias pesadas (solo `prometheus-client`, `structlog`)

### 5. Casos borde cubiertos ✅
- Job legacy sin correlation_id
- Cardinalidad controlada (service, stage, status como labels; job_id solo en logs)
- Disco lleno no bloquea procesamiento
- Engine OCR no cargado → 503 en `/ready`
- Cola saturada → 503 en `/ready`
- Dev vs prod logging

### 6. Riesgos/supuestos explícitos ✅
- Pull vs push métricas (Pull - Prometheus estándar)
- Librerías estándar (`prometheus-client`, `structlog`)
- Sin OpenTelemetry (fase futura)
- Cardinalidad controlada
- Verbosidad logs controlada por nivel

### 7. Alcance acotado ✅
No incluye: alerting externo, dashboards Grafana, tracing distribuido. Todos explícitamente fuera de alcance.

## Observaciones menores (no bloqueantes)

1. **CA #2 métricas**: El histogram `gi_ocr_job_duration_seconds` con quantiles requiere `prometheus-client` histogram buckets configurados. Builder debe definir buckets apropiados (ej. [0.1, 0.5, 1, 2, 5, 10, 30] segundos).

2. **Correlation ID en `.DATA`**: El spec dice "en confirmation_metadata". El `.DATA` v2 no tiene campo para eso; iría en `.CONFIDENCE.json` o JSON confirmado. Builder documenta decisión en `decision.md`.

3. **Runbook ubicación**: `docs/operacion/runbook.md` - carpeta `docs/operacion/` no existe hoy. Builder debe crearla.

## Conclusión

Spec aprobado. Listo para builder-agent.