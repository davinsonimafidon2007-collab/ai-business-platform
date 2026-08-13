"""Structured access logging middleware.

Logs every request in a consistent JSON format with:

  - timestamp
  - method
  - path
  - status_code
  - duration_ms
  - ip
  - user_agent
  - request_id
  - correlation_id

All controlled via Settings (LOG_LEVEL, ENABLE_ACCESS_LOG, etc.).
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.middleware.request_id import get_request_id_from_state
from app.utils.correlation import get_correlation_id

logger = logging.getLogger("app.access")


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Middleware that logs structured access logs for every request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not settings.enable_access_log:
            return await call_next(request)

        start_time = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            # Re-raise after logging; exception handler will produce final response
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            self._log(request=request, status_code=500, duration_ms=duration_ms)
            raise

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        self._log(request=request, status_code=response.status_code, duration_ms=duration_ms)

        return response

    def _log(self, request: Request, status_code: int, duration_ms: float) -> None:
        """Emit a structured access log entry."""
        request_id = get_request_id_from_state(request)
        correlation_id = get_correlation_id()

        log_data: dict = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            "request_id": request_id or "",
            "correlation_id": correlation_id or "",
            "method": request.method,
            "path": request.url.path,
            "query": str(request.url.query) if request.url.query else "",
            "status": status_code,
            "duration_ms": duration_ms,
            "ip": request.client.host if request.client else "",
            "user_agent": request.headers.get("user-agent", ""),
        }

        # Add database pool metrics logging if available (TASK-011)
        try:
            from app.database import db_manager
            log_data["db_pool"] = db_manager.get_pool_metrics()
        except Exception:
            pass

        if settings.log_json:
            logger.info(json.dumps(log_data, ensure_ascii=False))
        else:
            db_pool = log_data.get("db_pool", {})
            pool_info = f" (db_pool size={db_pool.get('size', 0)} checkedout={db_pool.get('checkedout', 0)})" if db_pool else ""
            logger.info(
                "%s %s %d %.2fms [%s]%s",
                log_data["method"],
                log_data["path"],
                log_data["status"],
                log_data["duration_ms"],
                log_data["request_id"],
                pool_info,
            )

