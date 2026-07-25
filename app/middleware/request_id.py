from __future__ import annotations

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware que genera un request_id único por petición y registra métricas."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generar o recuperar request_id
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        # Añadir request_id al contexto de logging
        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
            },
        )

        start_time = time.time()

        try:
            response = await call_next(request)

            # Calcular tiempo de ejecución
            process_time = time.time() - start_time
            response.headers["X-Request-ID"] = request_id

            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time_ms": round(process_time * 1000, 2),
                },
            )

            return response

        except Exception as exc:
            # Log de error no controlado
            process_time = time.time() - start_time
            logger.error(
                "Request failed with unhandled exception",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "process_time_ms": round(process_time * 1000, 2),
                },
            )

            # Re-lanzar para que el exception handler lo maneje
            raise