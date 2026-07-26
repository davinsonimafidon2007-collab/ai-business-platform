"""Tests para el SearchOrchestrator — Coordinador del flujo de búsqueda.

Casos mínimos requeridos:
    - búsqueda vacía
    - búsqueda con resultados
    - providers múltiples
    - orden correcto
    - top()
    - filter()
    - summarize()
    - determinismo
    - integración con mocks
    - edge cases
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.market import MarketEstimation
from app.models.search import SearchRequest, SearchResult, SearchSummary
from app.providers.dto import VehicleSearchResult
from app.providers.registry import ProviderRegistry
from app.services.opportunity_finder import (
    OpportunityAnalysis,
    OpportunityFinder,
    OpportunityLevel,
    Recommendation as OppRecommendation,
)
from app.services.profit_analyzer import ProfitAnalysis, RiskLevel
from app.services.search_orchestrator import SearchOrchestrator
from app.services.vehicle_scorer import VehicleScore


# =============================================================================
# Stubs
# =============================================================================


@dataclass
class VehicleStub:
    """Stub mínimo que cumple VehicleData para los analizadores."""
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
    """Stub del MarketEstimator para pruebas."""
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
    """Stub del VehicleScorer para pruebas."""
    score_value: int = 75
    category: str = "Muy bueno"

    def score(self, vehicle: object) -> VehicleScore:
        return VehicleScore(
            score=self.score_value,
            category=self.category,
            strengths=["Precio competitivo", "Bajo kilometraje"],
            weaknesses=["Sin descripción"],
        )


@dataclass
class ProfitAnalyzerStub:
    """Stub del ProfitAnalyzer para pruebas."""
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
    """Stub del OpportunityFinder para pruebas."""
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


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def vehicle_service_mock() -> AsyncMock:
    """Mock del VehicleService."""
    mock = AsyncMock()
    mock.search_from_provider = AsyncMock()
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
def orchestrator(
    vehicle_service_mock: AsyncMock,
    vehicle_scorer: VehicleScorerStub,
    market_estimator: MarketEstimatorStub,
    profit_analyzer: ProfitAnalyzerStub,
    opportunity_finder: OpportunityFinderStub,
) -> SearchOrchestrator:
    return SearchOrchestrator(
        vehicle_service=vehicle_service_mock,
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


# =============================================================================
# Tests de estructura de modelos
# =============================================================================


class TestModelStructure:
    """Verifica que las estructuras de datos son correctas."""

    def test_search_request_defaults(self) -> None:
        request = SearchRequest(query="test")
        assert request.query == "test"
        assert request.max_results == 20
        assert request.providers == ["mobile_de", "autoscout24"]
        assert request.country == "ES"
        assert request.budget_min is None
        assert request.budget_max is None

    def test_search_request_custom_values(self) -> None:
        request = SearchRequest(
            query="BMW",
            max_results=10,
            providers=["mobile_de"],
            country="DE",
            budget_min=5000,
            budget_max=30000,
        )
        assert request.query == "BMW"
        assert request.max_results == 10
        assert request.providers == ["mobile_de"]
        assert request.country == "DE"
        assert request.budget_min == 5000
        assert request.budget_max == 30000

    def test_search_request_validation(self) -> None:
        with pytest.raises(Exception):
            SearchRequest(query="", max_results=0)

    def test_search_result_creation(self) -> None:
        result = SearchResult(
            vehicle="vehicle_dto",
            vehicle_score="score",
            market_estimation="market",
            profit_analysis="profit",
            opportunity="opportunity",
        )
        assert result.vehicle == "vehicle_dto"
        assert result.vehicle_score == "score"
        assert result.market_estimation == "market"
        assert result.profit_analysis == "profit"
        assert result.opportunity == "opportunity"

    def test_search_summary_defaults(self) -> None:
        summary = SearchSummary()
        assert summary.total_results == 0
        assert summary.excellent == 0
        assert summary.good == 0
        assert summary.average == 0
        assert summary.poor == 0
        assert summary.rejected == 0

    def test_search_summary_custom(self) -> None:
        summary = SearchSummary(
            total_results=10,
            excellent=2,
            good=3,
            average=2,
            poor=1,
            rejected=2,
        )
        assert summary.total_results == 10
        assert summary.excellent == 2
        assert summary.good == 3
        assert summary.average == 2
        assert summary.poor == 1
        assert summary.rejected == 2


# =============================================================================
# Tests de instanciación
# =============================================================================


class TestOrchestratorInstantiation:
    """Verifica que el orquestador se instancia correctamente."""

    def test_create_orchestrator(
        self,
        vehicle_service_mock: AsyncMock,
        vehicle_scorer: VehicleScorerStub,
        market_estimator: MarketEstimatorStub,
        profit_analyzer: ProfitAnalyzerStub,
        opportunity_finder: OpportunityFinderStub,
    ) -> None:
        orchestrator = SearchOrchestrator(
            vehicle_service=vehicle_service_mock,
            vehicle_scorer=vehicle_scorer,
            market_estimator=market_estimator,
            profit_analyzer=profit_analyzer,
            opportunity_finder=opportunity_finder,
        )
        assert orchestrator is not None
        assert hasattr(orchestrator, "search")
        assert hasattr(orchestrator, "summarize")
        assert hasattr(orchestrator, "top")
        assert hasattr(orchestrator, "filter")
        assert hasattr(orchestrator, "sort")

    def test_orchestrator_uses_dependency_injection(
        self,
        vehicle_service_mock: AsyncMock,
        vehicle_scorer: VehicleScorerStub,
        market_estimator: MarketEstimatorStub,
        profit_analyzer: ProfitAnalyzerStub,
        opportunity_finder: OpportunityFinderStub,
    ) -> None:
        orchestrator = SearchOrchestrator(
            vehicle_service=vehicle_service_mock,
            vehicle_scorer=vehicle_scorer,
            market_estimator=market_estimator,
            profit_analyzer=profit_analyzer,
            opportunity_finder=opportunity_finder,
        )
        # Verificar que no instancia nada internamente
        assert orchestrator._vehicle_service is vehicle_service_mock
        assert orchestrator._vehicle_scorer is vehicle_scorer
        assert orchestrator._market_estimator is market_estimator
        assert orchestrator._profit_analyzer is profit_analyzer
        assert orchestrator._opportunity_finder is opportunity_finder


# =============================================================================
# Tests de búsqueda vacía
# =============================================================================


class TestEmptySearch:
    """Búsqueda sin resultados."""

    @pytest.mark.asyncio
    async def test_empty_search(
        self,
        orchestrator: SearchOrchestrator,
        vehicle_service_mock: AsyncMock,
    ) -> None:
        vehicle_service_mock.search_from_provider.return_value = []
        request = SearchRequest(query="ZZZZZ", max_results=10, providers=["mobile_de"])

        with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
            results = await orchestrator.search(request)

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_empty_search_summary(
        self,
        orchestrator: SearchOrchestrator,
        vehicle_service_mock: AsyncMock,
    ) -> None:
        vehicle_service_mock.search_from_provider.return_value = []
        request = SearchRequest(query="ZZZZZ", providers=["mobile_de"])

        with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
            results = await orchestrator.search(request)

        summary = orchestrator.summarize(results)
        assert summary.total_results == 0
        assert summary.excellent == 0
        assert summary.good == 0
        assert summary.average == 0
        assert summary.poor == 0
        assert summary.rejected == 0

    @pytest.mark.asyncio
    async def test_empty_search_top_returns_empty(
        self,
        orchestrator: SearchOrchestrator,
        vehicle_service_mock: AsyncMock,
    ) -> None:
        vehicle_service_mock.search_from_provider.return_value = []
        request = SearchRequest(query="ZZZZZ", providers=["mobile_de"])

        with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
            results = await orchestrator.search(request)

        top_results = orchestrator.top(results)
        assert len(top_results) == 0


# =============================================================================
# Tests de búsqueda con resultados
# =============================================================================


class TestSearchWithResults:
    """Búsqueda con resultados."""

    @pytest.mark.asyncio
    async def test_search_single_result(
        self,
        orchestrator: SearchOrchestrator,
        vehicle_service_mock: AsyncMock,
        sample_dto: VehicleSearchResult,
    ) -> None:
        vehicle_service_mock.search_from_provider.return_value = [sample_dto]

        request = SearchRequest(query="BMW", max_results=10, providers=["mobile_de"])

        with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
            results = await orchestrator.search(request)

        assert len(results) == 1
        assert results[0].vehicle is sample_dto
        assert results[0].vehicle_score is not None
        assert results[0].market_estimation is not None
        assert results[0].profit_analysis is not None
        assert results[0].opportunity is not None

    @pytest.mark.asyncio
    async def test_search_multiple_results(
        self,
        orchestrator: SearchOrchestrator,
        vehicle_service_mock: AsyncMock,
        sample_dto: VehicleSearchResult,
        sample_dto_expensive: VehicleSearchResult,
    ) -> None:
        vehicle_service_mock.search_from_provider.return_value = [
            sample_dto,
            sample_dto_expensive,
        ]

        request = SearchRequest(query="BMW", max_results=10, providers=["mobile_de"])

        with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
            results = await orchestrator.search(request)

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_max_results_limit(
        self,
        orchestrator: SearchOrchestrator,
        vehicle_service_mock: AsyncMock,
        sample_dto: VehicleSearchResult,
    ) -> None:
        vehicle_service_mock.search_from_provider.return_value = [
            sample_dto,
            sample_dto,
            sample_dto,
            sample_dto,
            sample_dto,
        ]

        request = SearchRequest(query="BMW", max_results=3, providers=["mobile_de"])

        with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
            results = await orchestrator.search(request)

        assert len(results) <= 3


# =============================================================================
# Tests de providers múltiples
# =============================================================================


class TestMultipleProviders:
    """Búsqueda con múltiples providers."""

    @pytest.mark.asyncio
    async def test_multiple_providers(
        self,
        orchestrator: SearchOrchestrator,
        vehicle_service_mock: AsyncMock,
        sample_dto: VehicleSearchResult,
    ) -> None:
        vehicle_service_mock.search_from_provider.return_value = [sample_dto]

        request = SearchRequest(
            query="BMW",
            max_results=20,
            providers=["mobile_de", "autoscout24"],
        )

        providers = {
            "mobile_de": MagicMock(),
            "autoscout24": MagicMock(),
        }

        with patch.object(ProviderRegistry, "get", side_effect=lambda name: providers[name]):
            results = await orchestrator.search(request)

        assert len(results) == 2  # 1 from each provider
        assert vehicle_service_mock.search_from_provider.call_count == 2

    @pytest.mark.asyncio
    async def test_provider_not_found_skipped(
        self,
        orchestrator: SearchOrchestrator,
        vehicle_service_mock: AsyncMock,
        sample_dto: VehicleSearchResult,
    ) -> None:
        vehicle_service_mock.search_from_provider.return_value = [sample_dto]

        request = SearchRequest(
            query="BMW",
            max_results=20,
            providers=["nonexistent_provider"],
        )

        with patch.object(ProviderRegistry, "get", side_effect=KeyError("not found")):
            results = await orchestrator.search(request)

        assert len(results) == 0
        vehicle_service_mock.search_from_provider.assert_not_called()


# =============================================================================
# Tests de orden correcto
# =============================================================================


class TestSorting:
    """Verifica el ordenamiento correcto de los resultados."""

    def test_default_sort_by_score_desc(self) -> None:
        """Orden por defecto: opportunity score DESC."""
        r1 = SearchResult(
            vehicle="v1",
            vehicle_score=VehicleScore(score=80, category="Excelente"),
            market_estimation=MagicMock(),
            profit_analysis=MagicMock(roi_percentage=10.0, net_profit=1000.0),
            opportunity=OpportunityAnalysis(
                overall_score=90.0,
                opportunity_level=OpportunityLevel.EXCELLENT,
                recommendation=OppRecommendation.BUY_NOW,
                estimated_profit=1000.0,
                roi=10.0,
                market_confidence=70.0,
                risk_level="LOW",
            ),
        )
        r2 = SearchResult(
            vehicle="v2",
            vehicle_score=VehicleScore(score=60, category="Bueno"),
            market_estimation=MagicMock(),
            profit_analysis=MagicMock(roi_percentage=5.0, net_profit=500.0),
            opportunity=OpportunityAnalysis(
                overall_score=50.0,
                opportunity_level=OpportunityLevel.AVERAGE,
                recommendation=OppRecommendation.WATCH,
                estimated_profit=500.0,
                roi=5.0,
                market_confidence=50.0,
                risk_level="MEDIUM",
            ),
        )

        sorted_results = SearchOrchestrator.sort([r2, r1])
        assert sorted_results[0].opportunity.overall_score == 90.0
        assert sorted_results[1].opportunity.overall_score == 50.0

    def test_sort_by_roi(self) -> None:
        r1 = SearchResult(
            vehicle="v1",
            vehicle_score=MagicMock(score=70),
            market_estimation=MagicMock(),
            profit_analysis=MagicMock(roi_percentage=20.0, net_profit=2000.0),
            opportunity=MagicMock(overall_score=75.0),
        )
        r2 = SearchResult(
            vehicle="v2",
            vehicle_score=MagicMock(score=70),
            market_estimation=MagicMock(),
            profit_analysis=MagicMock(roi_percentage=10.0, net_profit=1000.0),
            opportunity=MagicMock(overall_score=75.0),
        )

        sorted_results = SearchOrchestrator.sort([r2, r1], by="ROI")
        assert sorted_results[0].profit_analysis.roi_percentage == 20.0
        assert sorted_results[1].profit_analysis.roi_percentage == 10.0

    def test_sort_by_ascending(self) -> None:
        r1 = SearchResult(
            vehicle="v1",
            vehicle_score=MagicMock(score=70),
            market_estimation=MagicMock(),
            profit_analysis=MagicMock(roi_percentage=10.0, net_profit=1000.0),
            opportunity=MagicMock(overall_score=90.0),
        )
        r2 = SearchResult(
            vehicle="v2",
            vehicle_score=MagicMock(score=70),
            market_estimation=MagicMock(),
            profit_analysis=MagicMock(roi_percentage=10.0, net_profit=1000.0),
            opportunity=MagicMock(overall_score=50.0),
        )

        sorted_results = SearchOrchestrator.sort([r2, r1], reverse=False)
        assert sorted_results[0].opportunity.overall_score == 50.0
        assert sorted_results[1].opportunity.overall_score == 90.0

    def test_sort_deterministic(self) -> None:
        """Mismos datos deben producir mismo orden."""
        r1 = SearchResult(
            vehicle="v1",
            vehicle_score=MagicMock(score=70),
            market_estimation=MagicMock(),
            profit_analysis=MagicMock(roi_percentage=10.0, net_profit=1000.0),
            opportunity=MagicMock(overall_score=75.0),
        )
        r2 = SearchResult(
            vehicle="v2",
            vehicle_score=MagicMock(score=70),
            market_estimation=MagicMock(),
            profit_analysis=MagicMock(roi_percentage=10.0, net_profit=1000.0),
            opportunity=MagicMock(overall_score=75.0),
        )

        s1 = SearchOrchestrator.sort([r2, r1])
        s2 = SearchOrchestrator.sort([r2, r1])
        assert s1[0].vehicle == s2[0].vehicle
        assert s1[1].vehicle == s2[1].vehicle


# =============================================================================
# Tests de top()
# =============================================================================


class TestTop:
    """Verifica el método top()."""

    def test_top_returns_n_results(self) -> None:
        results = [
            SearchResult(
                vehicle=f"v{i}",
                vehicle_score=MagicMock(),
                market_estimation=MagicMock(),
                profit_analysis=MagicMock(),
                opportunity=MagicMock(overall_score=float(100 - i)),
            )
            for i in range(20)
        ]

        top_results = SearchOrchestrator.top(results, n=5)
        assert len(top_results) == 5

    def test_top_with_default_n(self) -> None:
        results = [
            SearchResult(
                vehicle=f"v{i}",
                vehicle_score=MagicMock(),
                market_estimation=MagicMock(),
                profit_analysis=MagicMock(),
                opportunity=MagicMock(overall_score=float(100 - i)),
            )
            for i in range(5)
        ]

        top_results = SearchOrchestrator.top(results)
        assert len(top_results) == 5  # n=10, but only 5 available

    def test_top_returns_first_n(self) -> None:
        results = [
            SearchResult(
                vehicle=f"v{i}",
                vehicle_score=MagicMock(),
                market_estimation=MagicMock(),
                profit_analysis=MagicMock(),
                opportunity=MagicMock(overall_score=float(100 - i)),
            )
            for i in range(5)
        ]

        top_results = SearchOrchestrator.top(results, n=3)
        assert top_results[0].vehicle == "v0"
        assert top_results[1].vehicle == "v1"
        assert top_results[2].vehicle == "v2"

    def test_top_empty_list(self) -> None:
        top_results = SearchOrchestrator.top([], n=5)
        assert len(top_results) == 0


# =============================================================================
# Tests de filter()
# =============================================================================


class TestFilter:
    """Verifica el método filter()."""

    @pytest.fixture
    def filter_results(self) -> list[SearchResult]:
        """Crea resultados variados para pruebas de filtro."""
        return [
            SearchResult(
                vehicle="v1",
                vehicle_score=MagicMock(),
                market_estimation=MagicMock(),
                profit_analysis=MagicMock(risk_level=RiskLevel.LOW),
                opportunity=OpportunityAnalysis(
                    overall_score=90.0,
                    opportunity_level=OpportunityLevel.EXCELLENT,
                    recommendation=OppRecommendation.BUY_NOW,
                    estimated_profit=5000.0,
                    roi=25.0,
                    market_confidence=80.0,
                    risk_level="LOW",
                ),
            ),
            SearchResult(
                vehicle="v2",
                vehicle_score=MagicMock(),
                market_estimation=MagicMock(),
                profit_analysis=MagicMock(risk_level=RiskLevel.MEDIUM),
                opportunity=OpportunityAnalysis(
                    overall_score=60.0,
                    opportunity_level=OpportunityLevel.AVERAGE,
                    recommendation=OppRecommendation.WATCH,
                    estimated_profit=1000.0,
                    roi=10.0,
                    market_confidence=50.0,
                    risk_level="MEDIUM",
                ),
            ),
            SearchResult(
                vehicle="v3",
                vehicle_score=MagicMock(),
                market_estimation=MagicMock(),
                profit_analysis=MagicMock(risk_level=RiskLevel.HIGH),
                opportunity=OpportunityAnalysis(
                    overall_score=20.0,
                    opportunity_level=OpportunityLevel.REJECT,
                    recommendation=OppRecommendation.REJECT,
                    estimated_profit=-500.0,
                    roi=-5.0,
                    market_confidence=20.0,
                    risk_level="HIGH",
                ),
            ),
        ]

    def test_filter_by_recommendation(
        self, filter_results: list[SearchResult]
    ) -> None:
        filtered = SearchOrchestrator.filter(
            filter_results, recommendation="BUY_NOW"
        )
        assert len(filtered) == 1
        assert filtered[0].vehicle == "v1"

    def test_filter_by_opportunity_level(
        self, filter_results: list[SearchResult]
    ) -> None:
        filtered = SearchOrchestrator.filter(
            filter_results, opportunity_level="REJECT"
        )
        assert len(filtered) == 1
        assert filtered[0].vehicle == "v3"

    def test_filter_by_risk_level(
        self, filter_results: list[SearchResult]
    ) -> None:
        filtered = SearchOrchestrator.filter(
            filter_results, risk_level="MEDIUM"
        )
        assert len(filtered) == 1
        assert filtered[0].vehicle == "v2"

    def test_filter_combined(
        self, filter_results: list[SearchResult]
    ) -> None:
        filtered = SearchOrchestrator.filter(
            filter_results,
            recommendation="BUY_NOW",
            opportunity_level="EXCELLENT",
            risk_level="LOW",
        )
        assert len(filtered) == 1
        assert filtered[0].vehicle == "v1"

    def test_filter_no_match(
        self, filter_results: list[SearchResult]
    ) -> None:
        filtered = SearchOrchestrator.filter(
            filter_results, recommendation="NEGOTIATE"
        )
        assert len(filtered) == 0

    def test_filter_no_criteria(
        self, filter_results: list[SearchResult]
    ) -> None:
        filtered = SearchOrchestrator.filter(filter_results)
        assert len(filtered) == 3

    def test_filter_empty_list(self) -> None:
        filtered = SearchOrchestrator.filter(
            [], recommendation="BUY_NOW"
        )
        assert len(filtered) == 0


# =============================================================================
# Tests de summarize()
# =============================================================================


class TestSummarize:
    """Verifica el método summarize()."""

    def test_summarize_mixed_results(self) -> None:
        results = [
            SearchResult(
                vehicle="v1",
                vehicle_score=MagicMock(),
                market_estimation=MagicMock(),
                profit_analysis=MagicMock(),
                opportunity=OpportunityAnalysis(
                    overall_score=95.0,
                    opportunity_level=OpportunityLevel.EXCELLENT,
                    recommendation=OppRecommendation.BUY_NOW,
                    estimated_profit=5000.0,
                    roi=25.0,
                    market_confidence=80.0,
                    risk_level="LOW",
                ),
            ),
            SearchResult(
                vehicle="v2",
                vehicle_score=MagicMock(),
                market_estimation=MagicMock(),
                profit_analysis=MagicMock(),
                opportunity=OpportunityAnalysis(
                    overall_score=75.0,
                    opportunity_level=OpportunityLevel.GOOD,
                    recommendation=OppRecommendation.WATCH,
                    estimated_profit=2000.0,
                    roi=12.0,
                    market_confidence=60.0,
                    risk_level="LOW",
                ),
            ),
            SearchResult(
                vehicle="v3",
                vehicle_score=MagicMock(),
                market_estimation=MagicMock(),
                profit_analysis=MagicMock(),
                opportunity=OpportunityAnalysis(
                    overall_score=55.0,
                    opportunity_level=OpportunityLevel.AVERAGE,
                    recommendation=OppRecommendation.WATCH,
                    estimated_profit=500.0,
                    roi=5.0,
                    market_confidence=40.0,
                    risk_level="MEDIUM",
                ),
            ),
            SearchResult(
                vehicle="v4",
                vehicle_score=MagicMock(),
                market_estimation=MagicMock(),
                profit_analysis=MagicMock(),
                opportunity=OpportunityAnalysis(
                    overall_score=35.0,
                    opportunity_level=OpportunityLevel.POOR,
                    recommendation=OppRecommendation.REJECT,
                    estimated_profit=100.0,
                    roi=1.0,
                    market_confidence=30.0,
                    risk_level="HIGH",
                ),
            ),
            SearchResult(
                vehicle="v5",
                vehicle_score=MagicMock(),
                market_estimation=MagicMock(),
                profit_analysis=MagicMock(),
                opportunity=OpportunityAnalysis(
                    overall_score=10.0,
                    opportunity_level=OpportunityLevel.REJECT,
                    recommendation=OppRecommendation.REJECT,
                    estimated_profit=-1000.0,
                    roi=-10.0,
                    market_confidence=10.0,
                    risk_level="HIGH",
                ),
            ),
        ]

        summary = SearchOrchestrator.summarize(results)
        assert summary.total_results == 5
        assert summary.excellent == 1
        assert summary.good == 1
        assert summary.average == 1
        assert summary.poor == 1
        assert summary.rejected == 1

    def test_summarize_empty(self) -> None:
        summary = SearchOrchestrator.summarize([])
        assert summary.total_results == 0
        assert summary.excellent == 0
        assert summary.good == 0
        assert summary.average == 0
        assert summary.poor == 0
        assert summary.rejected == 0

    def test_summarize_all_excellent(self) -> None:
        results = [
            SearchResult(
                vehicle=f"v{i}",
                vehicle_score=MagicMock(),
                market_estimation=MagicMock(),
                profit_analysis=MagicMock(),
                opportunity=OpportunityAnalysis(
                    overall_score=95.0,
                    opportunity_level=OpportunityLevel.EXCELLENT,
                    recommendation=OppRecommendation.BUY_NOW,
                    estimated_profit=5000.0,
                    roi=25.0,
                    market_confidence=80.0,
                    risk_level="LOW",
                ),
            )
            for i in range(5)
        ]

        summary = SearchOrchestrator.summarize(results)
        assert summary.total_results == 5
        assert summary.excellent == 5
        assert summary.good == 0
        assert summary.average == 0
        assert summary.poor == 0
        assert summary.rejected == 0

    def test_summarize_all_rejected(self) -> None:
        results = [
            SearchResult(
                vehicle=f"v{i}",
                vehicle_score=MagicMock(),
                market_estimation=MagicMock(),
                profit_analysis=MagicMock(),
                opportunity=OpportunityAnalysis(
                    overall_score=10.0,
                    opportunity_level=OpportunityLevel.REJECT,
                    recommendation=OppRecommendation.REJECT,
                    estimated_profit=-1000.0,
                    roi=-10.0,
                    market_confidence=10.0,
                    risk_level="HIGH",
                ),
            )
            for i in range(3)
        ]

        summary = SearchOrchestrator.summarize(results)
        assert summary.total_results == 3
        assert summary.rejected == 3


# =============================================================================
# Tests de determinismo
# =============================================================================


class TestDeterminism:
    """El orquestador debe ser determinista."""

    @pytest.mark.asyncio
    async def test_deterministic_search(
        self,
        orchestrator: SearchOrchestrator,
        vehicle_service_mock: AsyncMock,
        sample_dto: VehicleSearchResult,
    ) -> None:
        vehicle_service_mock.search_from_provider.return_value = [sample_dto]

        request = SearchRequest(query="BMW", max_results=10, providers=["mobile_de"])

        with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
            results1 = await orchestrator.search(request)
            results2 = await orchestrator.search(request)

        assert len(results1) == len(results2)
        for r1, r2 in zip(results1, results2):
            assert r1.opportunity.overall_score == r2.opportunity.overall_score
            assert r1.opportunity.opportunity_level == r2.opportunity.opportunity_level

    def test_deterministic_summarize(self) -> None:
        results = [
            SearchResult(
                vehicle="v1",
                vehicle_score=MagicMock(),
                market_estimation=MagicMock(),
                profit_analysis=MagicMock(),
                opportunity=OpportunityAnalysis(
                    overall_score=80.0,
                    opportunity_level=OpportunityLevel.GOOD,
                    recommendation=OppRecommendation.WATCH,
                    estimated_profit=2000.0,
                    roi=12.0,
                    market_confidence=60.0,
                    risk_level="LOW",
                ),
            ),
        ]

        s1 = SearchOrchestrator.summarize(results)
        s2 = SearchOrchestrator.summarize(results)

        assert s1.total_results == s2.total_results
        assert s1.good == s2.good

    def test_deterministic_top(self) -> None:
        results = [
            SearchResult(
                vehicle=f"v{i}",
                vehicle_score=MagicMock(),
                market_estimation=MagicMock(),
                profit_analysis=MagicMock(),
                opportunity=MagicMock(overall_score=float(100 - i)),
            )
            for i in range(10)
        ]

        t1 = SearchOrchestrator.top(results, 5)
        t2 = SearchOrchestrator.top(results, 5)
        assert [r.vehicle for r in t1] == [r.vehicle for r in t2]

    def test_deterministic_filter(self) -> None:
        results = [
            SearchResult(
                vehicle="v1",
                vehicle_score=MagicMock(),
                market_estimation=MagicMock(),
                profit_analysis=MagicMock(risk_level=RiskLevel.LOW),
                opportunity=OpportunityAnalysis(
                    overall_score=90.0,
                    opportunity_level=OpportunityLevel.EXCELLENT,
                    recommendation=OppRecommendation.BUY_NOW,
                    estimated_profit=5000.0,
                    roi=25.0,
                    market_confidence=80.0,
                    risk_level="LOW",
                ),
            ),
        ]

        f1 = SearchOrchestrator.filter(results, recommendation="BUY_NOW")
        f2 = SearchOrchestrator.filter(results, recommendation="BUY_NOW")
        assert len(f1) == len(f2)
        assert f1[0].vehicle == f2[0].vehicle


# =============================================================================
# Tests de integración con mocks
# =============================================================================


class TestIntegrationWithMocks:
    """Integración con mocks de todos los servicios."""

    @pytest.mark.asyncio
    async def test_full_pipeline_called(
        self,
        sample_dto: VehicleSearchResult,
    ) -> None:
        """Verifica que todos los servicios son llamados en el orden correcto."""
        # Mocks
        vehicle_service = AsyncMock()
        vehicle_service.search_from_provider = AsyncMock(return_value=[sample_dto])

        vehicle_scorer = MagicMock()
        vehicle_scorer.score = MagicMock(
            return_value=VehicleScore(score=75, category="Muy bueno")
        )

        market_estimator = MagicMock()
        market_estimator.estimate = MagicMock(
            return_value=MarketEstimation(
                market_price=20000.0, confidence=70.0
            )
        )

        profit_analyzer = MagicMock()
        profit_analyzer.analyze = MagicMock(
            return_value=MagicMock(
                purchase_price=15000.0,
                net_profit=3000.0,
                roi_percentage=15.0,
                risk_level=RiskLevel.LOW,
                recommendation="BUY",
                total_cost=18000.0,
                estimated_sale_price=21000.0,
                gross_profit=6000.0,
                profit_margin_percentage=14.29,
                transport_cost=500.0,
                registration_cost=300.0,
                taxes=1500.0,
                inspection_cost=100.0,
                repair_estimate=500.0,
                commission_cost=200.0,
                miscellaneous_cost=100.0,
                cost_breakdown=MagicMock(),
            )
        )

        opportunity_finder = MagicMock()
        opportunity_finder.analyze = MagicMock(
            return_value=OpportunityAnalysis(
                overall_score=75.0,
                opportunity_level=OpportunityLevel.GOOD,
                recommendation=OppRecommendation.WATCH,
                estimated_profit=3000.0,
                roi=15.0,
                market_confidence=70.0,
                risk_level="LOW",
            )
        )

        orchestrator = SearchOrchestrator(
            vehicle_service=vehicle_service,
            vehicle_scorer=vehicle_scorer,
            market_estimator=market_estimator,
            profit_analyzer=profit_analyzer,
            opportunity_finder=opportunity_finder,
        )

        request = SearchRequest(query="BMW", max_results=10, providers=["mobile_de"])

        with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
            results = await orchestrator.search(request)

        # Verificar que todos los servicios fueron llamados
        vehicle_service.search_from_provider.assert_called_once()
        vehicle_scorer.score.assert_called_once()
        market_estimator.estimate.assert_called_once()
        profit_analyzer.analyze.assert_called_once()
        opportunity_finder.analyze.assert_called_once()

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_pipeline_does_not_instantiate_services(
        self,
        sample_dto: VehicleSearchResult,
    ) -> None:
        """El orquestador no debe instanciar servicios internamente."""
        vehicle_service = AsyncMock()
        vehicle_service.search_from_provider = AsyncMock(return_value=[sample_dto])

        # Crear mocks que NO son las clases reales
        scorer = MagicMock()
        scorer.score.return_value = VehicleScore(score=75, category="Muy bueno")

        estimator = MagicMock()
        estimator.estimate.return_value = MarketEstimation(
            market_price=20000.0, confidence=70.0
        )

        analyzer = MagicMock()
        analyzer.analyze.return_value = MagicMock(
            purchase_price=15000.0,
            net_profit=3000.0,
            roi_percentage=15.0,
            risk_level=RiskLevel.LOW,
            recommendation="BUY",
        )

        finder = MagicMock()
        finder.analyze.return_value = OpportunityAnalysis(
            overall_score=75.0,
            opportunity_level=OpportunityLevel.GOOD,
            recommendation=OppRecommendation.WATCH,
            estimated_profit=3000.0,
            roi=15.0,
            market_confidence=70.0,
            risk_level="LOW",
        )

        orchestrator = SearchOrchestrator(
            vehicle_service=vehicle_service,
            vehicle_scorer=scorer,
            market_estimator=estimator,
            profit_analyzer=analyzer,
            opportunity_finder=finder,
        )

        # Verificar que los servicios inyectados son los mismos
        assert orchestrator._vehicle_service is vehicle_service
        assert orchestrator._vehicle_scorer is scorer
        assert orchestrator._market_estimator is estimator
        assert orchestrator._profit_analyzer is analyzer
        assert orchestrator._opportunity_finder is finder


# =============================================================================
# Tests de presupuesto (budget)
# =============================================================================


class TestBudgetFilter:
    """Filtro por presupuesto en la búsqueda."""

    @pytest.mark.asyncio
    async def test_budget_min_filter(
        self,
        orchestrator: SearchOrchestrator,
        vehicle_service_mock: AsyncMock,
        sample_dto: VehicleSearchResult,
    ) -> None:
        """Vehículo por debajo del presupuesto mínimo debe ser excluido."""
        sample_dto.price = 5000.0
        vehicle_service_mock.search_from_provider.return_value = [sample_dto]

        request = SearchRequest(query="BMW", max_results=10, budget_min=10000.0, providers=["mobile_de"])

        with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
            results = await orchestrator.search(request)

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_budget_max_filter(
        self,
        orchestrator: SearchOrchestrator,
        vehicle_service_mock: AsyncMock,
        sample_dto: VehicleSearchResult,
    ) -> None:
        """Vehículo por encima del presupuesto máximo debe ser excluido."""
        sample_dto.price = 50000.0
        vehicle_service_mock.search_from_provider.return_value = [sample_dto]

        request = SearchRequest(query="BMW", max_results=10, budget_max=30000.0, providers=["mobile_de"])

        with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
            results = await orchestrator.search(request)

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_budget_range(
        self,
        orchestrator: SearchOrchestrator,
        vehicle_service_mock: AsyncMock,
        sample_dto: VehicleSearchResult,
    ) -> None:
        """Vehículo dentro del rango de presupuesto debe ser incluido."""
        sample_dto.price = 15000.0
        vehicle_service_mock.search_from_provider.return_value = [sample_dto]

        request = SearchRequest(
            query="BMW",
            max_results=10,
            budget_min=10000.0,
            budget_max=20000.0,
            providers=["mobile_de"],
        )

        with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
            results = await orchestrator.search(request)

        assert len(results) == 1


# =============================================================================
# Tests de edge cases
# =============================================================================


class TestEdgeCases:
    """Casos borde y situaciones límite."""

    @pytest.mark.asyncio
    async def test_search_with_no_providers(
        self,
        orchestrator: SearchOrchestrator,
        vehicle_service_mock: AsyncMock,
    ) -> None:
        """Lista vacía de providers debe devolver lista vacía."""
        vehicle_service_mock.search_from_provider.return_value = []

        request = SearchRequest(query="BMW", max_results=10, providers=[])

        results = await orchestrator.search(request)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_with_vehicle_no_price(
        self,
        orchestrator: SearchOrchestrator,
        vehicle_service_mock: AsyncMock,
    ) -> None:
        """Vehículo sin precio no debe romper el pipeline."""
        dto = VehicleSearchResult(
            source="mobile_de",
            external_id="99999",
            url="https://example.com/vehicle/99999",
            brand="Unknown",
            model="Unknown",
            year=None,
            mileage=None,
            price=None,
        )
        vehicle_service_mock.search_from_provider.return_value = [dto]

        request = SearchRequest(query="test", max_results=10, providers=["mobile_de"])

        with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
            results = await orchestrator.search(request)

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_with_minimal_data(
        self,
        vehicle_service_mock: AsyncMock,
    ) -> None:
        """Búsqueda con datos mínimos debe funcionar."""
        dto = VehicleSearchResult(
            source="mobile_de",
            external_id="1",
            brand="Test",
            model="Test",
            price=1000.0,
        )
        vehicle_service_mock.search_from_provider.return_value = [dto]

        scorer = MagicMock()
        scorer.score.return_value = VehicleScore(score=50, category="Aceptable")

        estimator = MagicMock()
        estimator.estimate.return_value = MarketEstimation(
            market_price=1000.0, confidence=50.0
        )

        analyzer = MagicMock()
        analyzer.analyze.return_value = MagicMock(
            purchase_price=1000.0,
            net_profit=100.0,
            roi_percentage=10.0,
            risk_level=RiskLevel.LOW,
            recommendation="CONSIDER",
        )

        finder = MagicMock()
        finder.analyze.return_value = OpportunityAnalysis(
            overall_score=50.0,
            opportunity_level=OpportunityLevel.AVERAGE,
            recommendation=OppRecommendation.WATCH,
            estimated_profit=100.0,
            roi=10.0,
            market_confidence=50.0,
            risk_level="LOW",
        )

        orchestrator = SearchOrchestrator(
            vehicle_service=vehicle_service_mock,
            vehicle_scorer=scorer,
            market_estimator=estimator,
            profit_analyzer=analyzer,
            opportunity_finder=finder,
        )

        request = SearchRequest(query="test", max_results=10, providers=["mobile_de"])

        with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
            results = await orchestrator.search(request)

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_provider_error_does_not_block(
        self,
        orchestrator: SearchOrchestrator,
        vehicle_service_mock: AsyncMock,
        sample_dto: VehicleSearchResult,
    ) -> None:
        """Error en un provider no debe bloquear la búsqueda completa."""
        vehicle_service_mock.search_from_provider.side_effect = Exception("Provider error")

        request = SearchRequest(query="BMW", max_results=10, providers=["mobile_de"])

        with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
            results = await orchestrator.search(request)

        assert len(results) == 0  # Error silencioso, resultados vacíos

    @pytest.mark.asyncio
    async def test_very_large_max_results(
        self,
        orchestrator: SearchOrchestrator,
        vehicle_service_mock: AsyncMock,
        sample_dto: VehicleSearchResult,
    ) -> None:
        """max_results grande no debe causar problemas."""
        many_dtos = [sample_dto] * 50
        vehicle_service_mock.search_from_provider.return_value = many_dtos

        request = SearchRequest(query="BMW", max_results=100, providers=["mobile_de"])

        with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
            results = await orchestrator.search(request)

        assert len(results) == 50  # max_results=100, but only 50 available

    def test_summarize_with_non_opportunity_analysis(self) -> None:
        """Resultados sin OpportunityAnalysis deben contarse como rejected."""
        results = [
            SearchResult(
                vehicle="v1",
                vehicle_score=MagicMock(),
                market_estimation=MagicMock(),
                profit_analysis=MagicMock(),
                opportunity="not_an_opportunity_analysis",  # No es OpportunityAnalysis
            ),
        ]

        summary = SearchOrchestrator.summarize(results)
        assert summary.total_results == 1
        assert summary.rejected == 1

    def test_sort_empty_list(self) -> None:
        """Ordenar lista vacía debe devolver lista vacía."""
        sorted_results = SearchOrchestrator.sort([])
        assert len(sorted_results) == 0

    def test_filter_with_none_attributes(self) -> None:
        """Filtrar con atributos None debe incluir el resultado."""
        result = SearchResult(
            vehicle="v1",
            vehicle_score=MagicMock(),
            market_estimation=MagicMock(),
            profit_analysis=MagicMock(risk_level=None),
            opportunity=MagicMock(
                recommendation=None,
                opportunity_level=None,
                overall_score=50.0,
            ),
        )

        filtered = SearchOrchestrator.filter(
            [result], recommendation="BUY_NOW"
        )
        assert len(filtered) == 0  # No cumple el filtro

        # Sin filtros, debe incluirse
        filtered = SearchOrchestrator.filter([result])
        assert len(filtered) == 1


# =============================================================================
# Tests de orden por defecto (cascada)
# =============================================================================


class TestDefaultSortOrder:
    """Verifica el orden por defecto en cascada."""

    def test_default_sort_cascade(self) -> None:
        """Orden por defecto: score DESC > ROI DESC > Beneficio DESC > Vehicle Score DESC."""
        results = [
            SearchResult(
                vehicle="v1",
                vehicle_score=MagicMock(score=80),
                market_estimation=MagicMock(),
                profit_analysis=MagicMock(roi_percentage=15.0, net_profit=2000.0),
                opportunity=MagicMock(overall_score=85.0),
            ),
            SearchResult(
                vehicle="v2",
                vehicle_score=MagicMock(score=80),
                market_estimation=MagicMock(),
                profit_analysis=MagicMock(roi_percentage=10.0, net_profit=1000.0),
                opportunity=MagicMock(overall_score=85.0),
            ),
            SearchResult(
                vehicle="v3",
                vehicle_score=MagicMock(score=70),
                market_estimation=MagicMock(),
                profit_analysis=MagicMock(roi_percentage=5.0, net_profit=500.0),
                opportunity=MagicMock(overall_score=60.0),
            ),
        ]

        sorted_results = SearchOrchestrator.sort(results)
        # v1 y v2 tienen el mismo score (85), pero v1 tiene ROI más alto (15 vs 10)
        # v3 tiene score más bajo (60)
        assert sorted_results[0].vehicle == "v1"
        assert sorted_results[1].vehicle == "v2"
        assert sorted_results[2].vehicle == "v3"
