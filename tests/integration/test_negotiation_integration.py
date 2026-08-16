"""Tests de integración para NegotiationEngine dentro del pipeline completo.

Verifica que:
    1. Un vehículo con recomendación BUY se genera correctamente.
    2. Un vehículo con recomendación NEGOTIATE se genera correctamente.
    3. Un vehículo con recomendación WALK_AWAY se genera correctamente.
    4. NegotiationResult aparece en SearchResult y en la respuesta de la API.
    5. La compatibilidad hacia atrás se mantiene (los campos existentes no cambian).

Estrategia:
    - Usamos stubs para VehicleScorer, MarketEstimator, ProfitAnalyzer y
      OpportunityFinder para evitar dependencias externas.
    - Probamos SearchOrchestrator con NegotiationEngine real inyectado.
    - Verificamos que el campo `negotiation` aparece en SearchResult.
    - Verificamos las 3 recomendaciones posibles.

No depende de:
    - Bases de datos.
    - Proveedores externos.
    - Internet.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.market import MarketEstimation
from app.models.negotiation import (
    NegotiationRecommendation,
    NegotiationResult,
)
from app.models.search import SearchRequest, SearchResult
from app.providers.dto import VehicleSearchResult
from app.providers.registry import ProviderRegistry
from app.services.negotiation_engine import NegotiationEngine
from app.services.opportunity_finder import (
    OpportunityAnalysis,
    OpportunityLevel,
)
from app.services.opportunity_finder import (
    Recommendation as OppRecommendation,
)
from app.services.profit_analyzer import ProfitAnalysis
from app.services.profit_analyzer import RiskLevel as ProfitRiskLevel
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
    repair_estimate: float = 500.0
    risk_level: ProfitRiskLevel = ProfitRiskLevel.LOW
    recommendation: str = "BUY"

    def analyze(self, vehicle: object, **kwargs: Any) -> ProfitAnalysis:
        return ProfitAnalysis(
            purchase_price=self.purchase_price,
            transport_cost=500.0,
            registration_cost=300.0,
            taxes=1500.0,
            inspection_cost=100.0,
            repair_estimate=self.repair_estimate,
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


# =============================================================================
# Tests de integración: NegotiationEngine en el pipeline
# =============================================================================


class TestNegotiationInPipeline:
    """Verifica que NegotiationEngine se integra correctamente en el pipeline."""

    @pytest.fixture
    def orchestrator_with_negotiation(
        self,
        vehicle_service_mock: AsyncMock,
        vehicle_scorer: VehicleScorerStub,
        market_estimator: MarketEstimatorStub,
        profit_analyzer: ProfitAnalyzerStub,
        opportunity_finder: OpportunityFinderStub,
    ) -> SearchOrchestrator:
        """Orquestador con NegotiationEngine real."""
        return SearchOrchestrator(
            vehicle_service=vehicle_service_mock,
            vehicle_scorer=vehicle_scorer,
            market_estimator=market_estimator,
            profit_analyzer=profit_analyzer,
            opportunity_finder=opportunity_finder,
            negotiation_engine=NegotiationEngine(),
        )

    @pytest.mark.asyncio
    async def test_negotiation_field_present_in_result(
        self,
        orchestrator_with_negotiation: SearchOrchestrator,
        vehicle_service_mock: AsyncMock,
        sample_dto: VehicleSearchResult,
    ) -> None:
        """Verifica que NegotiationResult aparece en SearchResult.

        Es el test de compatibilidad fundamental: ningún campo existente
        se pierde y el nuevo campo `negotiation` está presente.
        """
        vehicle_service_mock.search_from_provider.return_value = [sample_dto]
        request = SearchRequest(query="BMW", max_results=10, providers=["mobile_de"])

        with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
            results = await orchestrator_with_negotiation.search(request)

        assert len(results) == 1
        result = results[0]

        # Compatibilidad hacia atrás: campos existentes
        assert result.vehicle is not None
        assert result.vehicle_score is not None
        assert result.market_estimation is not None
        assert result.profit_analysis is not None
        assert result.opportunity is not None

        # Nuevo campo: negotiation
        assert result.negotiation is not None
        assert isinstance(result.negotiation, NegotiationResult)

    @pytest.mark.asyncio
    async def test_negotiation_has_expected_structure(
        self,
        orchestrator_with_negotiation: SearchOrchestrator,
        vehicle_service_mock: AsyncMock,
        sample_dto: VehicleSearchResult,
    ) -> None:
        """Verifica que NegotiationResult tiene todos los campos esperados."""
        vehicle_service_mock.search_from_provider.return_value = [sample_dto]
        request = SearchRequest(query="BMW", max_results=10, providers=["mobile_de"])

        with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
            results = await orchestrator_with_negotiation.search(request)

        neg = results[0].negotiation
        assert neg is not None

        # Campos numéricos
        assert isinstance(neg.estimated_vehicle_value, float)
        assert isinstance(neg.recommended_initial_offer, float)
        assert isinstance(neg.recommended_counter_offer, float)
        assert isinstance(neg.maximum_purchase_price, float)
        assert isinstance(neg.walk_away_price, float)
        assert isinstance(neg.expected_profit, float)
        assert isinstance(neg.expected_roi, float)
        assert isinstance(neg.leverage_score, float)
        assert isinstance(neg.price_gap, float)
        assert isinstance(neg.discount_needed, float)

        # Recomendación
        assert isinstance(neg.recommendation, NegotiationRecommendation)

        # Argumentos (puede estar vacío pero debe ser lista)
        assert isinstance(neg.negotiation_arguments, list)

        # Script
        assert neg.negotiation_script is not None
        assert hasattr(neg.negotiation_script, "opening")
        assert hasattr(neg.negotiation_script, "closing")

    @pytest.mark.asyncio
    async def test_orchestrator_without_negotiation_still_works(
        self,
        vehicle_service_mock: AsyncMock,
        vehicle_scorer: VehicleScorerStub,
        market_estimator: MarketEstimatorStub,
        profit_analyzer: ProfitAnalyzerStub,
        opportunity_finder: OpportunityFinderStub,
        sample_dto: VehicleSearchResult,
    ) -> None:
        """Verifica compatibilidad: orquestador sin NegotiationEngine.

        Si no se inyecta NegotiationEngine, el SearchResult debe tener
        negotiation=None y el resto del análisis debe funcionar igual.
        """
        orchestrator = SearchOrchestrator(
            vehicle_service=vehicle_service_mock,
            vehicle_scorer=vehicle_scorer,
            market_estimator=market_estimator,
            profit_analyzer=profit_analyzer,
            opportunity_finder=opportunity_finder,
            # No se pasa negotiation_engine → se crea NegotiationEngine() por defecto
        )

        vehicle_service_mock.search_from_provider.return_value = [sample_dto]
        request = SearchRequest(query="BMW", max_results=10, providers=["mobile_de"])

        with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
            results = await orchestrator.search(request)

        assert len(results) == 1
        result = results[0]

        # Con el cambio actual, negotiation_engine se crea por defecto
        # así que negotiation siempre tendrá un valor.
        # Este test verifica que negotiation es NegotiationResult y no None.
        assert result.negotiation is not None
        assert isinstance(result.negotiation, NegotiationResult)

        # Compatibilidad: campos existentes
        assert result.vehicle is not None
        assert result.vehicle_score is not None
        assert result.market_estimation is not None
        assert result.profit_analysis is not None
        assert result.opportunity is not None


# =============================================================================
# Tests de recomendaciones de negociación
# =============================================================================


def _build_scenario(
    price: float,
    market_price: float,
    net_profit: float,
    roi_percentage: float,
    score_value: int = 75,
    supply_level: float = 50.0,
    demand_level: float = 60.0,
    market_trend: str = "stable",
    confidence: float = 70.0,
    repair_estimate: float = 500.0,
    risk_level: ProfitRiskLevel = ProfitRiskLevel.LOW,
) -> tuple[VehicleSearchResult, SearchOrchestrator, AsyncMock]:
    """Construye un escenario de prueba con los parámetros dados.

    Returns:
        Tuple con (dto, orchestrator, vehicle_service_mock).
    """
    dto = VehicleSearchResult(
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
        price=price,
        currency="EUR",
        description="Test vehicle",
        images=["img1.jpg"],
    )

    vehicle_service = AsyncMock()
    vehicle_service.search_from_provider = AsyncMock(return_value=[dto])

    scorer = VehicleScorerStub(score_value=score_value)
    market = MarketEstimatorStub(
        market_price=market_price,
        supply_level=supply_level,
        demand_level=demand_level,
        market_trend=market_trend,
        confidence=confidence,
    )
    profit = ProfitAnalyzerStub(
        purchase_price=price,
        net_profit=net_profit,
        roi_percentage=roi_percentage,
        repair_estimate=repair_estimate,
        risk_level=risk_level,
    )
    finder = OpportunityFinderStub()

    orchestrator = SearchOrchestrator(
        vehicle_service=vehicle_service,
        vehicle_scorer=scorer,
        market_estimator=market,
        profit_analyzer=profit,
        opportunity_finder=finder,
        negotiation_engine=NegotiationEngine(),
    )

    return dto, orchestrator, vehicle_service


@pytest.mark.asyncio
async def test_recommendation_buy() -> None:
    """Escenario: vehículo con recomendación BUY.

    Condiciones para BUY:
        - Descuento necesario ≤ 5% (BUY_MAX_DISCOUNT_NEEDED)
        - O ROI ≥ 5% (MIN_ROI_FOR_BUY) y margen ≥ 10% (MIN_MARGIN_FOR_BUY)

    Para cumplir, usamos un vehículo cuyo precio de venta (asking_price=12000€)
    ya está por debajo del valor de mercado (market_price=15000€), con
    beneficio positivo alto y ROI alto. El descuento necesario será negativo
    o muy pequeño, activando la condición BUY.
    """
    dto, orchestrator, vehicle_service = _build_scenario(
        price=12000.0,       # Precio por debajo del mercado
        market_price=15000.0, # Valor de mercado más alto
        net_profit=4000.0,   # Beneficio positivo alto
        roi_percentage=25.0, # ROI alto
        score_value=90,      # Score alto
        confidence=85.0,     # Confianza alta
        repair_estimate=200.0, # Reparaciones mínimas
    )

    request = SearchRequest(query="BMW", max_results=10, providers=["mobile_de"])

    with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
        results = await orchestrator.search(request)

    assert len(results) == 1
    neg = results[0].negotiation
    assert neg is not None

    # La recomendación debe ser BUY
    assert neg.recommendation == NegotiationRecommendation.BUY, (
        f"Esperaba BUY pero obtuvo {neg.recommendation}. "
        f"Discount needed: {neg.discount_needed:.2f}%, "
        f"Expected profit: {neg.expected_profit:.2f}, "
        f"Expected ROI: {neg.expected_roi:.2f}%"
    )

    # Verificaciones adicionales
    assert neg.recommended_initial_offer > 0
    assert neg.estimated_vehicle_value > 0


@pytest.mark.asyncio
async def test_recommendation_negotiate() -> None:
    """Escenario: vehículo con recomendación NEGOTIATE.

    Condiciones para NEGOTIATE:
        - No es BUY (descuento necesario > 5%)
        - No es WALK_AWAY (descuento necesario < 25%)
        - Apalancamiento suficiente (leverage_score >= NEGOTIATE_MIN_LEVERAGE_SCORE)

    Usamos un vehículo con precio (18000€) ligeramente por encima del valor
    de mercado (16000€) pero con beneficio positivo.
    Para generar apalancamiento: score bajo (45), alta oferta (70), baja demanda (30).
    El descuento necesario debe estar entre 5% y 25%.
    """
    dto, orchestrator, vehicle_service = _build_scenario(
        price=16500.0,       # Precio ligeramente por encima del valor de mercado
        market_price=15500.0, # Valor de mercado
        net_profit=1000.0,   # Beneficio positivo pero bajo
        roi_percentage=4.0,  # ROI por debajo de MIN_ROI_FOR_BUY (5%)
        score_value=45,      # Score bajo → genera apalancamiento
        supply_level=70.0,   # Alta oferta (apalancamiento)
        demand_level=30.0,   # Baja demanda (apalancamiento)
        market_trend="falling",  # Tendencia bajista (apalancamiento)
    )

    request = SearchRequest(query="BMW", max_results=10, providers=["mobile_de"])

    with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
        results = await orchestrator.search(request)

    assert len(results) == 1
    neg = results[0].negotiation
    assert neg is not None

    # La recomendación debe ser NEGOTIATE
    assert neg.recommendation == NegotiationRecommendation.NEGOTIATE, (
        f"Esperaba NEGOTIATE pero obtuvo {neg.recommendation}. "
        f"Leverage: {neg.leverage_score:.2f}, "
        f"Discount needed: {neg.discount_needed:.2f}%"
    )

    # Verificaciones adicionales
    assert neg.leverage_score > 20  # Debe tener algo de apalancamiento
    assert neg.recommended_initial_offer > 0
    assert neg.recommended_counter_offer > neg.recommended_initial_offer


@pytest.mark.asyncio
async def test_recommendation_walk_away() -> None:
    """Escenario: vehículo con recomendación WALK_AWAY.

    Condiciones para WALK_AWAY:
        - Descuento necesario ≥ 25% (WALK_AWAY_MIN_DISCOUNT_NEEDED)
        - O beneficio negativo (net_profit < MIN_PROFIT_FOR_NEGOTIATE)

    Usamos un vehículo con precio muy alto y beneficio negativo.
    """
    dto, orchestrator, vehicle_service = _build_scenario(
        price=25000.0,       # Precio muy alto
        market_price=15000.0, # Valor de mercado bajo
        net_profit=-500.0,   # Beneficio negativo
        roi_percentage=-3.0, # ROI negativo
        score_value=40,      # Score bajo
        risk_level=ProfitRiskLevel.HIGH,  # Riesgo alto
    )

    request = SearchRequest(query="BMW", max_results=10, providers=["mobile_de"])

    with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
        results = await orchestrator.search(request)

    assert len(results) == 1
    neg = results[0].negotiation
    assert neg is not None

    # La recomendación debe ser WALK_AWAY
    assert neg.recommendation == NegotiationRecommendation.WALK_AWAY, (
        f"Esperaba WALK_AWAY pero obtuvo {neg.recommendation}. "
        f"Expected profit: {neg.expected_profit:.2f}, "
        f"Discount needed: {neg.discount_needed:.2f}%"
    )

    # Verificaciones adicionales
    assert neg.walk_away_price > 0
    assert neg.price_gap > 0  # El precio es mayor que el valor estimado


@pytest.mark.asyncio
async def test_recommendation_walk_away_negative_profit() -> None:
    """Escenario: vehículo con beneficio negativo → WALK_AWAY.

    Si el beneficio original de ProfitAnalysis es negativo, la
    negociación debe recomendar WALK_AWAY independientemente del
    descuento necesario.
    """
    dto, orchestrator, vehicle_service = _build_scenario(
        price=15000.0,
        market_price=14000.0,
        net_profit=-200.0,   # Beneficio negativo
        roi_percentage=-1.5, # ROI negativo
        score_value=50,
        risk_level=ProfitRiskLevel.HIGH,
    )

    request = SearchRequest(query="BMW", max_results=10, providers=["mobile_de"])

    with patch.object(ProviderRegistry, "get", return_value=MagicMock()):
        results = await orchestrator.search(request)

    assert len(results) == 1
    neg = results[0].negotiation
    assert neg is not None

    assert neg.recommendation == NegotiationRecommendation.WALK_AWAY, (
        f"Esperaba WALK_AWAY por beneficio negativo pero obtuvo {neg.recommendation}"
    )


# =============================================================================
# Test de compatibilidad del serializador de la API
# =============================================================================


class TestNegotiationSchemaMapping:
    """Verifica que NegotiationResult se mapea correctamente al schema API.

    Estos tests usan la función _build_search_result_item del router
    para asegurar que la serialización funciona correctamente.
    """

    def _build_raw_search_result(self, negotiation: NegotiationResult | None) -> SearchResult:
        """Construye un SearchResult mínimo con negotiation."""
        return SearchResult(
            vehicle=VehicleSearchResult(
                source="mobile_de",
                external_id="12345",
                url="https://example.com/vehicle/12345",
                brand="TestBrand",
                model="TestModel",
                year=2020,
                price=15000.0,
            ),
            vehicle_score=VehicleScore(score=75, category="Muy bueno"),
            market_estimation=MarketEstimation(market_price=18000.0, confidence=70.0),
            profit_analysis=MagicMock(spec=ProfitAnalysis),
            opportunity=MagicMock(spec=OpportunityAnalysis),
            negotiation=negotiation,
        )

    def test_maps_all_recommendations(self) -> None:
        """Verifica que las 3 recomendaciones se mapean correctamente."""
        from app.api.v1.routes.search import _build_search_result_item
        from app.api.v1.schemas.negotiation import NegotiationResultSchema

        for rec in NegotiationRecommendation:
            neg = NegotiationResult(
                estimated_vehicle_value=10000.0,
                recommended_initial_offer=9000.0,
                recommended_counter_offer=9500.0,
                maximum_purchase_price=11000.0,
                walk_away_price=12000.0,
                expected_profit=500.0,
                expected_roi=5.0,
                recommendation=rec,
                leverage_score=50.0,
                price_gap=5000.0,
                discount_needed=10.0,
            )
            search_result = self._build_raw_search_result(neg)
            item = _build_search_result_item(search_result)

            assert item.negotiation is not None
            assert isinstance(item.negotiation, NegotiationResultSchema)
            assert item.negotiation.recommendation == rec.value

    def test_missing_negotiation_is_none(self) -> None:
        """Verifica que si negotiation=None en SearchResult, el item lo refleja."""
        from app.api.v1.routes.search import _build_search_result_item

        search_result = self._build_raw_search_result(None)
        item = _build_search_result_item(search_result)

        assert item.negotiation is None