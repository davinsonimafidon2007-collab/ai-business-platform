"""Tests unitarios para ProviderCanaryJob — Task A.5.

Cubre el comportamiento estricto del canary respecto a mobile.de:

1. Sin proxy/cookies: mobile.de 403 → WARN, job SUCCESS (si AS24 OK).
2. Con proxy/cookies: mobile.de 403 → FAIL.
3. Con proxy/cookies: mobile.de listings > 0 → job SUCCESS, mobile_status=ok.
4. Con proxy/cookies: mobile.de 0 listings → FAIL.
5. `_anti_bot_configured()` toggle según proxy/cookies en settings.

No hace falta red real: se mockean `MobileDeProvider.search` y
`AutoScout24Provider.search` y `.close`.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.jobs.base import JobContext
from app.jobs.provider_canary import (
    ProviderCanaryJob,
    _anti_bot_configured,
)
from app.providers.exceptions import ProviderConnectionError


def _make_context() -> JobContext:
    """JobContext con logger y db_manager triviales (settings no usado)."""
    manager = MagicMock()
    return JobContext(
        db_manager=manager,
        settings=MagicMock(),
        logger=logging.getLogger("test_provider_canary"),
    )


def _as24_result(count: int):
    """Devuelve una lista de resultados con `count` elementos (mocks)."""
    results = []
    for i in range(count):
        r = MagicMock()
        r.external_id = f"as24-{i}"
        r.price = 1000 + i
        results.append(r)
    return results


def _mobile_result(count: int):
    results = []
    for i in range(count):
        r = MagicMock()
        r.external_id = f"mobile-{i}"
        results.append(r)
    return results


@pytest.mark.asyncio
async def test_no_proxy_403_blocked_warns_success():
    """Sin proxy: AS24 OK + mobile 403 → job SUCCESS, mobile_status=blocked."""
    as24_provider_cls = MagicMock()
    as24_instance = as24_provider_cls.return_value
    as24_instance.search = AsyncMock(return_value=_as24_result(3))
    as24_instance.close = AsyncMock()

    mobile_provider_cls = MagicMock()
    mobile_instance = mobile_provider_cls.return_value
    mobile_instance.search = AsyncMock(
        side_effect=ProviderConnectionError(
            "mobile.de bloqueó la petición (HTTP 403).",
            provider="mobile_de",
        )
    )
    mobile_instance.close = AsyncMock()

    with (
        patch(
            "app.jobs.provider_canary.AutoScout24Provider", as24_provider_cls
        ),
        patch("app.jobs.provider_canary.MobileDeProvider", mobile_provider_cls),
        patch(
            "app.jobs.provider_canary.settings.provider_http_proxy", ""
        ),
        patch(
            "app.jobs.provider_canary.settings.provider_http_cookies", ""
        ),
        patch("app.jobs.provider_canary.settings.enable_mobile_de", True),
    ):
        job = ProviderCanaryJob()
        result = await job.execute(_make_context())

    assert result.success is True
    assert result.data["mobile_status"] == "blocked"
    assert result.data["strict_mobile"] is False


@pytest.mark.asyncio
async def test_with_proxy_403_blocked_fails():
    """Con proxy: AS24 OK + mobile 403 → job FAILURE, mobile_status=blocked."""
    as24_provider_cls = MagicMock()
    as24_instance = as24_provider_cls.return_value
    as24_instance.search = AsyncMock(return_value=_as24_result(3))
    as24_instance.close = AsyncMock()

    mobile_provider_cls = MagicMock()
    mobile_instance = mobile_provider_cls.return_value
    mobile_instance.search = AsyncMock(
        side_effect=ProviderConnectionError(
            "mobile.de bloqueó la petición (HTTP 403).",
            provider="mobile_de",
        )
    )
    mobile_instance.close = AsyncMock()

    with (
        patch(
            "app.jobs.provider_canary.AutoScout24Provider", as24_provider_cls
        ),
        patch("app.jobs.provider_canary.MobileDeProvider", mobile_provider_cls),
        patch(
            "app.jobs.provider_canary.settings.provider_http_proxy",
            "http://user:pass@host:port",
        ),
        patch(
            "app.jobs.provider_canary.settings.provider_http_cookies", ""
        ),
        patch("app.jobs.provider_canary.settings.enable_mobile_de", True),
    ):
        job = ProviderCanaryJob()
        result = await job.execute(_make_context())

    assert result.success is False
    assert result.data["mobile_status"] == "blocked"
    assert result.data["strict_mobile"] is True


@pytest.mark.asyncio
async def test_with_proxy_listings_success():
    """Con proxy: AS24 OK + mobile listings>0 → job SUCCESS, mobile_status=ok."""
    as24_provider_cls = MagicMock()
    as24_instance = as24_provider_cls.return_value
    as24_instance.search = AsyncMock(return_value=_as24_result(3))
    as24_instance.close = AsyncMock()

    mobile_provider_cls = MagicMock()
    mobile_instance = mobile_provider_cls.return_value
    mobile_instance.search = AsyncMock(return_value=_mobile_result(5))
    mobile_instance.close = AsyncMock()

    with (
        patch(
            "app.jobs.provider_canary.AutoScout24Provider", as24_provider_cls
        ),
        patch("app.jobs.provider_canary.MobileDeProvider", mobile_provider_cls),
        patch(
            "app.jobs.provider_canary.settings.provider_http_proxy",
            "http://user:pass@host:port",
        ),
        patch(
            "app.jobs.provider_canary.settings.provider_http_cookies", ""
        ),
        patch("app.jobs.provider_canary.settings.enable_mobile_de", True),
    ):
        job = ProviderCanaryJob()
        result = await job.execute(_make_context())

    assert result.success is True
    assert result.data["mobile_status"] == "ok"
    assert result.data["strict_mobile"] is True


@pytest.mark.asyncio
async def test_with_proxy_zero_listings_fails():
    """Con proxy: AS24 OK + mobile 0 listings → job FAILURE, mobile_status=empty."""
    as24_provider_cls = MagicMock()
    as24_instance = as24_provider_cls.return_value
    as24_instance.search = AsyncMock(return_value=_as24_result(3))
    as24_instance.close = AsyncMock()

    mobile_provider_cls = MagicMock()
    mobile_instance = mobile_provider_cls.return_value
    mobile_instance.search = AsyncMock(return_value=[])
    mobile_instance.close = AsyncMock()

    with (
        patch(
            "app.jobs.provider_canary.AutoScout24Provider", as24_provider_cls
        ),
        patch("app.jobs.provider_canary.MobileDeProvider", mobile_provider_cls),
        patch(
            "app.jobs.provider_canary.settings.provider_http_proxy",
            "http://user:pass@host:port",
        ),
        patch(
            "app.jobs.provider_canary.settings.provider_http_cookies", ""
        ),
        patch("app.jobs.provider_canary.settings.enable_mobile_de", True),
    ):
        job = ProviderCanaryJob()
        result = await job.execute(_make_context())

    assert result.success is False
    assert result.data["mobile_status"] == "empty"
    assert result.data["strict_mobile"] is True


@pytest.mark.asyncio
async def test_as24_zero_listings_fails_job():
    """SMOKE.AS24.LIVE.1: AS24 con 0 listings tumba el job aunque mobile vaya bien."""
    as24_provider_cls = MagicMock()
    as24_provider_cls.return_value.search = AsyncMock(return_value=[])
    as24_provider_cls.return_value.close = AsyncMock()

    mobile_provider_cls = MagicMock()
    mobile_provider_cls.return_value.search = AsyncMock(
        return_value=_mobile_result(5)
    )
    mobile_provider_cls.return_value.close = AsyncMock()

    with (
        patch("app.jobs.provider_canary.AutoScout24Provider", as24_provider_cls),
        patch("app.jobs.provider_canary.MobileDeProvider", mobile_provider_cls),
        patch("app.jobs.provider_canary.settings.provider_http_proxy", ""),
        patch("app.jobs.provider_canary.settings.provider_http_cookies", ""),
    ):
        result = await ProviderCanaryJob().execute(_make_context())

    assert result.success is False
    assert result.data["autoscout24"]["status"] == "fail"
    assert result.data["autoscout24"]["count"] == 0
    assert "AutoScout24" in result.message


@pytest.mark.asyncio
async def test_as24_connection_error_fails_job():
    """AS24 caído → job FAIL, status=error (mobile no puede salvarlo)."""
    as24_provider_cls = MagicMock()
    as24_provider_cls.return_value.search = AsyncMock(
        side_effect=ProviderConnectionError("timeout", provider="autoscout24")
    )
    as24_provider_cls.return_value.close = AsyncMock()

    mobile_provider_cls = MagicMock()
    mobile_provider_cls.return_value.search = AsyncMock(
        return_value=_mobile_result(3)
    )
    mobile_provider_cls.return_value.close = AsyncMock()

    with (
        patch("app.jobs.provider_canary.AutoScout24Provider", as24_provider_cls),
        patch("app.jobs.provider_canary.MobileDeProvider", mobile_provider_cls),
        patch("app.jobs.provider_canary.settings.provider_http_proxy", ""),
        patch("app.jobs.provider_canary.settings.provider_http_cookies", ""),
    ):
        result = await ProviderCanaryJob().execute(_make_context())

    assert result.success is False
    assert result.data["autoscout24"]["status"] == "error"
    assert "error" in result.data["autoscout24"]


@pytest.mark.asyncio
async def test_as24_ok_mobile_antibot_is_warn_not_fail():
    """Política AS24-first: mobile 403 sin proxy no tumba el job."""
    as24_provider_cls = MagicMock()
    as24_provider_cls.return_value.search = AsyncMock(return_value=_as24_result(20))
    as24_provider_cls.return_value.close = AsyncMock()

    mobile_provider_cls = MagicMock()
    mobile_provider_cls.return_value.search = AsyncMock(
        side_effect=ProviderConnectionError("HTTP 403", provider="mobile_de")
    )
    mobile_provider_cls.return_value.close = AsyncMock()

    with (
        patch("app.jobs.provider_canary.AutoScout24Provider", as24_provider_cls),
        patch("app.jobs.provider_canary.MobileDeProvider", mobile_provider_cls),
        patch("app.jobs.provider_canary.settings.provider_http_proxy", ""),
        patch("app.jobs.provider_canary.settings.provider_http_cookies", ""),
        patch("app.jobs.provider_canary.settings.enable_mobile_de", True),
    ):
        result = await ProviderCanaryJob().execute(_make_context())

    assert result.success is True
    assert result.data["policy"] == "as24_first"
    assert result.data["autoscout24"]["status"] == "ok"
    assert result.data["autoscout24"]["count"] == 20
    # warn_antibot, no fail: sin proxy el 403 no es concluyente.
    assert result.data["mobile_de"]["status"] == "warn_antibot"


@pytest.mark.asyncio
async def test_mobile_generic_error_without_proxy_does_not_fail_job():
    """Un error inesperado de mobile sin proxy tampoco tumba AS24-first."""
    as24_provider_cls = MagicMock()
    as24_provider_cls.return_value.search = AsyncMock(return_value=_as24_result(4))
    as24_provider_cls.return_value.close = AsyncMock()

    mobile_provider_cls = MagicMock()
    mobile_provider_cls.return_value.search = AsyncMock(
        side_effect=RuntimeError("boom")
    )
    mobile_provider_cls.return_value.close = AsyncMock()

    with (
        patch("app.jobs.provider_canary.AutoScout24Provider", as24_provider_cls),
        patch("app.jobs.provider_canary.MobileDeProvider", mobile_provider_cls),
        patch("app.jobs.provider_canary.settings.provider_http_proxy", ""),
        patch("app.jobs.provider_canary.settings.provider_http_cookies", ""),
        patch("app.jobs.provider_canary.settings.enable_mobile_de", True),
    ):
        result = await ProviderCanaryJob().execute(_make_context())

    assert result.success is True
    assert result.data["mobile_de"]["status"] == "error"


def test_anti_bot_configured_toggle():
    """`_anti_bot_configured` refleja proxy/cookies en settings."""
    with (
        patch(
            "app.jobs.provider_canary.settings.provider_http_proxy", ""
        ),
        patch(
            "app.jobs.provider_canary.settings.provider_http_cookies", ""
        ),
    ):
        assert _anti_bot_configured() is False

    with (
        patch(
            "app.jobs.provider_canary.settings.provider_http_proxy",
            "http://user:pass@host:port",
        ),
        patch(
            "app.jobs.provider_canary.settings.provider_http_cookies", ""
        ),
    ):
        assert _anti_bot_configured() is True

    with (
        patch(
            "app.jobs.provider_canary.settings.provider_http_proxy", ""
        ),
        patch(
            "app.jobs.provider_canary.settings.provider_http_cookies",
            "sid=abc; consent=1",
        ),
    ):
        assert _anti_bot_configured() is True
