"""Métricas Prometheus para gi-ocr.

Expone contadores, histogramas y gauges para observabilidad operativa.
"""

from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

# ============================================================
# Jobs
# ============================================================

JOBS_TOTAL = Counter(
    "gi_ocr_jobs_total",
    "Total number of jobs by status",
    ["status"],  # queued, processing, ready, confirmed, failed, rejected
)

QUEUE_SIZE = Gauge(
    "gi_ocr_queue_size",
    "Current number of jobs in queue (queued + processing)",
)

# ============================================================
# Job Duration (histograms with quantiles)
# ============================================================

JOB_DURATION_SECONDS = Histogram(
    "gi_ocr_job_duration_seconds",
    "Job processing duration by stage",
    ["stage"],  # ocr_det, classify_rec, ocr_rec, total
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

# ============================================================
# Fields
# ============================================================

FIELDS_TOTAL = Counter(
    "gi_ocr_fields_total",
    "Total fields processed by result and service",
    ["result", "service"],  # result: accepted, rejected, missing; service: GAS, CEVT, UNKNOWN
)

# ============================================================
# Storage Bridge
# ============================================================

STORAGE_BRIDGE_FILES = Gauge(
    "gi_ocr_storage_bridge_files",
    "Number of files in storage bridge by state",
    ["state"],  # ready, failed
)

# ============================================================
# OCR Engine
# ============================================================

OCR_ENGINE_LOADED = Gauge(
    "gi_ocr_ocr_engine_loaded",
    "Whether OCR engine is loaded (1) or not (0)",
)

# ============================================================
# Disk Usage
# ============================================================

DISK_USAGE_BYTES = Gauge(
    "gi_ocr_disk_usage_bytes",
    "Disk usage in bytes for key paths",
    ["path"],  # storage_bridge, output, uploads
)

# ============================================================
# Health / Readiness
# ============================================================

HEALTH_STATUS = Gauge(
    "gi_ocr_health_status",
    "Health status: 1=healthy, 0=degraded, -1=down",
)

READINESS_STATUS = Gauge(
    "gi_ocr_readiness_status",
    "Readiness status: 1=ready, 0=not ready",
)


def observe_job_duration(stage: str, duration_seconds: float) -> None:
    """Registra duración de una etapa del job."""
    JOB_DURATION_SECONDS.labels(stage=stage).observe(duration_seconds)


def inc_jobs_total(status: str) -> None:
    """Incrementa contador de jobs por estado."""
    JOBS_TOTAL.labels(status=status).inc()


def set_queue_size(size: int) -> None:
    """Actualiza tamaño de cola."""
    QUEUE_SIZE.set(size)


def inc_fields_total(result: str, service: str) -> None:
    """Incrementa contador de campos por resultado y servicio."""
    FIELDS_TOTAL.labels(result=result, service=service).inc()


def set_storage_bridge_files(state: str, count: int) -> None:
    """Actualiza contador de archivos en storage bridge."""
    STORAGE_BRIDGE_FILES.labels(state=state).set(count)


def set_ocr_engine_loaded(loaded: bool) -> None:
    """Actualiza estado del engine OCR."""
    OCR_ENGINE_LOADED.set(1 if loaded else 0)


def set_disk_usage(path: str, bytes_used: int) -> None:
    """Actualiza uso de disco para una ruta."""
    DISK_USAGE_BYTES.labels(path=path).set(bytes_used)


def set_health_status(healthy: bool) -> None:
    """Actualiza estado de salud: 1=healthy, 0=degraded."""
    HEALTH_STATUS.set(1 if healthy else 0)


def set_readiness_status(ready: bool) -> None:
    """Actualiza estado de readiness: 1=ready, 0=not ready."""
    READINESS_STATUS.set(1 if ready else 0)


def metrics_response() -> tuple[bytes, str]:
    """Genera respuesta de métricas para endpoint /metrics."""
    return generate_latest(), CONTENT_TYPE_LATEST
