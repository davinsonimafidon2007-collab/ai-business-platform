"""Security hardening middleware (Bloque 5).

Dos middlewares de Starlette:

- ``HTTPSRedirectMiddleware``: en ``production`` con ``HTTPS_REDIRECT=true``
  redirige HTTP→HTTPS (301) cuando ``x-forwarded-proto`` no es ``https``.
  Antes de redirigir añade ``Vary: X-Forwarded-Proto`` para que las cachés
  no mezclen respuestas HTTP/HTTPS.
- ``SecurityHeadersMiddleware``: aplica cabeceras de seguridad estándar
  (``X-Content-Type-Options``, ``X-Frame-Options``, ``Referrer-Policy``,
  ``X-XSS-Protection`` y HSTS solo en producción).
"""

from __future__ import annotations

import logging
import re
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
from starlette.types import ASGIApp

from app.core.config import settings

logger = logging.getLogger(__name__)

# Peticiones que nunca deben redirigirse (internas / de salud).
_HTTPS_SKIP_PATHS = {"/health", "/health/live", "/api/v1/health"}

# Expresión para reconstruir la URL sin query (Starlette deconstruye el query
# en request.url.query).
_HTTP_SCHEME_RE = re.compile(r"^http://", re.IGNORECASE)


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Force HTTPS in production (base-config cleartext=false del lado API).

    Solo actúa cuando ``settings.environment == "production"`` y
    ``settings.https_redirect`` es ``True``. En development/test no toca nada
    (el dev local y los tests usan http).
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.enabled = (
            settings.environment == "production" and settings.https_redirect
        )

    async def dispatch(self, request: Any, call_next: Any) -> Any:
        if not self.enabled:
            return await call_next(request)

        path = request.url.path
        if path in _HTTPS_SKIP_PATHS:
            return await call_next(request)

        xfp = request.headers.get("x-forwarded-proto", "").lower()
        if xfp == "https":
            return await call_next(request)

        url = str(request.url)
        https_url = _HTTP_SCHEME_RE.sub("https://", url, count=1)
        logger.info("https_redirect: %s -> %s", path, https_url)
        response = RedirectResponse(https_url, status_code=301)
        response.headers["Vary"] = "X-Forwarded-Proto"
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Aplica cabeceras de seguridad a todas las respuestas.

    Cabeceras:
    - ``X-Content-Type-Options: nosniff``   (evita MIME-sniffing)
    - ``X-Frame-Options: DENY``             (anti clickjacking)
    - ``Referrer-Policy: strict-origin-when-cross-origin``
    - ``X-XSS-Protection: 1; mode=block``   (defensa en profundidad legacy)
    - ``Strict-Transport-Security``         (HSTS; solo en producción)
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.enabled = settings.security_headers_enabled
        self.hsts_header = (
            "max-age=31536000; includeSubDomains"
            if settings.environment == "production"
            else None
        )

    async def dispatch(self, request: Any, call_next: Any) -> Any:
        response = await call_next(request)
        if not self.enabled:
            return response

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        if self.hsts_header:
            response.headers["Strict-Transport-Security"] = self.hsts_header
        return response