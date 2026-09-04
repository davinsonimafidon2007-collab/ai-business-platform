"""Tests de la abstracción BrowserAutomation (BROWSER.1).

Cubre: selección de backend (get_browser_automation), OpenClawBrowserAutomation
(no configurado, no disponible, timeout, respuesta malformada, bloqueado,
éxito) y que ninguna implementación fabrica resultados cuando el backend
no está disponible — siempre debe levantar ProviderUnavailableError para
que el caller decida el fallback.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.providers.browser_automation import (
    OpenClawBrowserAutomation,
    PlaywrightBrowserAutomation,
    get_browser_automation,
)
from app.providers.exceptions import ProviderUnavailableError


def _settings(**overrides: object) -> SimpleNamespace:
    base = dict(
        enable_openclaw_browser=False,
        openclaw_endpoint="",
        openclaw_agent_id="",
        openclaw_timeout_ms=45000,
        enable_mobile_de_playwright=False,
        playwright_timeout_ms=30000,
        playwright_headless=True,
        provider_http_proxy="",
        provider_http_cookies="",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


# ---------------------------------------------------------------------------
# get_browser_automation: selección de backend
# ---------------------------------------------------------------------------


def test_no_backend_enabled_returns_none() -> None:
    assert get_browser_automation(_settings()) is None


def test_only_playwright_enabled_returns_playwright() -> None:
    backend = get_browser_automation(_settings(enable_mobile_de_playwright=True))
    assert isinstance(backend, PlaywrightBrowserAutomation)


def test_openclaw_enabled_without_endpoint_falls_back_to_playwright() -> None:
    """enable_openclaw_browser=True pero sin endpoint configurado no debe
    construir un OpenClawBrowserAutomation roto — cae a Playwright si está
    habilitado, o a None si tampoco."""
    backend = get_browser_automation(
        _settings(enable_openclaw_browser=True, openclaw_endpoint="", enable_mobile_de_playwright=True)
    )
    assert isinstance(backend, PlaywrightBrowserAutomation)


def test_openclaw_enabled_with_endpoint_takes_priority_over_playwright() -> None:
    backend = get_browser_automation(
        _settings(
            enable_openclaw_browser=True,
            openclaw_endpoint="http://localhost:4173",
            enable_mobile_de_playwright=True,
        )
    )
    assert isinstance(backend, OpenClawBrowserAutomation)


def test_playwright_receives_user_agent_and_cookies() -> None:
    backend = get_browser_automation(
        _settings(enable_mobile_de_playwright=True, provider_http_cookies="sid=abc"),
        user_agent="custom-ua/1.0",
    )
    assert isinstance(backend, PlaywrightBrowserAutomation)
    assert backend._user_agent == "custom-ua/1.0"
    assert backend._extra_headers["Cookie"] == "sid=abc"


# ---------------------------------------------------------------------------
# OpenClawBrowserAutomation
# ---------------------------------------------------------------------------


def test_openclaw_construction_without_endpoint_raises_unavailable() -> None:
    with pytest.raises(ProviderUnavailableError):
        OpenClawBrowserAutomation(endpoint="", agent_id="mobile-de-browser")


@pytest.mark.asyncio
async def test_openclaw_fetch_success_returns_html() -> None:
    automation = OpenClawBrowserAutomation(
        endpoint="http://localhost:4173", agent_id="mobile-de-browser"
    )

    class _Resp:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"status": "ok", "html": "<html>listado</html>"}

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=_Resp())

    with patch("httpx.AsyncClient", return_value=mock_client):
        html = await automation.fetch("https://suchen.mobile.de/x", wait_selector="article")

    assert html == "<html>listado</html>"
    mock_client.post.assert_awaited_once()
    call = mock_client.post.call_args
    assert call.args[0] == "http://localhost:4173/agents/mobile-de-browser/fetch"
    assert call.kwargs["json"] == {"url": "https://suchen.mobile.de/x", "wait_selector": "article"}


@pytest.mark.asyncio
async def test_openclaw_fetch_unreachable_raises_unavailable_not_generic() -> None:
    automation = OpenClawBrowserAutomation(endpoint="http://localhost:4173", agent_id="x")

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(side_effect=httpx.ConnectError("connection refused"))

    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(ProviderUnavailableError):
            await automation.fetch("https://suchen.mobile.de/x")


@pytest.mark.asyncio
async def test_openclaw_fetch_timeout_raises_unavailable() -> None:
    automation = OpenClawBrowserAutomation(endpoint="http://localhost:4173", agent_id="x")

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(ProviderUnavailableError):
            await automation.fetch("https://suchen.mobile.de/x")


@pytest.mark.asyncio
async def test_openclaw_fetch_malformed_response_raises_unavailable() -> None:
    """status != "ok" o sin campo html utilizable -> nunca se fabrica HTML vacío."""
    automation = OpenClawBrowserAutomation(endpoint="http://localhost:4173", agent_id="x")

    class _Resp:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"status": "blocked", "warnings": ["anti-bot"]}

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=_Resp())

    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(ProviderUnavailableError):
            await automation.fetch("https://suchen.mobile.de/x")


@pytest.mark.asyncio
async def test_openclaw_fetch_status_ok_without_html_raises_unavailable() -> None:
    automation = OpenClawBrowserAutomation(endpoint="http://localhost:4173", agent_id="x")

    class _Resp:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"status": "ok"}  # sin "html"

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=_Resp())

    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(ProviderUnavailableError):
            await automation.fetch("https://suchen.mobile.de/x")
