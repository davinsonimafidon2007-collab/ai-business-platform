"""Tests de integracion para el SearchEngineService.

Verifica que el servicio principal de busqueda end-to-end.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.market import MarketEstimation
from app.models.search import (
    SearchEngineResult,
    SearchRequest,
    SearchResult,
    SearchSummary,
)
from app.providers.autoscout24 import AutoScout24Provider
from app.providers.dto import VehicleSearchResult
from app.providers.mobile_de import MobileDeProvider
from app.providers.registry import ProviderRegistry
from app.services.opportunity_finder import (
    OpportunityAnalysis,
    OpportunityFinder,
    OpportunityLevel,
    Recommendation as OppRecommendation,
)
from app.services.profit_analyzer import ProfitAnalysis, RiskLevel
from app.services.search_engine import SearchEngineService
from app.services.search_orchestrator import SearchOrchestrator
from app.services.vehicle_scorer import VehicleScore


@dataclass
class VehicleStub:
    price: float | None = 15000.0
    mileage: int | None = 50000
    year: int | None = 2020
    fuel_type: str | None = "diesel"
    transmission: str | None = "manual"
    power_hp: int | None = 120
    description: str | None = "Coche en buen estado"
    images: Any = None
    brand: str | None = "TestBrand"
    model: str | None = "TestModel"


@dataclass
class MarketEstimatorStub:
    market_price: float = 20000.0
    confidence: float = 70.0
    supply_level: float = 50.0
    demand_level: float = 60.0
    market_trend: str = "stable"
    comparable_count: int = 10

    def estimate(self, vehicle: object) -> MarketEstimation:
        return MarketEstimation(
            market_price=self.market_price,
            confidence=self.confidence,
            supply_level=self.supply_level,
            demand_level=self.demand_level,
            market_trend=self.market_trend,
            comparable_count=self.comparable_count,
        )


@dataclass
class VehicleScorerStub:
    score_value: int = 75
    category: str = "Muy bueno"

    def score(self, vehicle: object) -> VehicleScore:
        return VehicleScore(
            score=self.score_value,
            category=self.category,
            strengths=["Precio competitivo", "Bajo kilometraje"],
            weaknesses=["Sin descripcion"],
        )


@dataclass
class ProfitAnalyzerStub:
    purchase_price: float = 15000.0
    roi_percentage: float = 15.0
    net_profit: float = 3000.0
    risk_level: RiskLevel = RiskLevel.LOW
    recommendation: str = "BUY"

    def analyze(self, vehicle: object, **kwargs: Any) -> ProfitAnalysis:
        return ProfitAnalysis(
            purchase_price=self.purchase_price,
            transport_cost=500.0,
            registration_cost=300.0,
            taxes=1500.0,
            inspection_cost=100.0,
            repair_estimate=500.0,
            commission_cost=200.0,
            miscellaneous_cost=100.0,
            total_cost=self.purchase_price + 3200.0,
            estimated_sale_price=self.purchase_price * 1.4,
            gross_profit=self.purchase_price * 0.4,
            net_profit=self.net_profit,
            roi_percentage=self.roi_percentage,
            profit_margin_percentage=12.0,
            risk_level=self.risk_level,
            recommendation=self.recommendation,
            cost_breakdown=MagicMock(),
        )


@dataclass
class OpportunityFinderStub:
    overall_score: float = 75.0
    opportunity_level: OpportunityLevel = OpportunityLevel.GOOD
    recommendation: OppRecommendation = OppRecommendation.WATCH
    estimated_profit: float = 3000.0
    roi: float = 15.0
    market_confidence: float = 70.0
    risk_level: str = "LOW"

    def analyze(
        self,
        vehicle_score: object,
        profit_analysis: object,
        market_estimation: object,
    ) -> OpportunityAnalysis:
        return OpportunityAnalysis(
            overall_score=self.overall_score,
            opportunity_level=self.opportunity_level,
            recommendation=self.recommendation,
            estimated_profit=self.estimated_profit,
            roi=self.roi,
            market_confidence=self.market_confidence,
            risk_level=self.risk_level,
            strengths=["Buena oportunidad"],
            weaknesses=["Mercado incierto"],
            reasons=[],
        )


@pytest.fixture(autouse=True)
def clear_registry() -> None:
    ProviderRegistry.clear()


@pytest.fixture
def vehicle_service_mock() -> AsyncMock:
    mock = AsyncMock()
    mock.search_from_provider = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def mobile_de_provider() -> MagicMock:
    mock = MagicMock(spec=MobileDeProvider)
    mock.source_name = "mobile_de"
    return mock


@pytest.fixture
def autoscout24_provider() -> MagicMock:
    mock = MagicMock(spec=AutoScout24Provider)
    mock.source_name = "autoscout24"
    return mock


@pytest.fixture
def vehicle_scorer() -> VehicleScorerStub:
    return VehicleScorerStub()


@pytest.fixture
def market_estimator() -> MarketEstimatorStub:
    return MarketEstimatorStub()


@pytest.fixture
def profit_analyzer() -> ProfitAnalyzerStub:
    return ProfitAnalyzerStub()


@pytest.fixture
def opportunity_finder() -> OpportunityFinderStub:
    return OpportunityFinderStub()


@pytest.fixture
def search_engine(
    vehicle_service_mock: AsyncMock,
    mobile_de_provider: MagicMock,
    autoscout24_provider: MagicMock,
    vehicle_scorer: VehicleScorerStub,
    market_estimator: MarketEstimatorStub,
    profit_analyzer: ProfitAnalyzerStub,
    opportunity_finder: OpportunityFinderStub,
) -> SearchEngineService:
    return SearchEngineService(
        vehicle_service=vehicle_service_mock,
        mobile_de_provider=mobile_de_provider,
        autoscout24_provider=autoscout24_provider,
        vehicle_scorer=vehicle_scorer,
        market_estimator=market_estimator,
        profit_analyzer=profit_analyzer,
        opportunity_finder=opportunity_finder,
    )


@pytest.fixture
def sample_dto() -> VehicleSearchResult:
    return VehicleSearchResult(
        source="mobile_de",
        external_id="12345",
        url="https://example.com/vehicle/12345",
        brand="TestBrand",
        model="TestModel",
        year=2020,
        mileage=50000,
        fuel_type="diesel",
        transmission="manual",
        power_hp=120,
        price=15000.0,
        currency="EUR",
        description="Test vehicle",
        images=["img1.jpg"],
    )


@pytest.fixture
def sample_dto_expensive() -> VehicleSearchResult:
    return VehicleSearchResult(
        source="autoscout24",
        external_id="67890",
        url="https://example.com/vehicle/67890",
        brand="LuxuryBrand",
        model="LuxuryModel",
        year=2022,
        mileage=10000,
        fuel_type="electric",
        transmission="automatic",
        power_hp=300,
        price=50000.0,
        currency="EUR",
        description="Expensive vehicle",
        images=["img1.jpg", "img2.jpg"],
    )


class TestSearchEngineInitialization:

    def test_create_search_engine(
        self,
        search_engine: SearchEngineService,
    ) -> None:
        assert search_engine is not None
        assert hasattr(search_engine, "search")

    def test_providers_registered_on_init(
        self,
        vehicle_service_mock: AsyncMock,
        mobile_de_provider: MagicMock,
        autoscout24_provider: MagicMock,
        vehicle_scorer: VehicleScorerStub,
        market_estimator: MarketEstimatorStub,
        profit_analyzer: ProfitAnalyzerStub,
        opportunity_finder: OpportunityFinderStub,
    ) -> None:
        ProviderRegistry.clear()
        engine = SearchEngineService(
            vehicle_service=vehicle_service_mock,
            mobile_de_provider=mobile_de_provider,
            autoscout24_provider=autoscout24_provider,
            vehicle_scorer=vehicle_scorer,
            market_estimator=market_estimator,
            profit_analyzer=profit_analyzer,
            opportunity_finder=opportunity_finder,
        )
        providers = ProviderRegistry.list_providers()
        assert "mobile_de" in providers
        assert "autoscout24" in providers

    def test_providers_not_re_registered(
        self,
        vehicle_service_mock: AsyncMock,
        mobile_de_provider: MagicMock,
        autoscout24_provider: MagicMock,
        vehicle_scorer: VehicleScorerStub,
        market_estimator: MarketEstimatorStub,
        profit_analyzer: ProfitAnalyzerStub,
        opportunity_finder: OpportunityFinderStub,
    ) -> None:
        ProviderRegistry.clear()
        engine1 = SearchEngineService(
            vehicle_service=vehicle_service_mock,
            mobile_de_provider=mobile_de_provider,
            autoscout24_provider=autoscout24_provider,
            vehicle_scorer=vehicle_scorer,
            market_estimator=market_estimator,
            profit_analyzer=profit_analyzer,
            opportunity_finder=opportunity_finder,
        )
        providers_after_first = ProviderRegistry.list_providers()
        assert len(providers_after_first) == 2

        engine2 = SearchEngineService(
            vehicle_service=vehicle_service_mock,
            mobile_de_provider=mobile_de_provider,
            autoscout24_provider=autoscout24_provider,
            vehicle_scorer=vehicle_scorer,
            market_estimator=market_estimator,
            profit_analyzer=profit_analyzer,
            opportunity_finder=opportunity_finder,
        )
        providers_after_second = ProviderRegistry.list_providers()
        assert len(providers_after_second) == 2

    def test_dependency_injection(
        self,
        search_engine: SearchEngineService,
        vehicle_service_mock: AsyncMock,
        mobile_de_provider: MagicMock,
        autoscout24_provider: MagicMock,
        vehicle_scorer: VehicleScorerStub,
        market_estimator: MarketEstimatorStub,
        profit_analyzer: ProfitAnalyzerStub,
        opportunity_finder: OpportunityFinderStub,
    ) -> None:
        assert search_engine._vehicle_service is vehicle_service_mock
        assert search_engine._mobile_de_provider is mobile_de_provider
        assert search_engine._autoscout24_provider is autoscout24_provider
        assert search_engine._vehicle_scorer is vehicle_scorer
        assert search_engine._market_estimator is market_estimator
        assert search_engine._profit_analyzer is profit_analyzer
        assert search_engine._opportunity_finder is opportunity_finder

    def test_orchestrator_created_by_default(
        self,
        search_engine: SearchEngineService,
    ) -> None:
        assert hasattr(search_engine, "_orchestrator")
        assert isinstance(search_engine._orchestrator, SearchOrchestrator)


class TestSearchEngineSearch:

    @pytest.mark.asyncio
    async def test_search_returns_search_engine_result(
        self,
        search_engine: SearchEngineService,
        vehicle_service_mock: AsyncMock,
        sample_dto: VehicleSearchResult,
    ) -> None:
        vehicle_service_mock.search_from_provider.return_value = [sample_dto]
        request = SearchRequest(query="BMW", max_results=10, providers=["mobile_de"])
        with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
            result = await search_engine.search(request)
        assert isinstance(result, SearchEngineResult)
        assert isinstance(result.summary, SearchSummary)
        assert isinstance(result.results, list)

    @pytest.mark.asyncio
    async def test_search_returns_summary(
        self,
        search_engine: SearchEngineService,
        vehicle_service_mock: AsyncMock,
        sample_dto: VehicleSearchResult,
    ) -> None:
        vehicle_service_mock.search_from_provider.return_value = [sample_dto]
        request = SearchRequest(query="BMW", max_results=10, providers=["mobile_de"])
        with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
            result = await search_engine.search(request)
        assert result.summary.total_results == 1
        assert result.summary.total_results == len(result.results)

    @pytest.mark.asyncio
    async def test_search_returns_analyzed_results(
        self,
        search_engine: SearchEngineService,
        vehicle_service_mock: AsyncMock,
        sample_dto: VehicleSearchResult,
    ) -> None:
        vehicle_service_mock.search_from_provider.return_value = [sample_dto]
        request = SearchRequest(query="BMW", max_results=10, providers=["mobile_de"])
        with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
            result = await search_engine.search(request)
        assert len(result.results) == 1
        sr = result.results[0]
        assert sr.vehicle is not None
        assert sr.vehicle_score is not None
        assert sr.market_estimation is not None
        assert sr.profit_analysis is not None
        assert sr.opportunity is not None

    @pytest.mark.asyncio
    async def test_both_providers_queried(
        self,
        search_engine: SearchEngineService,
        vehicle_service_mock: AsyncMock,
        sample_dto: VehicleSearchResult,
    ) -> None:
        vehicle_service_mock.search_from_provider.return_value = [sample_dto]
        request = SearchRequest(
            query="BMW", max_results=20, providers=["mobile_de", "autoscout24"],
        )
        providers = {"mobile_de": MagicMock(), "autoscout24": MagicMock()}
        with patch.object(ProviderRegistry, "get", side_effect=lambda name: providers[name]):
            result = await search_engine.search(request)
        assert vehicle_service_mock.search_from_provider.call_count == 2
        assert len(result.results) == 2

    @pytest.mark.asyncio
    async def test_full_pipeline_executed(
        self,
        sample_dto: VehicleSearchResult,
    ) -> None:
        vehicle_service = AsyncMock()
        vehicle_service.search_from_provider = AsyncMock(return_value=[sample_dto])
        scorer = MagicMock()
        scorer.score.return_value = VehicleScore(score=75, category="Muy bueno")
        estimator = MagicMock()
        estimator.estimate.return_value = MarketEstimation(market_price=20000.0, confidence=70.0)
        analyzer = MagicMock()
        analyzer.analyze.return_value = MagicMock(
            purchase_price=15000.0, net_profit=3000.0, roi_percentage=15.0,
            risk_level=RiskLevel.LOW, recommendation="BUY",
        )
        finder = MagicMock()
        finder.analyze.return_value = OpportunityAnalysis(
            overall_score=75.0, opportunity_level=OpportunityLevel.GOOD,
            recommendation=OppRecommendation.WATCH, estimated_profit=3000.0,
            roi=15.0, market_confidence=70.0, risk_level="LOW",
        )
        engine = SearchEngineService(
            vehicle_service=vehicle_service,
            mobile_de_provider=MagicMock(spec=MobileDeProvider, source_name="mobile_de"),
            autoscout24_provider=MagicMock(spec=AutoScout24Provider, source_name="autoscout24"),
            vehicle_scorer=scorer, market_estimator=estimator,
            profit_analyzer=analyzer, opportunity_finder=finder,
        )
        request = SearchRequest(query="BMW", max_results=10, providers=["mobile_de"])
        with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
            result = await engine.search(request)
        scorer.score.assert_called_once()
        estimator.estimate.assert_called_once()
        analyzer.analyze.assert_called_once()
        finder.analyze.assert_called_once()
        assert len(result.results) == 1

    @pytest.mark.asyncio
    async def test_provider_failure_does_not_stop_search(
        self,
        search_engine: SearchEngineService,
        vehicle_service_mock: AsyncMock,
    ) -> None:
        vehicle_service_mock.search_from_provider.side_effect = Exception("Provider error")
        request = SearchRequest(query="BMW", max_results=10, providers=["mobile_de"])
        with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
            result = await search_engine.search(request)
        assert isinstance(result, SearchEngineResult)
        assert result.summary.total_results == 0
        assert len(result.results) == 0

    @pytest.mark.asyncio
    async def test_deterministic_output(
        self,
        search_engine: SearchEngineService,
        vehicle_service_mock: AsyncMock,
        sample_dto: VehicleSearchResult,
    ) -> None:
        vehicle_service_mock.search_from_provider.return_value = [sample_dto]
        request = SearchRequest(query="BMW", max_results=10, providers=["mobile_de"])
        with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
            result1 = await search_engine.search(request)
            result2 = await search_engine.search(request)
        assert result1.summary.total_results == result2.summary.total_results
        assert len(result1.results) == len(result2.results)
        for r1, r2 in zip(result1.results, result2.results):
            assert r1.opportunity.overall_score == r2.opportunity.overall_score
            assert r1.opportunity.opportunity_level == r2.opportunity.opportunity_level

    @pytest.mark.asyncio
    async def test_empty_search(
        self,
        search_engine: SearchEngineService,
        vehicle_service_mock: AsyncMock,
    ) -> None:
        vehicle_service_mock.search_from_provider.return_value = []
        request = SearchRequest(query="ZZZZZ", max_results=10, providers=["mobile_de"])
        with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
            result = await search_engine.search(request)
        assert result.summary.total_results == 0
        assert len(result.results) == 0

    @pytest.mark.asyncio
    async def test_search_with_no_providers(
        self,
        search_engine: SearchEngineService,
    ) -> None:
        request = SearchRequest(query="BMW", max_results=10, providers=[])
        result = await search_engine.search(request)
        assert result.summary.total_results == 0
        assert len(result.results) == 0

    @pytest.mark.asyncio
    async def test_search_with_custom_orchestrator(
        self,
        vehicle_service_mock: AsyncMock,
        mobile_de_provider: MagicMock,
        autoscout24_provider: MagicMock,
        vehicle_scorer: VehicleScorerStub,
        market_estimator: MarketEstimatorStub,
        profit_analyzer: ProfitAnalyzerStub,
        opportunity_finder: OpportunityFinderStub,
        sample_dto: VehicleSearchResult,
    ) -> None:
        orchestrator = SearchOrchestrator(
            vehicle_service=vehicle_service_mock, vehicle_scorer=vehicle_scorer,
            market_estimator=market_estimator, profit_analyzer=profit_analyzer,
            opportunity_finder=opportunity_finder,
        )
        engine = SearchEngineService(
            vehicle_service=vehicle_service_mock,
            mobile_de_provider=mobile_de_provider,
            autoscout24_provider=autoscout24_provider,
            vehicle_scorer=vehicle_scorer, market_estimator=market_estimator,
            profit_analyzer=profit_analyzer, opportunity_finder=opportunity_finder,
            orchestrator=orchestrator,
        )
        assert engine._orchestrator is orchestrator
        vehicle_service_mock.search_from_provider.return_value = [sample_dto]
        request = SearchRequest(query="BMW", max_results=10, providers=["mobile_de"])
        with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
            result = await engine.search(request)
        assert result.summary.total_results == 1

    @pytest.mark.asyncio
    async def test_search_with_budget_filter(
        self,
        search_engine: SearchEngineService,
        vehicle_service_mock: AsyncMock,
        sample_dto: VehicleSearchResult,
    ) -> None:
        sample_dto.price = 50000.0
        vehicle_service_mock.search_from_provider.return_value = [sample_dto]
        request = SearchRequest(query="BMW", max_results=10, budget_max=30000.0, providers=["mobile_de"])
        with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
            result = await search_engine.search(request)
        assert result.summary.total_results == 0

    @pytest.mark.asyncio
    async def test_search_with_budget_range(
        self,
        search_engine: SearchEngineService,
        vehicle_service_mock: AsyncMock,
        sample_dto: VehicleSearchResult,
    ) -> None:
        sample_dto.price = 15000.0
        vehicle_service_mock.search_from_provider.return_value = [sample_dto]
        request = SearchRequest(query="BMW", max_results=10, budget_min=10000.0, budget_max=20000.0, providers=["mobile_de"])
        with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
            result = await search_engine.search(request)
        assert result.summary.total_results == 1
        assert len(result.results) == 1
