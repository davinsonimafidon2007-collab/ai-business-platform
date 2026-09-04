"""Abstracción de browser automation (BROWSER.1).

El dominio y los providers (``MobileDeProvider`` y derivados) no deben saber
si el navegador que renderiza una página está controlado por Playwright,
OpenClaw o cualquier otro backend. Solo conocen ``BrowserAutomation``:

    html = await browser.fetch(url, wait_selector="article")

Implementaciones:
    - ``PlaywrightBrowserAutomation``: Chromium headless local (playwright).
    - ``OpenClawBrowserAutomation``: delega en un agente OpenClaw externo
      (HTTP). Capa OPCIONAL: si no está configurada/disponible, el sistema
      debe seguir funcionando sin ella (ver ``get_browser_automation``).

Ninguna implementación debe:
    - intentar evadir/bypassear anti-bot (CAPTCHA solving, stealth,
      fingerprint spoofing, rotación fraudulenta de identidad);
    - inventar resultados cuando el proveedor bloquea el acceso (eso lo
      decide el caller vía ``_raise_if_blocked`` sobre el HTML devuelto,
      igual que con el transporte httpx).

Esta capa solo devuelve el HTML tal cual lo ve el navegador — el parsing y
la detección de bloqueo siguen viviendo en el provider (``MobileDeProvider``),
sin duplicar esa lógica aquí.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

from app.providers.exceptions import ProviderUnavailableError

logger = logging.getLogger(__name__)


@runtime_checkable
class BrowserAutomation(Protocol):
    """Contrato mínimo que debe cumplir cualquier backend de browser automation."""

    async def fetch(
        self,
        url: str,
        *,
        wait_selector: str | None = None,
    ) -> str:
        """Navega a ``url`` y devuelve el HTML final renderizado.

        Args:
            url: URL absoluta a visitar.
            wait_selector: selector CSS opcional a esperar antes de leer el
                DOM (best-effort: si no aparece en el timeout corto interno,
                se lee el DOM igualmente en vez de fallar).

        Raises:
            ProviderUnavailableError: si este backend de browser no está
                disponible (no instalado, no configurado, no responde).
            Exception: errores de navegación (timeout, crash del browser)
                se propagan tal cual; el caller decide si hace fallback.
        """
        ...


class PlaywrightBrowserAutomation:
    """Backend Chromium headless local vía ``playwright.async_api``.

    No requiere ningún servicio externo: lanza y cierra un browser por
    llamada a ``fetch`` (una búsqueda = una carga de página de resultados,
    no una por vehículo — ver AUDIT.PERF.1).
    """

    def __init__(
        self,
        *,
        timeout_ms: int = 30000,
        headless: bool = True,
        proxy: str | None = None,
        user_agent: str | None = None,
        extra_headers: dict[str, str] | None = None,
        locale: str = "de-DE",
    ) -> None:
        self._timeout_ms = timeout_ms
        self._headless = headless
        self._proxy = proxy
        self._user_agent = user_agent
        self._extra_headers = dict(extra_headers or {})
        self._locale = locale

    async def fetch(self, url: str, *, wait_selector: str | None = None) -> str:
        try:
            from playwright.async_api import async_playwright  # type: ignore
        except ImportError as exc:
            raise ProviderUnavailableError(
                "playwright no está instalado en este entorno.",
                provider="playwright_browser",
            ) from exc

        pw_proxy = {"server": self._proxy} if self._proxy else None
        context_kwargs: dict[str, Any] = {
            "user_agent": self._user_agent,
            "locale": self._locale,
            "extra_http_headers": dict(self._extra_headers),
        }

        logger.info(
            "playwright_browser: navegando %s (headless=%s, proxy=%s)",
            url,
            self._headless,
            bool(self._proxy),
        )
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self._headless, proxy=pw_proxy)  # type: ignore[arg-type]
            try:
                context = await browser.new_context(**context_kwargs)
                page = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=self._timeout_ms)
                if wait_selector:
                    try:
                        await page.wait_for_selector(wait_selector, timeout=5000)
                    except Exception:
                        pass  # best-effort: la página puede estar vacía o bloqueada
                await page.wait_for_timeout(800)  # deja hidratar JS
                content = await page.content()
                await context.close()
                return content
            finally:
                await browser.close()


class OpenClawBrowserAutomation:
    """Backend que delega la navegación en un agente OpenClaw externo.

    Capa puramente HTTP: no importa ningún SDK/paquete de OpenClaw ni de
    Claude. Habla un contrato JSON simple con el endpoint configurado
    (``settings.openclaw_endpoint``). Si el endpoint no está configurado o
    no responde, levanta ``ProviderUnavailableError`` para que el caller
    haga fallback (Playwright/httpx) — nunca inventa un HTML de respuesta.

    Contrato esperado del endpoint (``POST {endpoint}/agents/{agent_id}/fetch``):
        request:  {"url": "...", "wait_selector": "..." | null}
        response: {"html": "...", "status": "ok" | "blocked" | "error", ...}
    """

    def __init__(
        self,
        *,
        endpoint: str,
        agent_id: str,
        timeout_ms: int = 45000,
    ) -> None:
        if not endpoint:
            raise ProviderUnavailableError(
                "OpenClaw no está configurado (openclaw_endpoint vacío).",
                provider="openclaw_browser",
            )
        self._endpoint = endpoint.rstrip("/")
        self._agent_id = agent_id or "mobile-de-browser"
        self._timeout_ms = timeout_ms

    async def fetch(self, url: str, *, wait_selector: str | None = None) -> str:
        import httpx

        request_url = f"{self._endpoint}/agents/{self._agent_id}/fetch"
        try:
            async with httpx.AsyncClient(timeout=self._timeout_ms / 1000) as client:
                response = await client.post(
                    request_url,
                    json={"url": url, "wait_selector": wait_selector},
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderUnavailableError(
                f"OpenClaw no disponible o respuesta inválida ({type(exc).__name__}).",
                provider="openclaw_browser",
            ) from exc

        status = payload.get("status")
        html = payload.get("html")
        if status != "ok" or not isinstance(html, str):
            raise ProviderUnavailableError(
                f"OpenClaw devolvió status={status!r} sin HTML utilizable.",
                provider="openclaw_browser",
            )
        return html


def get_browser_automation(
    settings: Any,
    *,
    user_agent: str | None = None,
) -> BrowserAutomation | None:
    """Selecciona el backend de browser automation según configuración.

    Orden: OpenClaw (si ``enable_openclaw_browser`` y ``openclaw_endpoint``
    configurados) → Playwright (si ``enable_mobile_de_playwright``) → None
    (el caller debe hacer fallback a httpx puro).

    ``user_agent`` se reenvía al backend Playwright (típicamente el
    User-Agent que ya usa el ``ProviderHttpClient`` del provider, para
    mantener consistencia entre transporte httpx y browser).

    No lanza excepciones: la construcción de ``OpenClawBrowserAutomation``
    ya valida que ``endpoint`` no esté vacío, y la ausencia del paquete
    ``playwright`` se detecta en ``fetch()``, no aquí — así el caller decide
    en un único lugar (su propio ``try/except ProviderUnavailableError``)
    qué hacer ante cualquier backend no disponible.
    """
    if getattr(settings, "enable_openclaw_browser", False) and getattr(
        settings, "openclaw_endpoint", ""
    ):
        return OpenClawBrowserAutomation(
            endpoint=settings.openclaw_endpoint,
            agent_id=getattr(settings, "openclaw_agent_id", "") or "mobile-de-browser",
            timeout_ms=int(getattr(settings, "openclaw_timeout_ms", 45000) or 45000),
        )
    if getattr(settings, "enable_mobile_de_playwright", False):
        extra_headers = {"Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8"}
        cookies_raw = (getattr(settings, "provider_http_cookies", "") or "").strip()
        if cookies_raw:
            extra_headers["Cookie"] = cookies_raw
        return PlaywrightBrowserAutomation(
            timeout_ms=int(getattr(settings, "playwright_timeout_ms", 30000) or 30000),
            headless=bool(getattr(settings, "playwright_headless", True)),
            proxy=(getattr(settings, "provider_http_proxy", "") or "").strip() or None,
            user_agent=user_agent,
            extra_headers=extra_headers,
        )
    return None
