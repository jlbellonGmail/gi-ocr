"""Middleware de correlation ID para trazabilidad de requests."""

from __future__ import annotations

import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware que genera/propaga correlation_id en requests y responses."""

    HEADER_NAME = "X-Correlation-ID"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Obtener correlation_id del header entrante o generar uno nuevo
        correlation_id = request.headers.get(self.HEADER_NAME) or uuid.uuid4().hex

        # Añadir al estado del request para acceso en handlers
        request.state.correlation_id = correlation_id

        # Procesar request
        response = await call_next(request)

        # Añadir header de respuesta
        response.headers[self.HEADER_NAME] = correlation_id

        return response


def get_correlation_id(request: Request) -> str:
    """Obtiene correlation_id del request state."""
    return getattr(request.state, "correlation_id", "-")
