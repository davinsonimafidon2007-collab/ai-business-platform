"""Provider mobile.de con Playwright (browser headless).

No requiere cuenta externa. Usa ``playwright.async_api`` si está instalado
y ``enable_mobile_de_playwright=true``. Si Playwright no está disponible
o falla, hace fallback silencioso al ``ProviderHttpClient`` (httpx) del
``MobileDeProvider`` padre.

Ventajas vs httpx puro:
  - Ejecuta JS, resuelve Cloudflare/challenge estático simple y cookies
  - Renderiza DOM final (selectores más estables)
  - Reusa proxy / User-Agent del ``ProviderHttpClient`` si hay proxy

Diseño: no rompe contratos. Hereda toda la lógica de parsing de
``MobileDeProvider`` (``_find_listing_nodes``, ``_extract_*``). Solo
sobrescribe ``_download_url`` para usar browser cuando está habilitado.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings
from app.providers.mobile_de import MobileDeProvider

logger = logging.getLogger(__name__)


class MobileDePlaywrightProvider(MobileDeProvider):
    """Mobile.de con transporte Playwright opcional."""

    def __init__(self, http_client: Any = None, base_url: str | None = None, **kwargs: Any) -> None:
        # base_url por defecto suchen.mobile.de (igual que MobileDeProvider DI)
        from app.providers.mobile_de import BASE_URL

        super().__init__(http_client=http_client, base_url=base_url or BASE_URL)

    async def _download_url(self, url: str) -> str:
        # Si Playwright no está habilitado o no instalado → fallback httpx
        if not getattr(settings, "enable_mobile_de_playwright", False):
            return await super()._download_url(url)

        try:
            from playwright.async_api import async_playwright  # type: ignore
        except ImportError:
            logger.warning("mobile_de_playwright: playwright no instalado, fallback a httpx (url=%s)", url)
            return await super()._download_url(url)

        # Config browser headless
        timeout = int(getattr(settings, "playwright_timeout_ms", 30000) or 30000)
        headless = bool(getattr(settings, "playwright_headless", True))
        proxy = (getattr(settings, "provider_http_proxy", "") or "").strip() or None
        # Playwright proxy espera dict {"server": "http://..."}
        pw_proxy = {"server": proxy} if proxy else None

        # User-Agent realista: reusar el del http_client si existe, sino default
        user_agent: str | None = None
        try:
            if self._http_client is not None and hasattr(self._http_client, "_get_random_user_agent"):
                user_agent = self._http_client._get_random_user_agent()  # type: ignore
        except Exception:
            user_agent = None

        logger.info("mobile_de_playwright: navegando %s (headless=%s, proxy=%s)", url, headless, bool(proxy))
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=headless, proxy=pw_proxy)  # type: ignore[arg-type]
                context_kwargs: dict[str, Any] = {
                    "user_agent": user_agent,
                    "locale": "de-DE",
                    "extra_http_headers": {
                        "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8",
                    },
                }
                # Cookies manuales si PROVIDER_HTTP_COOKIES está seteada (se inyectan como header)
                cookies_raw = (getattr(settings, "provider_http_cookies", "") or "").strip()
                if cookies_raw:
                    context_kwargs["extra_http_headers"]["Cookie"] = cookies_raw

                context = await browser.new_context(**context_kwargs)
                page = await context.new_page()
                # Bloquear recursos pesados para acelerar (imágenes/media opcionales)
                # No bloqueamos por defecto para no romper render, solo timeout.

                await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                # Esperar a que aparezca algún listado o al menos body
                try:
                    await page.wait_for_selector("article, [data-listing-id], .result-item", timeout=5000)
                except Exception:
                    # No es fatal: la página puede estar vacía o bloqueada
                    pass

                # Pequeña espera para JS que hidrata listados
                await page.wait_for_timeout(800)

                content = await page.content()
                await context.close()
                await browser.close()

                # Reusar detección anti-bot del padre
                self._raise_if_blocked(content, url)
                return content

        except Exception as exc:  # noqa: BLE001 — cualquier fallo de browser → fallback
            logger.warning("mobile_de_playwright: fallo browser (%s), fallback httpx: %s", type(exc).__name__, exc)
            # No enmascarar ProviderConnectionError anti-bot: ya se lanzó arriba
            # Para otros errores (timeout, crash), intentar httpx como último intento
            try:
                return await super()._download_url(url)
            except Exception as fallback_exc:
                logger.error("mobile_de_playwright: fallback httpx también falló: %s", fallback_exc)
                # Propagar el error original de Playwright si fallback también falla, envolver
                raise fallback_exc from exc
