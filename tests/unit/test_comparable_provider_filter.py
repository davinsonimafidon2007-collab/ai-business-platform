"""Tests para el filtro opcional de sources de comparables (SEARCH.PROVIDERS.1).

Cubre:
    - Sin request ni settings → todo el registry (comportamiento actual).
    - Settings CSV filtra sources del estimador.
    - Body ``comparable_providers`` tiene prioridad sobre settings.
    - Nombres desconocidos se ignoran (no 500).
    - La semántica de ``providers`` del listado NO cambia: solo afecta a
      los comparables del market estimate.
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.market import MarketEstimation
from app.services.comparable_market_estimator import (
    ComparableMarketEstimator,
    resolve_comparable_provider_names,
)

AVAILABLE = ["mobile_de", "autoscout24", "es_market_fixture"]


# =============================================================================
# Helper resolve_comparable_provider_names
# =============================================================================


def test_default_all_registry():
    """Sin request ni settings → todos los del registry."""
    assert resolve_comparable_provider_names(
        ["mobile_de", "autoscout24", "es_market_fixture"],
        request_names=None,
        settings_csv="",
    ) == ["mobile_de", "autoscout24", "es_market_fixture"]


def test_settings_csv_filters():
    """Settings CSV filtra y mantiene el orden del CSV, ignorando desconocidos."""
    assert resolve_comparable_provider_names(
        ["mobile_de", "autoscout24", "es_market_fixture"],
        request_names=None,
        settings_csv="autoscout24, es_market_fixture, unknown",
    ) == ["autoscout24", "es_market_fixture"]


def test_request_overrides_settings():
    """Body ``comparable_providers`` tiene prioridad sobre settings."""
    assert resolve_comparable_provider_names(
        ["mobile_de", "autoscout24", "es_market_fixture"],
        request_names=["mobile_de"],
        settings_csv="autoscout24",
    ) == ["mobile_de"]


def test_unknown_only_yields_empty():
    """Solo desconocidos → lista vacía (sin excepción)."""
    assert resolve_comparable_provider_names(
        ["mobile_de"],
        request_names=["nope"],
        settings_csv="",
    ) == []


def test_settings_csv_empty_string_means_all():
    """CSV vacío/None → todo el registry."""
    assert resolve_comparable_provider_names(
        AVAILABLE, request_names=None, settings_csv=None,
    ) == AVAILABLE
    assert resolve_comparable_provider_names(
        AVAILABLE, request_names=None, settings_csv="   ",
    ) == AVAILABLE


def test_request_names_with_blank_entries_ignored():
    """Entradas vacías en request se ignoran."""
    assert resolve_comparable_provider_names(
        AVAILABLE,
        request_names=["mobile_de", "", "   ", "autoscout24"],
        settings_csv="es_market_fixture",
    ) == ["mobile_de", "autoscout24"]


# =============================================================================
# Test ligero de integración del estimador con allowlist
# =============================================================================


@dataclass
class VehicleStub:
    brand: str = "BMW"
    model: str = "Serie 3"
    year: int = 2020
    mileage: int = 50000
    fuel_type: str = "Diesel"
    transmission: str = "Manual"
    price: float = 20000.0
    source: str = "mobile_de"
    external_id: str = "test-123"


class TestEstimatorAllowlist:
    @pytest.fixture
    def estimator(self) -> ComparableMarketEstimator:
        vehicle_service = AsyncMock()
        cached_repo = AsyncMock()
        cached_repo.get_valid = AsyncMock(return_value=None)
        cached_repo.save = AsyncMock()
        return ComparableMarketEstimator(
            vehicle_service=vehicle_service,
            cached_market_repository=cached_repo,
            cache_ttl_seconds=86400,
        )

    @pytest.mark.asyncio
    async def test_allowlist_limits_provider_sources(
        self, estimator: ComparableMarketEstimator
    ) -> None:
        """Con allowlist de un solo nombre, provider_sources/notes solo contienen ese source."""
        vehicle_service: AsyncMock = estimator._vehicle_service
        comparable = VehicleStub(price=18000.0, external_id="comp-1")
        vehicle_service.search_from_provider = AsyncMock(return_value=[comparable])

        vehicle = VehicleStub(price=20000.0)

        with patch.object(
            estimator._provider_registry, "list_providers",
            return_value=["mobile_de", "autoscout24"],
        ):
            with patch.object(
                estimator._provider_registry, "get",
                return_value=MagicMock(),
            ):
                result = await estimator.estimate(
                    vehicle,
                    comparable_providers=["autoscout24"],
                )

        assert isinstance(result, MarketEstimation)
        # El provider consultado es solo autoscout24
        # (vehicle_service.search_from_provider recibe el provider del registry.get)
        assert "autoscout24" in result.provider_sources
        assert "mobile_de" not in result.provider_sources
        providers_note = [n for n in result.notes if n.startswith("providers=")]
        assert providers_note
        assert "mobile_de" not in providers_note[0]

    @pytest.mark.asyncio
    async def test_no_allowlist_uses_all_registry(
        self, estimator: ComparableMarketEstimator
    ) -> None:
        """Sin request ni settings → usa todo el registry (default actual)."""
        vehicle_service: AsyncMock = estimator._vehicle_service
        vehicle_service.search_from_provider = AsyncMock(return_value=[])

        vehicle = VehicleStub(brand="RareBrand")

        with patch.object(
            estimator._provider_registry, "list_providers",
            return_value=["mobile_de", "autoscout24"],
        ):
            with patch.object(
                estimator._provider_registry, "get",
                return_value=MagicMock(),
            ):
                result = await estimator.estimate(vehicle)

        assert isinstance(result, MarketEstimation)
        assert result.comparable_count == 0

