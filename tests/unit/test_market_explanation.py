"""Tests para build_market_explanation y cableado de explanation en el estimador.

Cubre:
    - explicación bajo/precio justo/sobre mercado
    - sin comparables
    - cableado en estimate (explanation no vacío con comparables)
    - roundtrip caché DB sin migración (explanation embebida en notes JSON)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.cached_market import CachedMarketData
from app.services.comparable_market_estimator import (
    ComparableMarketEstimator,
    MarketStatistics,
)


def _stats(**kwargs: Any) -> MarketStatistics:
    defaults = {
        "count": 10,
        "mean": 10000.0,
        "median": 9800.0,
        "std_dev": 500.0,
        "min_price": 8000.0,
        "max_price": 12000.0,
        "q1": 9000.0,
        "q3": 11000.0,
        "iqr": 2000.0,
        "coefficient_of_variation": 0.05,
        "percentile_position": 20.0,
        "weighted_mean": 9900.0,
        "total_weight": 8.0,
    }
    defaults.update(kwargs)
    return MarketStatistics(**defaults)


@dataclass
class _VehicleStub:
    brand: str = "BMW"
    model: str = "Serie 3"
    year: int = 2020
    mileage: int = 50000
    fuel_type: str = "Diesel"
    transmission: str = "Manual"
    price: float = 20000.0
    source: str = "mobile_de"
    external_id: str = "test-123"


def test_explanation_underpriced_mentions_delta() -> None:
    text = ComparableMarketEstimator.build_market_explanation(
        target_price=8500.0,
        market_price=9900.0,
        stats=_stats(percentile_position=15.0),
        pricing="underpriced",
        provider_sources={"mobile_de", "autoscout24"},
        confidence=75.0,
        discarded_ratio=0.1,
    )
    assert "por debajo" in text.lower() or "debajo" in text.lower()
    assert "8500" in text.replace(",", "") or "8,500" in text or "8.500" in text
    assert "comparables" in text.lower()
    assert "autoscout24" in text or "mobile_de" in text or "comparables" in text.lower()


def test_explanation_no_comparables() -> None:
    text = ComparableMarketEstimator.build_market_explanation(
        target_price=10000.0,
        market_price=0.0,
        stats=_stats(
            count=0, mean=0, median=0, std_dev=0, min_price=0, max_price=0,
            q1=0, q3=0, iqr=0, coefficient_of_variation=0, percentile_position=0,
            weighted_mean=0, total_weight=0,
        ),
        pricing="fair",
        provider_sources=set(),
        confidence=0.0,
        discarded_ratio=1.0,
    )
    assert "no hay comparables" in text.lower()


def test_explanation_overpriced() -> None:
    text = ComparableMarketEstimator.build_market_explanation(
        target_price=15000.0,
        market_price=10000.0,
        stats=_stats(percentile_position=95.0, coefficient_of_variation=0.3),
        pricing="overpriced",
        provider_sources={"autoscout24"},
        confidence=55.0,
        discarded_ratio=0.2,
    )
    assert "por encima" in text.lower() or "encima" in text.lower()
    assert "dispersión" in text.lower() or "dispers" in text.lower()


def test_explanation_fair() -> None:
    text = ComparableMarketEstimator.build_market_explanation(
        target_price=10000.0,
        market_price=9900.0,
        stats=_stats(percentile_position=50.0),
        pricing="fair",
        provider_sources={"mobile_de"},
        confidence=85.0,
        discarded_ratio=0.05,
    )
    assert "alineado" in text.lower()
    assert "confianza alta" in text.lower()


@pytest.mark.asyncio
async def test_estimate_explanation_non_empty_with_comparables() -> None:
    vehicle_service = AsyncMock()
    vehicle_service.search_from_provider = AsyncMock(
        return_value=[
            _VehicleStub(price=float(15000 + i * 800), source="mobile_de", external_id=f"c{i}")
            for i in range(5)
        ]
    )
    repo = AsyncMock()
    repo.get_valid = AsyncMock(return_value=None)
    estimator = ComparableMarketEstimator(
        vehicle_service=vehicle_service,
        cached_market_repository=repo,
    )
    vehicle = _VehicleStub(price=15000.0)
    with (
        patch.object(estimator._provider_registry, "list_providers", return_value=["mobile_de"]),
        patch.object(estimator._provider_registry, "get", return_value=MagicMock()),
    ):
        result = await estimator.estimate(vehicle)

    assert result.explanation
    assert result.notes  # notas machine-readable se mantienen
    assert result.explanation != ""


def test_from_cached_roundtrip_explanation_in_column() -> None:
    """La explanation sobrevive al cache DB en columna propia (sin prefijo en notes)."""
    repo = AsyncMock()
    estimator = ComparableMarketEstimator(
        vehicle_service=AsyncMock(),
        cached_market_repository=repo,
    )
    cached = CachedMarketData(
        external_id="x",
        provider="mobile_de",
        market_hash="h",
        market_price=9900.0,
        confidence=70.0,
        comparable_count=3,
        notes='["mean=10000", "pricing=fair"]',
        explanation="El anuncio está alineado con el mercado.",
    )
    estimation = estimator._from_cached(cached)
    assert estimation.explanation == "El anuncio está alineado con el mercado."
    assert "explanation=" not in estimation.notes
    assert estimation.notes == ["mean=10000", "pricing=fair"]


def test_from_cache_payload_explanation_field() -> None:
    estimator = ComparableMarketEstimator(
        vehicle_service=AsyncMock(),
        cached_market_repository=AsyncMock(),
    )
    estimation = estimator._from_cache_payload(
        {
            "market_price": 9900.0,
            "confidence": 70.0,
            "notes": ["mean=10000"],
            "explanation": "Explicación de caché",
        }
    )
    assert estimation.explanation == "Explicación de caché"
