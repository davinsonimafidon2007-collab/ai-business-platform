"""Tests del wiring del perfil de costes en SearchOrchestrator (Task B.2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.market import MarketEstimation
from app.services.profit_analyzer import ProfitAnalyzer
from app.services.search_orchestrator import SearchOrchestrator


@dataclass
class _VehicleStub:
    price: float | None = 15000.0
    brand: str | None = "TestBrand"
    model: str | None = "TestModel"
    year: int | None = 2020
    mileage: int | None = 50000


@dataclass
class _MarketStub:
    def estimate(self, vehicle: object) -> MarketEstimation:
        return MarketEstimation(
            market_price=20000.0,
            confidence=70.0,
            supply_level=50.0,
            demand_level=60.0,
            market_trend="stable",
            comparable_count=10,
        )

    async def estimate_async(self, vehicle: object) -> MarketEstimation:
        return self.estimate(vehicle)


@dataclass
class _ScorerStub:
    def score(self, vehicle: object, *, market_price: float | None = None) -> Any:
        return MagicMock(score=75, category="Muy bueno")


@dataclass
class _OpportunityStub:
    def analyze(self, *args: Any, **kwargs: Any) -> Any:
        return MagicMock(overall_score=75.0)


def _build_orchestrator(
    profit_analyzer: ProfitAnalyzer,
    import_cost_profile: str | None = None,
) -> SearchOrchestrator:
    return SearchOrchestrator(
        vehicle_service=AsyncMock(),
        vehicle_scorer=_ScorerStub(),
        market_estimator=_MarketStub(),
        profit_analyzer=profit_analyzer,
        opportunity_finder=_OpportunityStub(),
        import_cost_profile=import_cost_profile,
    )


@pytest.mark.asyncio
async def test_orchestrator_passes_spain_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    real = ProfitAnalyzer.analyze

    def spy(self: ProfitAnalyzer, vehicle: object, profile_name: str = "DEFAULT", **kwargs: Any) -> Any:
        calls.append(profile_name)
        return real(self, vehicle, profile_name=profile_name, **kwargs)

    monkeypatch.setattr(ProfitAnalyzer, "analyze", spy)

    orchestrator = _build_orchestrator(ProfitAnalyzer(), import_cost_profile="SPAIN")
    result = await orchestrator._analyze_vehicle(_VehicleStub())

    assert result is not None
    assert "SPAIN" in calls


@pytest.mark.asyncio
async def test_orchestrator_defaults_to_settings_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    real = ProfitAnalyzer.analyze

    def spy(self: ProfitAnalyzer, vehicle: object, profile_name: str = "DEFAULT", **kwargs: Any) -> Any:
        calls.append(profile_name)
        return real(self, vehicle, profile_name=profile_name, **kwargs)

    monkeypatch.setattr(ProfitAnalyzer, "analyze", spy)

    orchestrator = _build_orchestrator(ProfitAnalyzer())
    await orchestrator._analyze_vehicle(_VehicleStub())

    assert "SPAIN" in calls
