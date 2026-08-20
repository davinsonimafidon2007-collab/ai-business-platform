from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from app.providers.base import VehicleProvider
from app.providers.circuit_breaker import ProviderCircuitBreaker
from app.providers.exceptions import ProviderUnavailableError


class DummyProvider(VehicleProvider):
    @property
    def source_name(self) -> str:
        return "mobile_de"

    def _find_listing_nodes(self, soup):
        return []


@pytest.mark.asyncio
async def test_fourth_call_instantly_unavailable_after_three_403s(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = DummyProvider()
    response_403 = httpx.Response(403, request=httpx.Request("GET", "https://example.com"))
    error_403 = httpx.HTTPStatusError("403", request=response_403.request, response=response_403)
    http_client = AsyncMock()
    http_client.get.side_effect = [error_403, error_403, error_403, AssertionError("should not call http after circuit opens")]
    provider._http_client = http_client

    breaker = ProviderCircuitBreaker(failure_threshold=3, cooldown_seconds=60)
    monkeypatch.setattr("app.providers.base.circuit_breaker", breaker)

    with pytest.raises(httpx.HTTPStatusError):
        await provider.search("https://example.com/search")

    with pytest.raises(httpx.HTTPStatusError):
        await provider.search("https://example.com/search")

    with pytest.raises(httpx.HTTPStatusError):
        await provider.search("https://example.com/search")

    with pytest.raises(ProviderUnavailableError, match="mobile_de: circuito abierto"):
        await provider.search("https://example.com/search")
