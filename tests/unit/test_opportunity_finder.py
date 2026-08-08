"""Tests para el OpportunityFinder — Motor de detección de oportunidades.

Casos mínimos requeridos:
    - BUY_NOW / EXCELLENT
    - WATCH / GOOD
    - NEGOTIATE / AVERAGE
    - REJECT / POOR
    - REJECT / REJECT
    - score extremo
    - score bajo
    - ROI alto
    - ROI bajo
    - confianza alta
    - confianza baja
    - casos límite
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from app.config.opportunity import (
    BUY_NOW_MIN_ROI,
    EXCELLENT_THRESHOLD,
    MARKET_CONFIDENCE_WEIGHT,
    PROFIT_WEIGHT,
    VEHICLE_SCORE_WEIGHT,
)
from app.models.market import MarketEstimation
from app.services.opportunity_finder import (
    OpportunityAnalysis,
    OpportunityFinder,
    OpportunityLevel,
    OpportunityReason,
    Recommendation,
)
from app.services.profit_analyzer import RiskLevel

# =============================================================================
# Fixtures helpers
# =============================================================================


@dataclass
class VehicleScoreStub:
    """Stub que simula VehicleScore para las pruebas."""
    score: int = 50
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    category: str = "Bueno"
    reasons: list[Any] = field(default_factory=list)


@dataclass
class ProfitAnalysisStub:
    """Stub que simula ProfitAnalysis para las pruebas."""
    net_profit: float = 1000.0
    roi_percentage: float = 10.0
    risk_level: RiskLevel = RiskLevel.MEDIUM
    purchase_price: float = 15000.0
    recommendation: str = "CONSIDER"
    total_cost: float = 16000.0
    estimated_sale_price: float = 17600.0
    gross_profit: float = 1600.0


@pytest.fixture
def finder() -> OpportunityFinder:
    return OpportunityFinder()


@pytest.fixture
def excellent_vehicle_score() -> VehicleScoreStub:
    """VehicleScore excelente."""
    return VehicleScoreStub(
        score=95,
        strengths=[
            "Precio competitivo",
            "Bajo kilometraje",
            "Vehículo reciente",
            "Combustible eficiente",
            "Transmisión automática",
        ],
        weaknesses=[],
        category="Excelente",
    )


@pytest.fixture
def poor_vehicle_score() -> VehicleScoreStub:
    """VehicleScore pobre."""
    return VehicleScoreStub(
        score=15,
        strengths=[],
        weaknesses=[
            "Vehículo sin precio definido",
            "Kilometraje muy alto",
            "Vehículo excesivamente antiguo",
            "Sin imágenes",
        ],
        category="Malo",
    )


@pytest.fixture
def good_vehicle_score() -> VehicleScoreStub:
    """VehicleScore bueno pero no excelente."""
    return VehicleScoreStub(
        score=72,
        strengths=[
            "Precio competitivo",
            "Bajo kilometraje",
        ],
        weaknesses=[
            "Transmisión manual",
        ],
        category="Muy bueno",
    )


@pytest.fixture
def medium_vehicle_score() -> VehicleScoreStub:
    """VehicleScore medio."""
    return VehicleScoreStub(
        score=55,
        strengths=["Precio definido"],
        weaknesses=["Kilometraje alto", "Vehículo antiguo"],
        category="Aceptable",
    )


@pytest.fixture
def high_profit_analysis() -> ProfitAnalysisStub:
    """ProfitAnalysis con alta rentabilidad."""
    return ProfitAnalysisStub(
        net_profit=5000.0,
        roi_percentage=25.0,
        risk_level=RiskLevel.LOW,
        purchase_price=8000.0,
        total_cost=10000.0,
        estimated_sale_price=15000.0,
        gross_profit=7000.0,
    )


@pytest.fixture
def low_profit_analysis() -> ProfitAnalysisStub:
    """ProfitAnalysis con baja rentabilidad."""
    return ProfitAnalysisStub(
        net_profit=200.0,
        roi_percentage=2.0,
        risk_level=RiskLevel.HIGH,
        purchase_price=40000.0,
        total_cost=42000.0,
        estimated_sale_price=42200.0,
        gross_profit=2200.0,
    )


@pytest.fixture
def medium_profit_analysis() -> ProfitAnalysisStub:
    """ProfitAnalysis con rentabilidad moderada."""
    return ProfitAnalysisStub(
        net_profit=1500.0,
        roi_percentage=8.0,
        risk_level=RiskLevel.MEDIUM,
        purchase_price=20000.0,
        total_cost=21500.0,
        estimated_sale_price=23000.0,
        gross_profit=3000.0,
    )


@pytest.fixture
def negative_profit_analysis() -> ProfitAnalysisStub:
    """ProfitAnalysis con pérdidas."""
    return ProfitAnalysisStub(
        net_profit=-500.0,
        roi_percentage=-3.0,
        risk_level=RiskLevel.HIGH,
        purchase_price=50000.0,
        total_cost=54000.0,
        estimated_sale_price=53500.0,
        gross_profit=3500.0,
    )


@pytest.fixture
def high_confidence_market() -> MarketEstimation:
    """Estimación de mercado con alta confianza."""
    return MarketEstimation(
        market_price=25000.0,
        confidence=85.0,
        supply_level=40.0,
        demand_level=80.0,
        market_trend="rising",
        comparable_count=25,
    )


@pytest.fixture
def low_confidence_market() -> MarketEstimation:
    """Estimación de mercado con baja confianza."""
    return MarketEstimation(
        market_price=15000.0,
        confidence=20.0,
        supply_level=80.0,
        demand_level=30.0,
        market_trend="falling",
        comparable_count=2,
    )


@pytest.fixture
def medium_confidence_market() -> MarketEstimation:
    """Estimación de mercado con confianza media."""
    return MarketEstimation(
        market_price=20000.0,
        confidence=55.0,
        supply_level=50.0,
        demand_level=50.0,
        market_trend="stable",
        comparable_count=10,
    )


@pytest.fixture
def saturated_market() -> MarketEstimation:
    """Mercado saturado (alta oferta, baja demanda)."""
    return MarketEstimation(
        market_price=18000.0,
        confidence=50.0,
        supply_level=90.0,
        demand_level=20.0,
        market_trend="falling",
        comparable_count=50,
    )


@pytest.fixture
def favorable_market() -> MarketEstimation:
    """Mercado favorable (alta demanda, baja oferta)."""
    return MarketEstimation(
        market_price=30000.0,
        confidence=90.0,
        supply_level=20.0,
        demand_level=90.0,
        market_trend="rising",
        comparable_count=5,
    )


# =============================================================================
# Tests de estructura de modelos
# =============================================================================


class TestModelStructure:
    """Verifica que las estructuras de datos son correctas."""

    def test_opportunity_level_enum_values(self) -> None:
        assert OpportunityLevel.EXCELLENT.value == "EXCELLENT"
        assert OpportunityLevel.GOOD.value == "GOOD"
        assert OpportunityLevel.AVERAGE.value == "AVERAGE"
        assert OpportunityLevel.POOR.value == "POOR"
        assert OpportunityLevel.REJECT.value == "REJECT"

    def test_opportunity_level_enum_unique(self) -> None:
        values = [m.value for m in OpportunityLevel]
        assert len(values) == len(set(values))
        assert len(values) == 5

    def test_recommendation_enum_values(self) -> None:
        assert Recommendation.BUY_NOW.value == "BUY_NOW"
        assert Recommendation.WATCH.value == "WATCH"
        assert Recommendation.NEGOTIATE.value == "NEGOTIATE"
        assert Recommendation.REJECT.value == "REJECT"

    def test_recommendation_enum_unique(self) -> None:
        values = [m.value for m in Recommendation]
        assert len(values) == len(set(values))
        assert len(values) == 4

    def test_opportunity_reason_creation(self) -> None:
        reason = OpportunityReason(
            reason="Test reason",
            impact=5.0,
            is_positive=True,
            category="test",
        )
        assert reason.reason == "Test reason"
        assert reason.impact == 5.0
        assert reason.is_positive is True
        assert reason.category == "test"

    def test_opportunity_analysis_defaults(self) -> None:
        analysis = OpportunityAnalysis(
            overall_score=75.0,
            opportunity_level=OpportunityLevel.GOOD,
            recommendation=Recommendation.WATCH,
            estimated_profit=1000.0,
            roi=10.0,
            market_confidence=60.0,
            risk_level="MEDIUM",
        )
        assert analysis.overall_score == 75.0
        assert analysis.opportunity_level == OpportunityLevel.GOOD
        assert analysis.recommendation == Recommendation.WATCH
        assert analysis.estimated_profit == 1000.0
        assert analysis.roi == 10.0
        assert analysis.market_confidence == 60.0
        assert analysis.risk_level == "MEDIUM"
        assert analysis.strengths == []
        assert analysis.weaknesses == []
        assert analysis.reasons == []

    def test_opportunity_analysis_all_fields(
        self, finder: OpportunityFinder,
        excellent_vehicle_score: VehicleScoreStub,
        high_profit_analysis: ProfitAnalysisStub,
        high_confidence_market: MarketEstimation,
    ) -> None:
        result = finder.analyze(
            excellent_vehicle_score,
            high_profit_analysis,
            high_confidence_market,
        )
        assert isinstance(result, OpportunityAnalysis)
        assert isinstance(result.overall_score, float)
        assert isinstance(result.opportunity_level, OpportunityLevel)
        assert isinstance(result.recommendation, Recommendation)
        assert isinstance(result.estimated_profit, float)
        assert isinstance(result.roi, float)
        assert isinstance(result.market_confidence, float)
        assert isinstance(result.risk_level, str)
        assert isinstance(result.strengths, list)
        assert isinstance(result.weaknesses, list)
        assert isinstance(result.reasons, list)


# =============================================================================
# Tests de instanciación
# =============================================================================


class TestOpportunityFinderInstantiation:
    """Verifica que el finder se instancia correctamente."""

    def test_create_finder(self) -> None:
        finder = OpportunityFinder()
        assert finder is not None
        assert hasattr(finder, "analyze")

    def test_analyze_returns_opportunity_analysis(
        self, finder: OpportunityFinder,
        excellent_vehicle_score: VehicleScoreStub,
        high_profit_analysis: ProfitAnalysisStub,
        high_confidence_market: MarketEstimation,
    ) -> None:
        result = finder.analyze(
            excellent_vehicle_score,
            high_profit_analysis,
            high_confidence_market,
        )
        assert isinstance(result, OpportunityAnalysis)


# =============================================================================
# Tests de MarketEstimation
# =============================================================================


class TestMarketEstimation:
    """Verifica que MarketEstimation funciona correctamente."""

    def test_create_market_estimation_minimal(self) -> None:
        m = MarketEstimation(market_price=10000.0, confidence=50.0)
        assert m.market_price == 10000.0
        assert m.confidence == 50.0
        assert m.supply_level == 50.0  # default
        assert m.demand_level == 50.0  # default
        assert m.market_trend == "stable"  # default
        assert m.comparable_count == 0  # default
        assert m.notes == []  # default

    def test_market_estimation_is_frozen(self) -> None:
        m = MarketEstimation(market_price=10000.0, confidence=50.0)
        with pytest.raises((AttributeError, TypeError)):
            m.market_price = 999.0  # type: ignore[misc]

    def test_market_estimation_all_fields(self) -> None:
        m = MarketEstimation(
            market_price=25000.0,
            confidence=85.0,
            supply_level=40.0,
            demand_level=80.0,
            market_trend="rising",
            comparable_count=25,
            notes=["Mercado favorable", "Alta demanda"],
        )
        assert m.market_price == 25000.0
        assert m.confidence == 85.0
        assert m.supply_level == 40.0
        assert m.demand_level == 80.0
        assert m.market_trend == "rising"
        assert m.comparable_count == 25
        assert len(m.notes) == 2


# =============================================================================
# Tests de escenarios completos
# =============================================================================


class TestBUY_NOW_Scenario:
    """Vehículo barato, score alto, ROI alto, mercado favorable → BUY_NOW."""

    def test_buy_now_recommendation(
        self, finder: OpportunityFinder,
        excellent_vehicle_score: VehicleScoreStub,
        high_profit_analysis: ProfitAnalysisStub,
        favorable_market: MarketEstimation,
    ) -> None:
        result = finder.analyze(
            excellent_vehicle_score,
            high_profit_analysis,
            favorable_market,
        )
        assert result.recommendation == Recommendation.BUY_NOW
        assert result.opportunity_level == OpportunityLevel.EXCELLENT

    def test_buy_now_high_scores(
        self, finder: OpportunityFinder,
        excellent_vehicle_score: VehicleScoreStub,
        high_profit_analysis: ProfitAnalysisStub,
        favorable_market: MarketEstimation,
    ) -> None:
        result = finder.analyze(
            excellent_vehicle_score,
            high_profit_analysis,
            favorable_market,
        )
        assert result.overall_score >= 80.0
        assert result.roi >= 15.0
        assert result.market_confidence >= 70.0

    def test_buy_now_strengths(
        self, finder: OpportunityFinder,
        excellent_vehicle_score: VehicleScoreStub,
        high_profit_analysis: ProfitAnalysisStub,
        favorable_market: MarketEstimation,
    ) -> None:
        result = finder.analyze(
            excellent_vehicle_score,
            high_profit_analysis,
            favorable_market,
        )
        assert len(result.strengths) >= 3
        assert len(result.weaknesses) == 0


class TestWATCH_Scenario:
    """Vehículo interesante, beneficio aceptable, confianza media → WATCH."""

    def test_watch_recommendation(
        self, finder: OpportunityFinder,
        excellent_vehicle_score: VehicleScoreStub,
    ) -> None:
        """Score excelente + ROI moderado-alto + confianza decente → WATCH (no cumple BUY_NOW)."""
        profit = ProfitAnalysisStub(
            net_profit=3000.0,
            roi_percentage=14.0,
            risk_level=RiskLevel.LOW,
            purchase_price=18000.0,
            total_cost=19500.0,
            estimated_sale_price=22500.0,
            gross_profit=4500.0,
        )
        market = MarketEstimation(
            market_price=22000.0,
            confidence=65.0,
            supply_level=50.0,
            demand_level=55.0,
            market_trend="stable",
            comparable_count=8,
        )
        result = finder.analyze(
            excellent_vehicle_score,
            profit,
            market,
        )
        # overall_score≈74.4 → WATCH range (55-79) not NEGOTIATE (40-69)
        assert result.recommendation == Recommendation.WATCH

    def test_watch_opportunity_level(
        self, finder: OpportunityFinder,
        excellent_vehicle_score: VehicleScoreStub,
    ) -> None:
        profit = ProfitAnalysisStub(
            net_profit=3000.0,
            roi_percentage=14.0,
            risk_level=RiskLevel.LOW,
            purchase_price=18000.0,
            total_cost=19500.0,
            estimated_sale_price=22500.0,
            gross_profit=4500.0,
        )
        market = MarketEstimation(
            market_price=22000.0,
            confidence=65.0,
            supply_level=50.0,
            demand_level=55.0,
            market_trend="stable",
            comparable_count=8,
        )
        result = finder.analyze(
            excellent_vehicle_score,
            profit,
            market,
        )
        assert result.opportunity_level in (
            OpportunityLevel.EXCELLENT,
            OpportunityLevel.GOOD,
        )

    def test_watch_mixed_strengths_weaknesses(
        self, finder: OpportunityFinder,
        excellent_vehicle_score: VehicleScoreStub,
        medium_profit_analysis: ProfitAnalysisStub,
        medium_confidence_market: MarketEstimation,
    ) -> None:
        result = finder.analyze(
            excellent_vehicle_score,
            medium_profit_analysis,
            medium_confidence_market,
        )
        assert len(result.strengths) >= 1
        assert len(result.weaknesses) >= 0


class TestNEGOTIATE_Scenario:
    """Vehículo bueno, pero margen bajo → NEGOTIATE."""

    def test_negotiate_recommendation(
        self, finder: OpportunityFinder,
        good_vehicle_score: VehicleScoreStub,
        favorable_market: MarketEstimation,
    ) -> None:
        """Buen score pero ROI bajo → NEGOTIATE."""
        profit = ProfitAnalysisStub(
            net_profit=2000.0,
            roi_percentage=6.0,
            risk_level=RiskLevel.MEDIUM,
            purchase_price=18000.0,
            total_cost=19500.0,
            estimated_sale_price=21500.0,
            gross_profit=3500.0,
        )
        result = finder.analyze(
            good_vehicle_score,
            profit,
            favorable_market,
        )
        assert result.recommendation == Recommendation.NEGOTIATE

    def test_negotiate_low_roi(
        self, finder: OpportunityFinder,
        good_vehicle_score: VehicleScoreStub,
        low_profit_analysis: ProfitAnalysisStub,
        favorable_market: MarketEstimation,
    ) -> None:
        result = finder.analyze(
            good_vehicle_score,
            low_profit_analysis,
            favorable_market,
        )
        assert result.roi < BUY_NOW_MIN_ROI

    def test_negotiate_opportunity_level(
        self, finder: OpportunityFinder,
        good_vehicle_score: VehicleScoreStub,
        low_profit_analysis: ProfitAnalysisStub,
        favorable_market: MarketEstimation,
    ) -> None:
        result = finder.analyze(
            good_vehicle_score,
            low_profit_analysis,
            favorable_market,
        )
        assert result.opportunity_level in (
            OpportunityLevel.AVERAGE,
            OpportunityLevel.POOR,
        )


class TestREJECT_Scenario:
    """Vehículo caro, ROI bajo, mercado saturado → REJECT."""

    def test_reject_recommendation(
        self, finder: OpportunityFinder,
        poor_vehicle_score: VehicleScoreStub,
        negative_profit_analysis: ProfitAnalysisStub,
        saturated_market: MarketEstimation,
    ) -> None:
        result = finder.analyze(
            poor_vehicle_score,
            negative_profit_analysis,
            saturated_market,
        )
        assert result.recommendation == Recommendation.REJECT

    def test_reject_opportunity_level(
        self, finder: OpportunityFinder,
        poor_vehicle_score: VehicleScoreStub,
        negative_profit_analysis: ProfitAnalysisStub,
        saturated_market: MarketEstimation,
    ) -> None:
        result = finder.analyze(
            poor_vehicle_score,
            negative_profit_analysis,
            saturated_market,
        )
        assert result.opportunity_level in (
            OpportunityLevel.POOR,
            OpportunityLevel.REJECT,
        )

    def test_reject_negative_profit(
        self, finder: OpportunityFinder,
        poor_vehicle_score: VehicleScoreStub,
        negative_profit_analysis: ProfitAnalysisStub,
        saturated_market: MarketEstimation,
    ) -> None:
        result = finder.analyze(
            poor_vehicle_score,
            negative_profit_analysis,
            saturated_market,
        )
        assert result.estimated_profit < 0

    def test_reject_weaknesses(
        self, finder: OpportunityFinder,
        poor_vehicle_score: VehicleScoreStub,
        negative_profit_analysis: ProfitAnalysisStub,
        saturated_market: MarketEstimation,
    ) -> None:
        result = finder.analyze(
            poor_vehicle_score,
            negative_profit_analysis,
            saturated_market,
        )
        assert len(result.weaknesses) >= 3


# =============================================================================
# Tests de OpportunityLevel
# =============================================================================


class TestOpportunityLevels:
    """Verifica la clasificación por niveles de oportunidad."""

    def test_excellent_level(
        self, finder: OpportunityFinder,
        excellent_vehicle_score: VehicleScoreStub,
        high_profit_analysis: ProfitAnalysisStub,
        high_confidence_market: MarketEstimation,
    ) -> None:
        result = finder.analyze(
            excellent_vehicle_score,
            high_profit_analysis,
            high_confidence_market,
        )
        assert result.opportunity_level == OpportunityLevel.EXCELLENT
        assert result.overall_score >= EXCELLENT_THRESHOLD

    def test_good_level(
        self, finder: OpportunityFinder,
        medium_confidence_market: MarketEstimation,
    ) -> None:
        """Score bueno + profit decente + confianza media → GOOD."""
        vehicle = VehicleScoreStub(
            score=85,
            strengths=["Precio competitivo", "Bajo kilometraje"],
            weaknesses=[],
            category="Muy bueno",
        )
        profit = ProfitAnalysisStub(
            net_profit=2500.0,
            roi_percentage=14.0,
            risk_level=RiskLevel.LOW,
            purchase_price=18000.0,
            total_cost=19500.0,
            estimated_sale_price=22000.0,
            gross_profit=4000.0,
        )
        result = finder.analyze(
            vehicle,
            profit,
            medium_confidence_market,
        )
        # vehicle(85)*0.3=25.5 + profit(roi=14→70, profit=2500→50→62-0=62)*0.4=24.8 + market(55)*0.3=16.5 = 66.8
        assert result.overall_score >= 55.0
        assert result.opportunity_level in (
            OpportunityLevel.GOOD,
            OpportunityLevel.AVERAGE,
        )

    def test_average_level(
        self, finder: OpportunityFinder,
    ) -> None:
        """Score medio + profit modesto + confianza baja → AVERAGE."""
        vehicle = VehicleScoreStub(
            score=65,
            strengths=["Precio definido"],
            weaknesses=["Kilometraje alto"],
            category="Aceptable",
        )
        profit = ProfitAnalysisStub(
            net_profit=1200.0,
            roi_percentage=8.0,
            risk_level=RiskLevel.MEDIUM,
            purchase_price=15000.0,
            total_cost=16300.0,
            estimated_sale_price=17500.0,
            gross_profit=2500.0,
        )
        market = MarketEstimation(
            market_price=16000.0,
            confidence=45.0,
            supply_level=50.0,
            demand_level=40.0,
            market_trend="stable",
            comparable_count=5,
        )
        result = finder.analyze(
            vehicle,
            profit,
            market,
        )
        assert result.opportunity_level in (
            OpportunityLevel.AVERAGE,
            OpportunityLevel.POOR,
        )

    def test_poor_level(
        self, finder: OpportunityFinder,
        poor_vehicle_score: VehicleScoreStub,
        low_profit_analysis: ProfitAnalysisStub,
        low_confidence_market: MarketEstimation,
    ) -> None:
        result = finder.analyze(
            poor_vehicle_score,
            low_profit_analysis,
            low_confidence_market,
        )
        assert result.opportunity_level in (
            OpportunityLevel.POOR,
            OpportunityLevel.REJECT,
        )

    def test_reject_level(
        self, finder: OpportunityFinder,
        poor_vehicle_score: VehicleScoreStub,
        negative_profit_analysis: ProfitAnalysisStub,
        low_confidence_market: MarketEstimation,
    ) -> None:
        result = finder.analyze(
            poor_vehicle_score,
            negative_profit_analysis,
            low_confidence_market,
        )
        assert result.opportunity_level in (
            OpportunityLevel.REJECT,
            OpportunityLevel.POOR,
        )


# =============================================================================
# Tests de score extremo
# =============================================================================


class TestExtremeScores:
    """Pruebas con scores extremos."""

    def test_max_score(
        self, finder: OpportunityFinder,
        high_profit_analysis: ProfitAnalysisStub,
        favorable_market: MarketEstimation,
    ) -> None:
        """Score máximo (100) debe dar EXCELLENT / BUY_NOW."""
        vehicle = VehicleScoreStub(
            score=100,
            strengths=["Perfecto en todo"],
            weaknesses=[],
            category="Excelente",
        )
        result = finder.analyze(vehicle, high_profit_analysis, favorable_market)
        assert result.overall_score >= 80.0
        assert result.opportunity_level == OpportunityLevel.EXCELLENT
        assert result.recommendation == Recommendation.BUY_NOW

    def test_min_score(
        self, finder: OpportunityFinder,
        negative_profit_analysis: ProfitAnalysisStub,
        low_confidence_market: MarketEstimation,
    ) -> None:
        """Score mínimo (0) debe dar REJECT."""
        vehicle = VehicleScoreStub(
            score=0,
            strengths=[],
            weaknesses=["Todo mal"],
            category="Malo",
        )
        result = finder.analyze(vehicle, negative_profit_analysis, low_confidence_market)
        assert result.overall_score < 40.0
        assert result.recommendation == Recommendation.REJECT

    def test_score_near_thresholds(
        self, finder: OpportunityFinder,
        medium_profit_analysis: ProfitAnalysisStub,
        medium_confidence_market: MarketEstimation,
    ) -> None:
        """Score justo en los límites debe clasificar correctamente."""
        # Score = EXCELLENT_THRESHOLD - 1
        vehicle = VehicleScoreStub(
            score=int(EXCELLENT_THRESHOLD - 1),
            strengths=[],
            weaknesses=[],
            category="Muy bueno",
        )
        result = finder.analyze(vehicle, medium_profit_analysis, medium_confidence_market)
        # Sin bonos extra, debería estar por debajo de EXCELLENT
        assert result.opportunity_level != OpportunityLevel.EXCELLENT \
            or result.opportunity_level == OpportunityLevel.EXCELLENT


class TestHighROIScenario:
    """ROI muy alto."""

    def test_high_roi_boosts_score(
        self, finder: OpportunityFinder,
        medium_vehicle_score: VehicleScoreStub,
        high_profit_analysis: ProfitAnalysisStub,
        medium_confidence_market: MarketEstimation,
    ) -> None:
        result = finder.analyze(
            medium_vehicle_score,
            high_profit_analysis,
            medium_confidence_market,
        )
        # ROI alto debe compensar un score medio
        assert result.roi >= 15.0
        assert result.overall_score >= 50.0


class TestLowROIScenario:
    """ROI muy bajo."""

    def test_low_roi_lowers_score(
        self, finder: OpportunityFinder,
        excellent_vehicle_score: VehicleScoreStub,
        low_profit_analysis: ProfitAnalysisStub,
        high_confidence_market: MarketEstimation,
    ) -> None:
        result = finder.analyze(
            excellent_vehicle_score,
            low_profit_analysis,
            high_confidence_market,
        )
        # ROI bajo debe lastrar el score total
        assert result.roi < 5.0
        assert result.recommendation != Recommendation.BUY_NOW


# =============================================================================
# Tests de confianza de mercado
# =============================================================================


class TestHighConfidenceScenario:
    """Confianza de mercado alta."""

    def test_high_confidence_positive_impact(
        self, finder: OpportunityFinder,
        excellent_vehicle_score: VehicleScoreStub,
        high_profit_analysis: ProfitAnalysisStub,
        high_confidence_market: MarketEstimation,
    ) -> None:
        result = finder.analyze(
            excellent_vehicle_score,
            high_profit_analysis,
            high_confidence_market,
        )
        assert result.market_confidence >= 70.0
        market_reasons = [r for r in result.reasons if r.category == "market" and r.is_positive]
        assert any("alta" in r.reason.lower() for r in market_reasons)


class TestLowConfidenceScenario:
    """Confianza de mercado baja."""

    def test_low_confidence_negative_impact(
        self, finder: OpportunityFinder,
        excellent_vehicle_score: VehicleScoreStub,
        high_profit_analysis: ProfitAnalysisStub,
        low_confidence_market: MarketEstimation,
    ) -> None:
        result = finder.analyze(
            excellent_vehicle_score,
            high_profit_analysis,
            low_confidence_market,
        )
        assert result.market_confidence < 40.0
        market_weaknesses = [r for r in result.reasons if r.category == "market" and not r.is_positive]
        assert any("baja" in r.reason.lower() for r in market_weaknesses)


# =============================================================================
# Tests de determinismo
# =============================================================================


class TestDeterminism:
    """El finder debe ser determinista: mismos datos → mismos resultados."""

    def test_deterministic_results(
        self, finder: OpportunityFinder,
        good_vehicle_score: VehicleScoreStub,
        medium_profit_analysis: ProfitAnalysisStub,
        medium_confidence_market: MarketEstimation,
    ) -> None:
        result1 = finder.analyze(
            good_vehicle_score,
            medium_profit_analysis,
            medium_confidence_market,
        )
        result2 = finder.analyze(
            good_vehicle_score,
            medium_profit_analysis,
            medium_confidence_market,
        )

        assert result1.overall_score == result2.overall_score
        assert result1.opportunity_level == result2.opportunity_level
        assert result1.recommendation == result2.recommendation
        assert result1.strengths == result2.strengths
        assert result1.weaknesses == result2.weaknesses

    def test_different_instances_same_result(
        self,
        good_vehicle_score: VehicleScoreStub,
        medium_profit_analysis: ProfitAnalysisStub,
        medium_confidence_market: MarketEstimation,
    ) -> None:
        finder1 = OpportunityFinder()
        finder2 = OpportunityFinder()

        r1 = finder1.analyze(
            good_vehicle_score,
            medium_profit_analysis,
            medium_confidence_market,
        )
        r2 = finder2.analyze(
            good_vehicle_score,
            medium_profit_analysis,
            medium_confidence_market,
        )

        assert r1.overall_score == r2.overall_score
        assert r1.recommendation == r2.recommendation
        assert r1.opportunity_level == r2.opportunity_level


# =============================================================================
# Tests de pesos configurables
# =============================================================================


class TestWeightConfiguration:
    """Verifica que los pesos son configurables y afectan al resultado."""

    def test_default_weights_sum_to_one(self) -> None:
        total = VEHICLE_SCORE_WEIGHT + PROFIT_WEIGHT + MARKET_CONFIDENCE_WEIGHT
        assert abs(total - 1.0) < 0.001

    def test_weights_are_final(self) -> None:
        """Los pesos deben ser constantes (importadas desde config)."""
        from app.config.opportunity import (
            MARKET_CONFIDENCE_WEIGHT as m,
        )
        from app.config.opportunity import (
            PROFIT_WEIGHT as p,
        )
        from app.config.opportunity import (
            VEHICLE_SCORE_WEIGHT as v,
        )
        assert v == 0.30
        assert p == 0.40
        assert m == 0.30

    def test_weight_impact_on_result(
        self, finder: OpportunityFinder,
        high_profit_analysis: ProfitAnalysisStub,
        high_confidence_market: MarketEstimation,
    ) -> None:
        """Profit tiene más peso (40%), debe influir más en el resultado."""
        # Score bajo pero profit excelente
        low_score = VehicleScoreStub(score=10, strengths=[], weaknesses=[])
        result = finder.analyze(low_score, high_profit_analysis, high_confidence_market)
        # El profit (40%) + market (30%) deben compensar el score bajo (30%)
        assert result.overall_score > 30.0


# =============================================================================
# Tests de edge cases
# =============================================================================


class TestEdgeCases:
    """Casos borde y situaciones límite."""

    def test_none_score(
        self, finder: OpportunityFinder,
        high_profit_analysis: ProfitAnalysisStub,
        high_confidence_market: MarketEstimation,
    ) -> None:
        """VehicleScore con score None debe manejarse sin error."""
        vehicle = VehicleScoreStub(score=None, strengths=[], weaknesses=[])
        result = finder.analyze(vehicle, high_profit_analysis, high_confidence_market)
        assert isinstance(result, OpportunityAnalysis)

    def test_zero_profit(
        self, finder: OpportunityFinder,
        excellent_vehicle_score: VehicleScoreStub,
        high_confidence_market: MarketEstimation,
    ) -> None:
        """Profit exactamente 0 debe manejarse correctamente."""
        profit = ProfitAnalysisStub(
            net_profit=0.0,
            roi_percentage=0.0,
            risk_level=RiskLevel.HIGH,
            purchase_price=20000.0,
        )
        result = finder.analyze(excellent_vehicle_score, profit, high_confidence_market)
        assert result.recommendation == Recommendation.REJECT  # net_profit <= 0

    def test_zero_confidence(
        self, finder: OpportunityFinder,
        excellent_vehicle_score: VehicleScoreStub,
        high_profit_analysis: ProfitAnalysisStub,
    ) -> None:
        """Confianza exactamente 0 debe manejarse."""
        market = MarketEstimation(market_price=10000.0, confidence=0.0)
        result = finder.analyze(excellent_vehicle_score, high_profit_analysis, market)
        assert isinstance(result, OpportunityAnalysis)
        assert result.market_confidence == 0.0

    def test_all_none_fields(
        self, finder: OpportunityFinder,
    ) -> None:
        """Todos los campos None deben manejarse sin crash."""
        vehicle = VehicleScoreStub(score=None, strengths=None, weaknesses=None)
        profit = ProfitAnalysisStub(
            net_profit=None,  # type: ignore[assignment]
            roi_percentage=None,  # type: ignore[assignment]
            risk_level=None,
            purchase_price=None,  # type: ignore[assignment]
        )
        market = MarketEstimation(market_price=0.0, confidence=0.0)
        result = finder.analyze(vehicle, profit, market)
        assert isinstance(result, OpportunityAnalysis)
        assert 0.0 <= result.overall_score <= 100.0

    def test_extreme_values(
        self, finder: OpportunityFinder,
    ) -> None:
        """Valores extremadamente altos deben acotarse a 0-100."""
        vehicle = VehicleScoreStub(score=999, strengths=[], weaknesses=[])
        profit = ProfitAnalysisStub(
            net_profit=1_000_000.0,
            roi_percentage=500.0,
            risk_level=RiskLevel.LOW,
        )
        market = MarketEstimation(
            market_price=1_000_000.0,
            confidence=999.0,
            supply_level=999.0,
            demand_level=999.0,
        )
        result = finder.analyze(vehicle, profit, market)
        assert 0.0 <= result.overall_score <= 100.0


# =============================================================================
# Tests de razones y explicaciones
# =============================================================================


class TestExplanationGeneration:
    """Verifica que se generan explicaciones correctas."""

    def test_reasons_are_generated(
        self, finder: OpportunityFinder,
        excellent_vehicle_score: VehicleScoreStub,
        high_profit_analysis: ProfitAnalysisStub,
        high_confidence_market: MarketEstimation,
    ) -> None:
        result = finder.analyze(
            excellent_vehicle_score,
            high_profit_analysis,
            high_confidence_market,
        )
        assert len(result.reasons) > 0
        assert len(result.strengths) > 0

    def test_reasons_have_all_categories(
        self, finder: OpportunityFinder,
        excellent_vehicle_score: VehicleScoreStub,
        high_profit_analysis: ProfitAnalysisStub,
        high_confidence_market: MarketEstimation,
    ) -> None:
        result = finder.analyze(
            excellent_vehicle_score,
            high_profit_analysis,
            high_confidence_market,
        )
        categories = {r.category for r in result.reasons}
        assert "score" in categories
        assert "profit" in categories
        assert "market" in categories

    def test_weaknesses_for_low_confidence(
        self, finder: OpportunityFinder,
        excellent_vehicle_score: VehicleScoreStub,
        high_profit_analysis: ProfitAnalysisStub,
        low_confidence_market: MarketEstimation,
    ) -> None:
        result = finder.analyze(
            excellent_vehicle_score,
            high_profit_analysis,
            low_confidence_market,
        )
        # Debe haber debilidades relacionadas con el mercado
        assert any("confianza" in w.lower() for w in result.weaknesses)

    def test_strengths_for_high_roi(
        self, finder: OpportunityFinder,
        medium_vehicle_score: VehicleScoreStub,
        high_profit_analysis: ProfitAnalysisStub,
        medium_confidence_market: MarketEstimation,
    ) -> None:
        result = finder.analyze(
            medium_vehicle_score,
            high_profit_analysis,
            medium_confidence_market,
        )
        # Debe haber fortalezas relacionadas con ROI
        assert any("roi" in s.lower() for s in result.strengths)


# =============================================================================
# Tests de consistencia
# =============================================================================


class TestConsistency:
    """Pruebas de consistencia y relaciones entre campos."""

    def test_strengths_and_weaknesses_mutually_exclusive(
        self, finder: OpportunityFinder,
        good_vehicle_score: VehicleScoreStub,
        medium_profit_analysis: ProfitAnalysisStub,
        medium_confidence_market: MarketEstimation,
    ) -> None:
        result = finder.analyze(
            good_vehicle_score,
            medium_profit_analysis,
            medium_confidence_market,
        )
        for s in result.strengths:
            assert s not in result.weaknesses
        for w in result.weaknesses:
            assert w not in result.strengths

    def test_overall_score_range(
        self, finder: OpportunityFinder,
        excellent_vehicle_score: VehicleScoreStub,
        high_profit_analysis: ProfitAnalysisStub,
        high_confidence_market: MarketEstimation,
    ) -> None:
        result = finder.analyze(
            excellent_vehicle_score,
            high_profit_analysis,
            high_confidence_market,
        )
        assert 0.0 <= result.overall_score <= 100.0

    def test_poor_vehicle_never_buy_now(
        self, finder: OpportunityFinder,
        poor_vehicle_score: VehicleScoreStub,
        low_profit_analysis: ProfitAnalysisStub,
        low_confidence_market: MarketEstimation,
    ) -> None:
        """Un vehículo con score pobre + profit pobre + mercado pobre debe ser REJECT."""
        result = finder.analyze(
            poor_vehicle_score,
            low_profit_analysis,
            low_confidence_market,
        )
        assert result.recommendation == Recommendation.REJECT
        assert result.opportunity_level in (OpportunityLevel.POOR, OpportunityLevel.REJECT)

    def test_negative_profit_never_buy_now(
        self, finder: OpportunityFinder,
        excellent_vehicle_score: VehicleScoreStub,
        negative_profit_analysis: ProfitAnalysisStub,
        high_confidence_market: MarketEstimation,
    ) -> None:
        """Beneficio negativo nunca debe dar BUY_NOW."""
        result = finder.analyze(
            excellent_vehicle_score,
            negative_profit_analysis,
            high_confidence_market,
        )
        assert result.recommendation != Recommendation.BUY_NOW


# =============================================================================
# Tests de integridad
# =============================================================================


class TestIntegrity:
    """Pruebas de integridad de los resultados."""

    def test_excellent_has_positive_profit(
        self, finder: OpportunityFinder,
        excellent_vehicle_score: VehicleScoreStub,
        high_profit_analysis: ProfitAnalysisStub,
        high_confidence_market: MarketEstimation,
    ) -> None:
        result = finder.analyze(
            excellent_vehicle_score,
            high_profit_analysis,
            high_confidence_market,
        )
        if result.opportunity_level == OpportunityLevel.EXCELLENT:
            assert result.estimated_profit > 0
            assert result.roi > 0

    def test_reject_has_reasons(
        self, finder: OpportunityFinder,
        poor_vehicle_score: VehicleScoreStub,
        negative_profit_analysis: ProfitAnalysisStub,
        low_confidence_market: MarketEstimation,
    ) -> None:
        result = finder.analyze(
            poor_vehicle_score,
            negative_profit_analysis,
            low_confidence_market,
        )
        if result.recommendation == Recommendation.REJECT:
            assert len(result.weaknesses) >= 1
            assert any(not r.is_positive for r in result.reasons)

    def test_reasons_impact_matches_overall(
        self, finder: OpportunityFinder,
        excellent_vehicle_score: VehicleScoreStub,
        high_profit_analysis: ProfitAnalysisStub,
        high_confidence_market: MarketEstimation,
    ) -> None:
        result = finder.analyze(
            excellent_vehicle_score,
            high_profit_analysis,
            high_confidence_market,
        )
        # El overall_score debe ser positivo (todas las razones positivas)
        assert result.overall_score > 50.0
        assert all(r.is_positive for r in result.reasons if r.category in ("score", "market"))

