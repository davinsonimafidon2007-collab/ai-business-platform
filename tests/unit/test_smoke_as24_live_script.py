"""SMOKE.AS24.LIVE.1: exit codes de scripts/smoke_as24_live.py (con mocks).

El script real toca red; aquí se mockea el provider para fijar el contrato de
exit codes, que es lo que consume ops:

  0 → al menos 1 listing
  1 → 0 listings o cualquier error (red, parse, rate-limit)
"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.providers.exceptions import (
    ProviderConnectionError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)

_SCRIPT = (
    Path(__file__).resolve().parents[2] / "scripts" / "smoke_as24_live.py"
)


def _load_script() -> ModuleType:
    """Carga el script por ruta (``scripts/`` no es un paquete importable)."""
    spec = importlib.util.spec_from_file_location("smoke_as24_live", _SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def script() -> ModuleType:
    return _load_script()


def _listing(external_id: str = "as24-1", price: float = 9500.0) -> MagicMock:
    item = MagicMock()
    item.external_id = external_id
    item.brand = "BMW"
    item.model = "320d"
    item.price = price
    item.year = 2018
    return item


def _patch_provider(search: AsyncMock) -> MagicMock:
    provider_cls = MagicMock()
    provider_cls.return_value.search = search
    provider_cls.return_value.close = AsyncMock()
    return provider_cls


def _run(script: ModuleType, search: AsyncMock) -> tuple[int, dict]:
    with patch(
        "app.providers.autoscout24.AutoScout24Provider", _patch_provider(search)
    ):
        return asyncio.run(script._run_smoke(script.DEFAULT_SEARCH_URL, 5.0))


def test_exit_0_with_listings(script: ModuleType) -> None:
    code, payload = _run(script, AsyncMock(return_value=[_listing(), _listing("as24-2")]))

    assert code == 0
    assert payload["status"] == "ok"
    assert payload["count"] == 2
    assert payload["sample"]["external_id"] == "as24-1"


def test_exit_1_with_zero_listings(script: ModuleType) -> None:
    """HTTP OK pero 0 listings = parser roto: debe fallar, no pasar en silencio."""
    code, payload = _run(script, AsyncMock(return_value=[]))

    assert code == 1
    assert payload["status"] == "fail"
    assert payload["count"] == 0
    assert "selector" in payload["hint"].lower()


def test_exit_1_on_rate_limit(script: ModuleType) -> None:
    code, payload = _run(
        script,
        AsyncMock(side_effect=ProviderRateLimitError("429", provider="autoscout24")),
    )

    assert code == 1
    assert payload["status"] == "rate_limited"
    assert "rate-limit" in payload["hint"].lower()


def test_exit_1_on_timeout(script: ModuleType) -> None:
    code, payload = _run(
        script,
        AsyncMock(side_effect=ProviderTimeoutError("timeout", provider="autoscout24")),
    )

    assert code == 1
    assert payload["status"] == "timeout"


def test_exit_1_on_connection_error(script: ModuleType) -> None:
    code, payload = _run(
        script,
        AsyncMock(side_effect=ProviderConnectionError("refused", provider="autoscout24")),
    )

    assert code == 1
    assert payload["status"] == "blocked"


def test_unexpected_error_has_no_raw_traceback(script: ModuleType) -> None:
    """Ops debe ver un mensaje legible, no un traceback."""
    code, payload = _run(script, AsyncMock(side_effect=RuntimeError("boom")))

    assert code == 1
    assert payload["status"] == "error"
    assert payload["error"] == "RuntimeError: boom"
    assert "Traceback" not in payload["error"]


def test_script_does_not_touch_mobile_de(script: ModuleType) -> None:
    """El smoke es AS24-only: mobile.de no debe aparecer."""
    source = _SCRIPT.read_text(encoding="utf-8")

    assert "MobileDeProvider" not in source
    assert "suchen.mobile.de" not in source
