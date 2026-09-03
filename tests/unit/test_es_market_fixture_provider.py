"""Tests unit para el provider offline de mercado ES (Task P.1a).

Sin red: search/get_vehicle leen de fixtures JSON locales.
"""

from __future__ import annotations

import pytest

from app.providers.es_market_fixture import EsMarketFixtureProvider
from app.providers.registry import ProviderRegistry


@pytest.fixture
def provider() -> EsMarketFixtureProvider:
    return EsMarketFixtureProvider()


@pytest.mark.asyncio
async def test_search_bmw_320_returns_es_listings(provider: EsMarketFixtureProvider) -> None:
    results = await provider.search("BMW 320")
    assert len(results) >= 2
    assert all(r.source == "es_market_fixture" for r in results)
    assert all(r.brand and "bmw" in r.brand.lower() for r in results)
    assert all(r.price and r.price > 0 for r in results)
    assert all(r.location for r in results)  # ES cities in fixture


@pytest.mark.asyncio
async def test_search_unknown_brand_empty(provider: EsMarketFixtureProvider) -> None:
    results = await provider.search("Ferrari F40 rare")
    assert results == []


@pytest.mark.asyncio
async def test_get_vehicle_known_id(provider: EsMarketFixtureProvider) -> None:
    detail = await provider.get_vehicle("es-bmw-320d-001")
    assert detail.external_id == "es-bmw-320d-001"
    assert detail.price == 18900
    assert detail.source == "es_market_fixture"


@pytest.mark.asyncio
async def test_get_vehicle_unknown_id_minimal(provider: EsMarketFixtureProvider) -> None:
    detail = await provider.get_vehicle("es-no-existe")
    assert detail.external_id == "es-no-existe"
    assert detail.source == "es_market_fixture"
    assert detail.price is None


@pytest.mark.asyncio
async def test_search_empty_query_returns_all(provider: EsMarketFixtureProvider) -> None:
    results = await provider.search("")
    assert len(results) >= 5


@pytest.mark.asyncio
async def test_no_http_download(provider: EsMarketFixtureProvider) -> None:
    with pytest.raises(RuntimeError, match="does not use HTTP"):
        await provider._download_url("https://example.com")


def test_registry_ensure_idempotent() -> None:
    ProviderRegistry.clear()
    ProviderRegistry.ensure_es_market_fixture(enabled=True)
    ProviderRegistry.ensure_es_market_fixture(enabled=True)
    assert "es_market_fixture" in ProviderRegistry.list_providers()
    ProviderRegistry.clear()


def test_registry_ensure_disabled_does_nothing() -> None:
    ProviderRegistry.clear()
    ProviderRegistry.ensure_es_market_fixture(enabled=False)
    assert "es_market_fixture" not in ProviderRegistry.list_providers()
    ProviderRegistry.clear()


@pytest.mark.asyncio
async def test_estimator_sees_es_fixture_source(monkeypatch: pytest.MonkeyPatch) -> None:
    """El fixture ES solo se usa como comparable si se pide explícitamente.

    TASK 4: en selección automática los providers simulados quedan fuera —
    el precio de mercado alimenta el ROI y no debe fijarse con anuncios
    inventados. Pidiéndolo explícitamente (modo offline de desarrollo) sigue
    funcionando, y eso es lo que verifica este test.
    """
    from unittest.mock import AsyncMock

    from app.providers.registry import ProviderRegistry
    from app.services.comparable_market_estimator import ComparableMarketEstimator

    ProviderRegistry.clear()
    ProviderRegistry.ensure_es_market_fixture(enabled=True)

    vehicle_service = AsyncMock()
    # search_from_provider debe delegar al provider real del registry
    async def search_from(provider, query):
        return await provider.search(query)

    vehicle_service.search_from_provider = search_from
    cached_repo = AsyncMock()
    cached_repo.get_valid = AsyncMock(return_value=None)
    cached_repo.save = AsyncMock()

    def _make_estimator() -> ComparableMarketEstimator:
        # Una instancia por escenario: el estimador cachea por vehículo y el
        # caché no distingue la allowlist de comparables.
        return ComparableMarketEstimator(
            vehicle_service=vehicle_service,
            cached_market_repository=cached_repo,
            provider_registry=ProviderRegistry,
        )
    vehicle = type(
        "V",
        (),
        {
            "brand": "BMW",
            "model": "320",
            "year": 2019,
            "mileage": 120000,
            "price": 12000.0,
            "fuel_type": "Diesel",
            "transmission": "Automatic",
            "external_id": None,
            "source": None,
        },
    )()
    try:
        # Selección automática: el fixture (simulado) queda excluido.
        auto = await _make_estimator().estimate(vehicle)
        # Petición explícita: el fixture sí se usa (desarrollo offline).
        explicit = await _make_estimator().estimate(
            vehicle, comparable_providers=["es_market_fixture"]
        )
    finally:
        ProviderRegistry.clear()

    assert auto.comparable_count == 0
    assert explicit.comparable_count >= 1
    assert any("es_market_fixture" in n for n in explicit.notes)
