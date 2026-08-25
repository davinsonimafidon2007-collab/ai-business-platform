"""Tests de MobileDePlaywrightProvider (TEST.PROV.PW.1).

El borde externo mockeado es el NAVEGADOR (módulo ``playwright`` inyectado en
``sys.modules``) y el transporte httpx del padre. Toda la lógica bajo test es
real: flag de activación, import condicional, construcción del contexto,
detección anti-bot y política de fallback.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import AsyncMock

import pytest

from app.core.config import settings
from app.providers.exceptions import ProviderConnectionError
from app.providers.mobile_de import MobileDeProvider
from app.providers.mobile_de_playwright import MobileDePlaywrightProvider


@pytest.fixture(autouse=True)
def _restore_parent_download():
    """Aísla el monkeypatch de MobileDeProvider._download_url entre tests."""
    original = MobileDeProvider._download_url
    yield
    MobileDeProvider._download_url = original


def _install_fake_playwright(
    monkeypatch: pytest.MonkeyPatch, *, content: str = "<html>render</html>", crash: Exception | None = None
) -> dict[str, object]:
    """Inyecta un módulo playwright.async_api falso con un browser headless fake."""
    calls: dict[str, object] = {}

    class FakePage:
        async def goto(self, url: str, **kwargs: object) -> None:
            calls["goto"] = url
            if crash:
                raise crash

        async def wait_for_selector(self, *args: object, **kwargs: object) -> None:
            calls["waited_selector"] = True

        async def wait_for_timeout(self, ms: int) -> None:
            calls["timeout_ms"] = ms

        async def content(self) -> str:
            return content

    class FakeContext:
        async def new_page(self) -> FakePage:
            return FakePage()

        async def close(self) -> None:
            calls["context_closed"] = True

    class FakeBrowser:
        async def new_context(self, **kwargs: object) -> FakeContext:
            calls["context_kwargs"] = kwargs
            return FakeContext()

        async def close(self) -> None:
            calls["browser_closed"] = True

    class FakeChromium:
        async def launch(self, **kwargs: object) -> FakeBrowser:
            calls["launch_kwargs"] = kwargs
            return FakeBrowser()

    class FakePW:
        chromium = FakeChromium()

        async def __aenter__(self) -> FakePW:
            return self

        async def __aexit__(self, *exc: object) -> None:
            return None

    pw_module = types.ModuleType("playwright")
    api_module = types.ModuleType("playwright.async_api")
    api_module.async_playwright = lambda: FakePW()  # type: ignore[attr-defined]
    pw_module.async_api = api_module  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "playwright", pw_module)
    monkeypatch.setitem(sys.modules, "playwright.async_api", api_module)
    return calls


@pytest.mark.asyncio
async def test_flag_disabled_uses_httpx_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "enable_mobile_de_playwright", False)
    parent_mock = AsyncMock(return_value="<html>via-httpx</html>")
    monkeypatch.setattr(MobileDeProvider, "_download_url", parent_mock)

    provider = MobileDePlaywrightProvider()
    result = await provider._download_url("https://suchen.mobile.de/x")

    assert result == "<html>via-httpx</html>"
    parent_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_flag_enabled_navigates_browser_and_returns_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "enable_mobile_de_playwright", True)
    monkeypatch.setattr(settings, "provider_http_proxy", "")
    calls = _install_fake_playwright(monkeypatch, content="<html>listado-js</html>")

    provider = MobileDePlaywrightProvider()
    result = await provider._download_url("https://suchen.mobile.de/suchen/x")

    assert result == "<html>listado-js</html>"
    assert calls["goto"] == "https://suchen.mobile.de/suchen/x"
    launch = calls["launch_kwargs"]
    assert launch["headless"] is True
    assert launch["proxy"] is None
    ctx = calls["context_kwargs"]
    assert ctx["locale"] == "de-DE"


@pytest.mark.asyncio
async def test_proxy_and_cookies_forwarded_to_context(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "enable_mobile_de_playwright", True)
    monkeypatch.setattr(settings, "provider_http_proxy", "http://user:pass@proxy:8080")
    monkeypatch.setattr(settings, "provider_http_cookies", "sid=abc; consent=1")
    calls = _install_fake_playwright(monkeypatch)

    provider = MobileDePlaywrightProvider()
    await provider._download_url("https://suchen.mobile.de/x")

    launch = calls["launch_kwargs"]
    assert launch["proxy"] == {"server": "http://user:pass@proxy:8080"}
    headers = calls["context_kwargs"]["extra_http_headers"]
    assert headers["Cookie"] == "sid=abc; consent=1"


@pytest.mark.asyncio
async def test_missing_playwright_package_falls_back_to_httpx(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "enable_mobile_de_playwright", True)
    # Simular paquete no instalado
    monkeypatch.setitem(sys.modules, "playwright", None)
    monkeypatch.setitem(sys.modules, "playwright.async_api", None)
    parent_mock = AsyncMock(return_value="<html>httpx-ok</html>")
    monkeypatch.setattr(MobileDeProvider, "_download_url", parent_mock)

    provider = MobileDePlaywrightProvider()
    result = await provider._download_url("https://suchen.mobile.de/x")

    assert result == "<html>httpx-ok</html>"
    parent_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_browser_crash_falls_back_to_httpx(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "enable_mobile_de_playwright", True)
    _install_fake_playwright(monkeypatch, crash=RuntimeError("chromium exploded"))
    parent_mock = AsyncMock(return_value="<html>httpx-rescate</html>")
    monkeypatch.setattr(MobileDeProvider, "_download_url", parent_mock)

    provider = MobileDePlaywrightProvider()
    result = await provider._download_url("https://suchen.mobile.de/x")

    assert result == "<html>httpx-rescate</html>"


@pytest.mark.asyncio
async def test_browser_crash_and_httpx_failure_raise_chained(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "enable_mobile_de_playwright", True)
    _install_fake_playwright(monkeypatch, crash=RuntimeError("browser down"))
    httpx_error = ProviderConnectionError("mobile.de 403 anti-bot", provider="mobile_de")
    monkeypatch.setattr(MobileDeProvider, "_download_url", AsyncMock(side_effect=httpx_error))

    provider = MobileDePlaywrightProvider()
    with pytest.raises(Exception) as exc_info:
        await provider._download_url("https://suchen.mobile.de/x")

    # El error final es el del fallback httpx; la causa original queda encadenada.
    assert exc_info.value is httpx_error or isinstance(exc_info.value.__cause__, RuntimeError)


@pytest.mark.asyncio
async def test_antibot_content_raises_connection_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "enable_mobile_de_playwright", True)
    blocked = "<html>Access Denied - Zugriff verweigert</html>"
    calls = _install_fake_playwright(monkeypatch, content=blocked)

    provider = MobileDePlaywrightProvider()
    # El padre detecta bloqueo sobre el HTML renderizado
    raise_calls: list[tuple[str, str]] = []
    original_check = MobileDeProvider._raise_if_blocked

    def spy_check(self: MobileDeProvider, html: str, url: str) -> None:
        raise_calls.append((html, url))
        return original_check(self, html, url)

    monkeypatch.setattr(MobileDeProvider, "_raise_if_blocked", spy_check)

    with pytest.raises(ProviderConnectionError):
        await provider._download_url("https://suchen.mobile.de/x")

    # El contenido renderizado SÍ llegó al detector anti-bot
    assert raise_calls and raise_calls[0][0] == blocked
    assert calls.get("goto")
