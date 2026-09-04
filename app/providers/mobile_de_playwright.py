"""Provider mobile.de con browser automation opcional (Playwright u OpenClaw).

No requiere cuenta externa. Usa la abstracción ``BrowserAutomation``
(``app/providers/browser_automation.py``) para renderizar la página con un
navegador real cuando está habilitado (Playwright local u OpenClaw como
agente externo — ver ``get_browser_automation``). Si el backend elegido no
está disponible o falla, hace fallback silencioso al ``ProviderHttpClient``
(httpx) del ``MobileDeProvider`` padre.

Ventajas vs httpx puro:
  - Ejecuta JS, resuelve Cloudflare/challenge estático simple y cookies
  - Renderiza DOM final (selectores más estables)
  - Reusa proxy / User-Agent del ``ProviderHttpClient`` si hay proxy

Diseño: no rompe contratos. Hereda toda la lógica de parsing de
``MobileDeProvider`` (``_find_listing_nodes``, ``_extract_*``). Solo
sobrescribe ``_download_url`` para delegar en ``BrowserAutomation`` cuando
está habilitado. Esta clase NO conoce Playwright ni OpenClaw directamente
— eso vive en ``browser_automation.py``, así ambos backends son
intercambiables sin tocar lógica de mobile.de (BROWSER.1).
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings
from app.providers.browser_automation import get_browser_automation
from app.providers.exceptions import ProviderUnavailableError
from app.providers.mobile_de import MobileDeProvider

logger = logging.getLogger(__name__)

_LISTING_WAIT_SELECTOR = "article, [data-listing-id], .result-item"


class MobileDePlaywrightProvider(MobileDeProvider):
    """Mobile.de con transporte de browser automation opcional."""

    def __init__(self, http_client: Any = None, base_url: str | None = None, **kwargs: Any) -> None:
        # base_url por defecto suchen.mobile.de (igual que MobileDeProvider DI)
        from app.providers.mobile_de import BASE_URL

        super().__init__(http_client=http_client, base_url=base_url or BASE_URL)

    async def _download_url(self, url: str) -> str:
        user_agent: str | None = None
        try:
            if self._http_client is not None and hasattr(self._http_client, "_get_random_user_agent"):
                user_agent = self._http_client._get_random_user_agent()  # type: ignore
        except Exception:
            user_agent = None

        browser = get_browser_automation(settings, user_agent=user_agent)
        if browser is None:
            # Ni OpenClaw ni Playwright habilitados/configurados → httpx.
            return await super()._download_url(url)

        logger.info("mobile_de_browser: navegando %s vía %s", url, type(browser).__name__)
        try:
            content = await browser.fetch(url, wait_selector=_LISTING_WAIT_SELECTOR)
            # Reusar detección anti-bot del padre
            self._raise_if_blocked(content, url)
            return content
        except ProviderUnavailableError as exc:
            logger.warning(
                "mobile_de_browser: backend no disponible (%s), fallback httpx: %s",
                type(browser).__name__,
                exc,
            )
            return await super()._download_url(url)
        except Exception as exc:  # noqa: BLE001 — cualquier fallo de browser → fallback
            # No enmascarar ProviderConnectionError anti-bot: ya se lanzó arriba
            # (_raise_if_blocked se propaga tal cual, no entra en este except
            # porque la excepción real es ProviderConnectionError, distinta
            # de los fallos de navegación que sí queremos absorber aquí).
            from app.providers.exceptions import ProviderConnectionError

            if isinstance(exc, ProviderConnectionError):
                raise
            logger.warning(
                "mobile_de_browser: fallo navegación (%s), fallback httpx: %s",
                type(exc).__name__,
                exc,
            )
            try:
                return await super()._download_url(url)
            except Exception as fallback_exc:
                logger.error("mobile_de_browser: fallback httpx también falló: %s", fallback_exc)
                raise fallback_exc from exc
