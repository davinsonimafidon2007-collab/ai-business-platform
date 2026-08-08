from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.correlation import generate_correlation_id, set_correlation_id

logger = logging.getLogger(__name__)


def get_request_id_from_state(request: Request) -> str | None:
    """Obtiene el request_id desde el estado de la request.

    Esta función es utilizada por exception_handlers.py y logging_middleware.py
    para acceder al request_id sin acoplamiento directo.
    """
    return getattr(request.state, "request_id", None)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware que gestiona Request ID y Correlation ID.

    - Request ID: UUID único por petición. Si el cliente envía X-Request-ID,
      se utiliza ese; si no, se genera automáticamente.
    - Correlation ID: UUID que se propaga entre servicios internos.
      Si el cliente envía X-Correlation-ID, se utiliza ese; si no,
      se genera automáticamente.

    Ambos IDs se almacenan en request.state y están disponibles durante
    toda la petición via get_request_id_from_state() y app.utils.correlation.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # --- Request ID ---
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        # --- Correlation ID ---
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = generate_correlation_id()
        request.state.correlation_id = correlation_id
        set_correlation_id(correlation_id)

        # Log de inicio de petición
        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
            },
        )

        start_time = time.time()

        try:
            response = await call_next(request)

            process_time = time.time() - start_time
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Correlation-ID"] = correlation_id

            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(process_time * 1000, 2),
                },
            )

            return response

        except Exception:
            process_time = time.time() - start_time
            logger.error(
                "Request failed with unhandled exception",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(process_time * 1000, 2),
                },
            )
            # Re-lanzar para que los exception handlers lo manejen
            raise

