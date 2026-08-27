"""Configuración de logging estructurado para gi-ocr.

Usa structlog para logs JSON en producción, pretty console en desarrollo.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Callable

import structlog


def _is_dev() -> bool:
    return os.getenv("GI_OCR_ENV", "development").lower() == "development"


def _json_renderer() -> Callable:
    return structlog.processors.JSONRenderer()


def _console_renderer() -> Callable:
    return structlog.dev.ConsoleRenderer(colors=True)


def configure_logging() -> None:
    """Configura structlog globalmente.

    Debe llamarse una sola vez al inicio de la aplicación (en main.py startup).
    """
    log_level = os.getenv("GI_OCR_LOG_LEVEL", "INFO").upper()

    # Configurar stdlib logging
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    if _is_dev():
        handler.setFormatter(logging.Formatter("%(message)s"))
        renderer = _console_renderer()
    else:
        handler.setFormatter(logging.Formatter("%(message)s"))
        renderer = _json_renderer()

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level)

    # Configurar structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Obtiene un logger estructurado para el módulo dado."""
    return structlog.get_logger(name)


def bind_job_context(
    logger: structlog.BoundLogger,
    job_id: str,
    stage: str | None = None,
    **kwargs: Any,
) -> structlog.BoundLogger:
    """Añade contexto de job al logger."""
    ctx = {"job_id": job_id}
    if stage:
        ctx["stage"] = stage
    ctx.update(kwargs)
    return logger.bind(**ctx)


def log_job_event(
    logger: structlog.BoundLogger,
    event: str,
    job_id: str,
    stage: str,
    duration_ms: float | None = None,
    **kwargs: Any,
) -> None:
    """Log estandarizado de evento de job."""
    log = bind_job_context(logger, job_id, stage, **kwargs)
    if duration_ms is not None:
        log.info(event, duration_ms=round(duration_ms, 2))
    else:
        log.info(event)
