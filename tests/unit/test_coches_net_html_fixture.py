from __future__ import annotations

import pytest

from app.core.config import settings
from app.providers.coches_net_html import CochesNetHtmlFixtureProvider
from app.providers.registry import ProviderRegistry


def setup_function() -> None:
    ProviderRegistry.clear()


def teardown_function() -> None:
    ProviderRegistry.clear()


@pytest.fixture
def provider() -> CochesNetHtmlFixtureProvider:
    return CochesNetHtmlFixtureProvider()


@pytest.mark.asyncio
async def test_html_fixture_parses_three_ads(provider: CochesNetHtmlFixtureProvider) -> None:
    all_ = await provider.search("")
    assert len(all_) >= 3


@pytest.mark.asyncio
async def test_html_fixture_filter_bmw(provider: CochesNetHtmlFixtureProvider) -> None:
    hits = await provider.search("BMW")
    assert len(hits) >= 2
    assert all(h.brand and "bmw" in h.brand.lower() for h in hits)


@pytest.mark.asyncio
async def test_html_fixture_prices(provider: CochesNetHtmlFixtureProvider) -> None:
    hits = await provider.search("BMW")
    assert hits[0].price and hits[0].price > 1000


@pytest.mark.asyncio
async def test_no_http(provider: CochesNetHtmlFixtureProvider) -> None:
    with pytest.raises(RuntimeError, match="does not use HTTP"):
        await provider._download_url("https://www.coches.net/")


def test_registry_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "enable_coches_net_html_fixture", False)
    monkeypatch.setattr(settings, "default_import_cost_profile", "GERMANY")
    monkeypatch.setattr(settings, "enable_es_market_fixture", False)
    monkeypatch.setattr(settings, "enable_coches_net_fixture", False)
    monkeypatch.setattr(settings, "enable_autoscout24_es", False)
    ProviderRegistry.ensure_default_providers()
    assert "coches_net_html_fixture" not in ProviderRegistry.list_providers()


def test_registry_flag_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "enable_coches_net_html_fixture", True)
    monkeypatch.setattr(settings, "default_import_cost_profile", "GERMANY")
    monkeypatch.setattr(settings, "enable_es_market_fixture", False)
    monkeypatch.setattr(settings, "enable_coches_net_fixture", False)
    monkeypatch.setattr(settings, "enable_autoscout24_es", False)
    ProviderRegistry.ensure_default_providers()
    assert "coches_net_html_fixture" in ProviderRegistry.list_providers()


def test_registry_spain_profile_does_not_auto_enable_html(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "default_import_cost_profile", "SPAIN")
    monkeypatch.setattr(settings, "enable_coches_net_html_fixture", False)
    monkeypatch.setattr(settings, "enable_es_market_fixture", False)
    monkeypatch.setattr(settings, "enable_coches_net_fixture", False)
    monkeypatch.setattr(settings, "enable_autoscout24_es", False)
    ProviderRegistry.ensure_default_providers()
    assert "coches_net_html_fixture" not in ProviderRegistry.list_providers()
