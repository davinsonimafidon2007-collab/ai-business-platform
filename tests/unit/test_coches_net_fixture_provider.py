from __future__ import annotations

import pytest

from app.core.config import settings
from app.providers.coches_net_fixture import CochesNetFixtureProvider
from app.providers.registry import ProviderRegistry


def setup_function() -> None:
    ProviderRegistry.clear()


def teardown_function() -> None:
    ProviderRegistry.clear()


@pytest.fixture
def provider() -> CochesNetFixtureProvider:
    return CochesNetFixtureProvider()


@pytest.mark.asyncio
async def test_search_bmw_returns_listings(provider: CochesNetFixtureProvider) -> None:
    results = await provider.search("BMW 320")
    # "Serie 3" + version 320d debe matchear tokens bmw + 320
    assert len(results) >= 2
    assert all(r.source == "coches_net_fixture" for r in results)
    assert all(r.price and r.price > 0 for r in results)


@pytest.mark.asyncio
async def test_search_unknown_empty(provider: CochesNetFixtureProvider) -> None:
    assert await provider.search("Ferrari F40 rare") == []


@pytest.mark.asyncio
async def test_get_vehicle(provider: CochesNetFixtureProvider) -> None:
    d = await provider.get_vehicle("cn-bmw-320d-001")
    assert d.external_id == "cn-bmw-320d-001"
    assert d.price == 19200
    assert d.source == "coches_net_fixture"


@pytest.mark.asyncio
async def test_no_http(provider: CochesNetFixtureProvider) -> None:
    with pytest.raises(RuntimeError, match="does not use HTTP"):
        await provider._download_url("https://www.coches.net/")


def test_registry_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "default_import_cost_profile", "GERMANY")
    monkeypatch.setattr(settings, "enable_coches_net_fixture", False)
    monkeypatch.setattr(settings, "enable_es_market_fixture", False)
    monkeypatch.setattr(settings, "enable_autoscout24_es", False)
    ProviderRegistry.ensure_default_providers()
    assert "coches_net_fixture" not in ProviderRegistry.list_providers()


def test_registry_flag_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "default_import_cost_profile", "GERMANY")
    monkeypatch.setattr(settings, "enable_coches_net_fixture", True)
    monkeypatch.setattr(settings, "enable_es_market_fixture", False)
    monkeypatch.setattr(settings, "enable_autoscout24_es", False)
    ProviderRegistry.ensure_default_providers()
    assert "coches_net_fixture" in ProviderRegistry.list_providers()


def test_registry_spain_profile_auto_enables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "default_import_cost_profile", "SPAIN")
    monkeypatch.setattr(settings, "enable_coches_net_fixture", False)
    monkeypatch.setattr(settings, "enable_es_market_fixture", False)
    monkeypatch.setattr(settings, "enable_autoscout24_es", False)
    ProviderRegistry.ensure_default_providers()
    assert "coches_net_fixture" in ProviderRegistry.list_providers()
