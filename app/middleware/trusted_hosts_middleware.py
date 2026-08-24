from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings

logger = logging.getLogger(__name__)


class TrustedHostsMiddleware(BaseHTTPMiddleware):
    """Rechaza peticiones con Host no confiable en producción (TRUSTED_HOSTS)."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.enabled = settings.environment == "production" and bool(settings.trusted_hosts)

    async def dispatch(self, request, call_next):
        if not self.enabled:
            return await call_next(request)
        host = request.headers.get("host", "").split(":")[0]
        trusted = [h.split(":")[0] for h in settings.trusted_hosts]
        if host and host not in trusted:
            logger.warning("TrustedHosts: blocked host=%s", host)
            from starlette.responses import JSONResponse
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid host header"},
            )
        return await call_next(request)
