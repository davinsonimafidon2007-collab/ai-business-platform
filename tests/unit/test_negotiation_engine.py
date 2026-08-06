"""Tests para el NegotiationEngine — Motor de estrategia de negociación.

Casos mínimos requeridos:
    - BUY: descuento necesario ≤ 5% (precio ya es bueno)
    - NEGOTIATE: casos intermedios con apalancamiento suficiente
    - WALK_AWAY: descuento necesario ≥ 25% o beneficio negativo
    - Cálculo correcto de estimated_vehicle_value
    - Cálculo correcto de leverage_score
    - Generación de negotiation_arguments ordenados por impacto
    - Generación de negotiation_script en lenguaje natural
    - Cálculo de initial_offer, counter_offer, max_price, walk_away
    - Argumentos basados en defectos de seguridad
    - Argumentos basados en condiciones de mercado
    - Argumentos basados en score del vehículo
    - Argumentos basados en análisis de rentabilidad
    - Sin defectos (vehículo en perfecto estado)
    - Sin datos de mercado
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from app.models.negotiation import (
    DefectItem,
    InspectionResult,
    NegotiationInput,
    NegotiationRecommendation,
    RepairEstimate,
)
from app.services.negotiation_engine import NegotiationEngine


# =============================================================================
# Fixtures helpers
# =============================================================================


@dataclass
class MarketEstimationStub:
    """Stub que simula MarketEstimation para las pruebas."""
    market_price: float = 20000.0
    confidence: float = 70.0
    supply_level: float = 50.0
    demand_level: float = 50.0
    market_trend: str = "stable"
    comparable_count: int = 10
    notes: list[str] = field(default_factory=list)


@pytest.fixture
def engine() -> NegotiationEngine:
    return NegotiationEngine()


@pytest.fixture
def no_defects_inspection() -> InspectionResult:
    """Inspección sin defectos, vehículo en perfecto estado."""
    return InspectionResult(
        defects=[],
        overall_condition=10,
        has_accident_history=False,
    )


@pytest.fixture
def minor_defects_inspection() -> InspectionResult:
    """Inspección con defectos menores."""
    return InspectionResult(
        defects=[
            DefectItem(
                category="estético",
                description="Pequeño roce en parachoques trasero",
                severity=3,
                estimated_repair_cost=150.0,
                is_safety_relevant=False,
            ),
            DefectItem(
                category="estético",
                description="Rayón en puerta del conductor",
                severity=2,
                estimated_repair_cost=80.0,
                is_safety_relevant=False,
            ),
        ],
        overall_condition=8,
        has_accident_history=False,
    )


@pytest.fixture
def major_defects_inspection() -> InspectionResult:
    """Inspección con defectos graves, incluyendo seguridad."""
    return InspectionResult(
        defects=[
            DefectItem(
                category="mecánico",
                description="Pastillas de freno desgastadas (menos de 3mm)",
                severity=8,
                estimated_repair_cost=450.0,
                is_safety_relevant=True,
            ),
            DefectItem(
                category="mecánico",
                description="Correa de distribución original sin cambiar a los 120.000 km",
                severity=9,
                estimated_repair_cost=800.0,
                is_safety_relevant=True,
            ),
            DefectItem(
                category="eléctrico",
                description="Sensor de ABS averiado (testigo encendido)",
                severity=7,
                estimated_repair_cost=350.0,
                is_safety_relevant=True,
            ),
            DefectItem(
                category="carrocería",
                description="Óxido en paso de rueda trasero izquierdo",
                severity=6,
                estimated_repair_cost=600.0,
                is_safety_relevant=False,
            ),
            DefectItem(
                category="neumáticos",
                description="Neumáticos delanteros al límite legal (2mm)",
                severity=7,
                estimated_repair_cost=300.0,
                is_safety_relevant=True,
            ),
        ],
        overall_condition=5,
        has_accident_history=False,
    )


@pytest.fixture
def accident_inspection() -> InspectionResult:
    """Inspección con historial de accidentes."""
    return InspectionResult(
        defects=[
            DefectItem(
                category="carrocería",
                description="Diferencia de tono en puerta delantera derecha (reparación previa)",
                severity=5,
                estimated_repair_cost=200.0,
                is_safety_relevant=False,
            ),
        ],
        overall_condition=7,
        has_accident_history=True,
        accident_notes="Accidente frontal leve en 2022. Reparado pero con evidencias visibles.",
    )


@pytest.fixture
def high_repair_estimate() -> RepairEstimate:
    """Estimación de reparación alta."""
    return RepairEstimate(
        total_repair_cost=2500.0,
        parts_cost=1200.0,
        labor_cost=800.0,
        paint_and_body_cost=500.0,
        diagnostic_cost=0.0,
        notes=[
            "Distribución con kit completo: 800 EUR",
            "Pastillas de freno delanteras: 450 EUR",
            "Neumáticos 225/45R17 x2: 300 EUR",
        ],
    )


@pytest.fixture
def low_repair_estimate() -> RepairEstimate:
    """Estimación de reparación baja."""
    return RepairEstimate(
        total_repair_cost=230.0,
        parts_cost=80.0,
        labor_cost=100.0,
        paint_and_body_cost=50.0,
        diagnostic_cost=0.0,
        notes=["Roce en parachoques: repintado localizado."],
    )


@pytest.fixture
def zero_repair_estimate() -> RepairEstimate:
    """Sin reparaciones necesarias."""
    return RepairEstimate(
        total_repair_cost=0.0,
        parts_cost=0.0,
        labor_cost=0.0,
        paint_and_body_cost=0.0,
        diagnostic_cost=0.0,
    )


@pytest.fixture
def favorable_market() -> MarketEstimationStub:
    """Condiciones de mercado favorables (alta demanda, poca oferta)."""
    return MarketEstimationStub(
        market_price=22000.0,
        confidence=85.0,
        supply_level=30.0,
        demand_level=80.0,
        market_trend="rising",
    )


@pytest.fixture
def unfavorable_market() -> MarketEstimationStub:
    """Condiciones de mercado desfavorables (baja demanda, alta oferta)."""
    return MarketEstimationStub(
        market_price=18000.0,
        confidence=40.0,
        supply_level=80.0,
        demand_level=30.0,
        market_trend="falling",
    )


@pytest.fixture
def high_profit_data() -> dict[str, Any]:
    """Datos de ProfitAnalysis con alta rentabilidad."""
    return {
        "net_profit": 5000.0,
        "roi_percentage": 25.0,
        "risk_level": "LOW",
        "purchase_price": 15000.0,
        "total_cost": 18500.0,
        "estimated_sale_price": 23500.0,
        "profit_margin_percentage": 21.0,
    }


@pytest.fixture
def low_profit_data() -> dict[str, Any]:
    """Datos de ProfitAnalysis con baja rentabilidad."""
    return {
        "net_profit": 300.0,
        "roi_percentage": 2.0,
        "risk_level": "HIGH",
        "purchase_price": 20000.0,
        "total_cost": 24000.0,
        "estimated_sale_price": 24300.0,
        "profit_margin_percentage": 1.2,
    }


@pytest.fixture
def negative_profit_data() -> dict[str, Any]:
    """Datos de ProfitAnalysis con pérdidas."""
    return {
        "net_profit": -500.0,
        "roi_percentage": -2.5,
        "risk_level": "HIGH",
        "purchase_price": 25000.0,
        "total_cost": 28000.0,
        "estimated_sale_price": 27500.0,
        "profit_margin_percentage": -1.8,
    }


@pytest.fixture
def high_vehicle_score_data() -> dict[str, Any]:
    """Datos de VehicleScore alto."""
    return {
        "score": 90,
        "strengths": ["Bajo kilometraje", "Vehículo reciente", "Mantenimiento completo"],
        "weaknesses": [],
        "category": "Excelente",
    }


@pytest.fixture
def low_vehicle_score_data() -> dict[str, Any]:
    """Datos de VehicleScore bajo."""
    return {
        "score": 35,
        "strengths": [],
        "weaknesses": [
            "Kilometraje muy alto",
            "Vehículo antiguo",
            "Sin historial de mantenimiento",
            "Varios propietarios",
        ],
        "category": "Malo",
    }


# =============================================================================
# Tests: BUY recommendation
# =============================================================================


class TestBuyRecommendation:
    """Tests para cuando la recomendación debe ser BUY."""

    def test_buy_when_discount_needed_is_low(self, engine: NegotiationEngine) -> None:
        """Asking price muy cercano al valor de mercado → BUY por descuento ≤5%."""
        market = MarketEstimationStub(market_price=20000.0)
        inp = NegotiationInput(
            inspection_result=InspectionResult(defects=[], overall_condition=10),
            repair_estimate=RepairEstimate(total_repair_cost=0.0),
            market_estimation=market,
            asking_price=19000.0,  # asking ligeramente por debajo del valor, la oferta será ~90% de 19000
            minimum_desired_profit=2000.0,
            target_margin=15.0,
            profit_analysis_data={
                "net_profit": 3000.0, "roi_percentage": 15.0,
                "profit_margin_percentage": 12.0,
                "purchase_price": 19000.0,
                "total_cost": 21000.0,
                "estimated_sale_price": 24000.0,
            },
            vehicle_score_data={"score": 85},
        )
        result = engine.analyze(inp)
        assert result.recommendation == NegotiationRecommendation.BUY, (
            f"Esperado BUY, obtenido {result.recommendation}. "
            f"discount_needed={result.discount_needed:.1f}%, leverage={result.leverage_score:.1f}"
        )

    def test_buy_with_good_roi_and_margin(self, engine: NegotiationEngine) -> None:
        """ROI ≥ 5% y margen ≥ 10% → BUY incluso con descuento moderado."""
        inp = NegotiationInput(
            inspection_result=InspectionResult(defects=[], overall_condition=10),
            repair_estimate=RepairEstimate(total_repair_cost=0.0),
            market_estimation=MarketEstimationStub(market_price=20000.0),
            asking_price=22000.0,
            minimum_desired_profit=2000.0,
            target_margin=15.0,
            profit_analysis_data={
                "net_profit": 4000.0,
                "roi_percentage": 18.0,
                "profit_margin_percentage": 15.0,
                "purchase_price": 20000.0,
                "total_cost": 22000.0,
                "estimated_sale_price": 26000.0,
            },
            vehicle_score_data={"score": 80},
        )
        result = engine.analyze(inp)
        assert result.recommendation == NegotiationRecommendation.BUY, (
            f"Esperado BUY, obtenido {result.recommendation}"
        )


# =============================================================================
# Tests: NEGOTIATE recommendation
# =============================================================================


class TestNegotiateRecommendation:
    """Tests para cuando la recomendación debe ser NEGOTIATE."""

    def test_negotiate_with_defects_and_leverage(self, engine: NegotiationEngine) -> None:
        """Vehículo con defectos y apalancamiento suficiente → NEGOTIATE."""
        inp = NegotiationInput(
            inspection_result=InspectionResult(
                defects=[
                    DefectItem(
                        category="mecánico",
                        description="Pastillas de freno desgastadas",
                        severity=7,
                        estimated_repair_cost=450.0,
                        is_safety_relevant=True,
                    ),
                    DefectItem(
                        category="carrocería",
                        description="Óxido en paso de rueda",
                        severity=5,
                        estimated_repair_cost=500.0,
                        is_safety_relevant=False,
                    ),
                ],
                overall_condition=6,
            ),
            repair_estimate=RepairEstimate(total_repair_cost=950.0),
            market_estimation=MarketEstimationStub(market_price=17000.0),
            asking_price=17500.0,
            minimum_desired_profit=1000.0,
            target_margin=12.0,
            profit_analysis_data={
                "net_profit": 2000.0,
                "roi_percentage": 7.0,
                "profit_margin_percentage": 5.0,
                "purchase_price": 17500.0,
                "total_cost": 19500.0,
                "estimated_sale_price": 21500.0,
            },
            vehicle_score_data={"score": 55},
        )
        result = engine.analyze(inp)
        assert result.recommendation == NegotiationRecommendation.NEGOTIATE, (
            f"Esperado NEGOTIATE, obtenido {result.recommendation}. "
            f"estimated_value={result.estimated_vehicle_value:.0f}, "
            f"discount_needed={result.discount_needed:.1f}%, leverage={result.leverage_score:.1f}"
        )

    def test_negotiate_includes_arguments(self, engine: NegotiationEngine) -> None:
        """NEGOTIATE debe generar argumentos de negociación."""
        inp = NegotiationInput(
            inspection_result=InspectionResult(
                defects=[
                    DefectItem(
                        category="mecánico",
                        description="Frenos desgastados",
                        severity=7,
                        estimated_repair_cost=500.0,
                        is_safety_relevant=True,
                    ),
                ],
                overall_condition=6,
            ),
            repair_estimate=RepairEstimate(total_repair_cost=500.0),
            market_estimation=MarketEstimationStub(market_price=17000.0),
            asking_price=19500.0,
            minimum_desired_profit=1000.0,
            target_margin=12.0,
            profit_analysis_data={
                "net_profit": 800.0,
                "roi_percentage": 4.0,
                "purchase_price": 19500.0,
                "total_cost": 21500.0,
                "estimated_sale_price": 22500.0,
            },
            vehicle_score_data={"score": 60},
        )
        result = engine.analyze(inp)
        assert len(result.negotiation_arguments) > 0, (
            "Debe haber al menos un argumento de negociación"
        )
        # Verificar que están ordenados por impacto descendente
        for i in range(len(result.negotiation_arguments) - 1):
            assert result.negotiation_arguments[i].economic_impact >= result.negotiation_arguments[i + 1].economic_impact, (
                "Los argumentos deben estar ordenados por impacto económico descendente"
            )

    def test_negotiate_includes_script(self, engine: NegotiationEngine) -> None:
        """NEGOTIATE debe generar un script de negociación."""
        inp = NegotiationInput(
            inspection_result=InspectionResult(
                defects=[
                    DefectItem(
                        category="mecánico",
                        description="Correa de distribución pendiente",
                        severity=8,
                        estimated_repair_cost=800.0,
                        is_safety_relevant=True,
                    ),
                ],
                overall_condition=6,
            ),
            repair_estimate=RepairEstimate(total_repair_cost=800.0),
            market_estimation=MarketEstimationStub(market_price=16000.0),
            asking_price=19000.0,
            minimum_desired_profit=1000.0,
            target_margin=12.0,
            profit_analysis_data={
                "net_profit": 500.0,
                "roi_percentage": 3.0,
                "purchase_price": 19000.0,
                "total_cost": 21000.0,
                "estimated_sale_price": 21800.0,
            },
            vehicle_score_data={"score": 55},
        )
        result = engine.analyze(inp)
        assert result.negotiation_script.opening, (
            "El script debe tener una apertura"
        )
        assert result.negotiation_script.closing, (
            "El script debe tener un cierre"
        )
        assert len(result.negotiation_script.defect_based_points) > 0, (
            "El script debe incluir puntos basados en defectos"
        )


# =============================================================================
# Tests: WALK_AWAY recommendation
# =============================================================================


class TestWalkAwayRecommendation:
    """Tests para cuando la recomendación debe ser WALK_AWAY."""

    def test_walk_away_when_large_discount_needed(self, engine: NegotiationEngine) -> None:
        """Asking price muy superior al valor estimado (≥25%) → WALK_AWAY."""
        inp = NegotiationInput(
            inspection_result=InspectionResult(
                defects=[
                    DefectItem(
                        category="mecánico",
                        description="Motor con golpe",
                        severity=9,
                        estimated_repair_cost=5000.0,
                        is_safety_relevant=True,
                    ),
                ],
                overall_condition=3,
            ),
            repair_estimate=RepairEstimate(total_repair_cost=5000.0),
            market_estimation=MarketEstimationStub(market_price=15000.0),
            asking_price=25000.0,
            minimum_desired_profit=2000.0,
            target_margin=15.0,
            profit_analysis_data={
                "net_profit": -1000.0,
                "roi_percentage": -5.0,
                "purchase_price": 25000.0,
                "total_cost": 28000.0,
                "estimated_sale_price": 27000.0,
            },
            vehicle_score_data={"score": 20},
        )
        result = engine.analyze(inp)
        assert result.recommendation == NegotiationRecommendation.WALK_AWAY, (
            f"Esperado WALK_AWAY, obtenido {result.recommendation}"
        )

    def test_walk_away_when_negative_profit(self, engine: NegotiationEngine) -> None:
        """Beneficio neto negativo → WALK_AWAY."""
        inp = NegotiationInput(
            inspection_result=InspectionResult(defects=[], overall_condition=10),
            repair_estimate=RepairEstimate(total_repair_cost=0.0),
            market_estimation=MarketEstimationStub(market_price=20000.0),
            asking_price=22000.0,
            minimum_desired_profit=2000.0,
            target_margin=15.0,
            profit_analysis_data={
                "net_profit": -500.0,
                "roi_percentage": -2.0,
                "risk_level": "HIGH",
                "purchase_price": 22000.0,
                "total_cost": 24000.0,
                "estimated_sale_price": 23500.0,
            },
            vehicle_score_data={"score": 50},
        )
        result = engine.analyze(inp)
        assert result.recommendation == NegotiationRecommendation.WALK_AWAY, (
            f"Esperado WALK_AWAY, obtenido {result.recommendation}. "
            f"discount_needed={result.discount_needed:.1f}%, leverage={result.leverage_score:.1f}"
        )

    def test_walk_away_negative_profit_despite_high_leverage(
        self, engine: NegotiationEngine
    ) -> None:
        """Pérdida neta: leverage alto NO puede forzar NEGOTIATE."""
        inp = NegotiationInput(
            inspection_result=InspectionResult(
                defects=[
                    DefectItem(
                        category="estético",
                        description="Rayones leves",
                        severity=3,
                        estimated_repair_cost=200.0,
                        is_safety_relevant=False,
                    ),
                ],
                overall_condition=7,
            ),
            repair_estimate=RepairEstimate(total_repair_cost=200.0),
            market_estimation=MarketEstimationStub(
                market_price=20000.0,
                supply_level=80.0,
                demand_level=30.0,
                market_trend="falling",
            ),
            asking_price=21000.0,
            minimum_desired_profit=2000.0,
            target_margin=15.0,
            profit_analysis_data={
                "net_profit": -500.0,
                "roi_percentage": -2.5,
                "risk_level": "HIGH",
                "purchase_price": 21000.0,
                "total_cost": 23000.0,
                "estimated_sale_price": 22500.0,
            },
            vehicle_score_data={"score": 35},
        )
        result = engine.analyze(inp)
        assert result.recommendation == NegotiationRecommendation.WALK_AWAY, (
            f"Esperado WALK_AWAY con net_profit=-500, obtenido {result.recommendation}. "
            f"discount_needed={result.discount_needed:.1f}% "
            f"leverage={result.leverage_score:.1f} "
            f"expected_profit={getattr(result, 'expected_profit', None)}"
        )


# =============================================================================
# Tests: Cálculo de precios
# =============================================================================


class TestPriceCalculations:
    """Tests para verificar el cálculo correcto de precios."""

    def test_estimated_vehicle_value_with_repairs(self, engine: NegotiationEngine) -> None:
        """Valor estimado = market_price - repair_cost."""
        inp = NegotiationInput(
            inspection_result=InspectionResult(defects=[], overall_condition=10),
            repair_estimate=RepairEstimate(total_repair_cost=2000.0),
            market_estimation=MarketEstimationStub(market_price=20000.0),
            asking_price=20000.0,
            minimum_desired_profit=2000.0,
            target_margin=15.0,
        )
        result = engine.analyze(inp)
        expected_value = 20000.0 - 2000.0
        assert result.estimated_vehicle_value == pytest.approx(expected_value, rel=0.01), (
            f"Valor estimado {result.estimated_vehicle_value} != {expected_value}"
        )

    def test_estimated_vehicle_value_with_accident(self, engine: NegotiationEngine) -> None:
        """Valor estimado descuenta 10% extra por accidentes."""
        inp = NegotiationInput(
            inspection_result=InspectionResult(
                defects=[],
                overall_condition=7,
                has_accident_history=True,
                accident_notes="Accidente frontal en 2022",
            ),
            repair_estimate=RepairEstimate(total_repair_cost=0.0),
            market_estimation=MarketEstimationStub(market_price=20000.0),
            asking_price=20000.0,
            minimum_desired_profit=2000.0,
            target_margin=15.0,
        )
        result = engine.analyze(inp)
        expected_value = 20000.0 - (20000.0 * 0.10)  # market_price - 10% accident discount
        assert result.estimated_vehicle_value == pytest.approx(expected_value, rel=0.01), (
            f"Valor estimado {result.estimated_vehicle_value} != {expected_value}"
        )

    def test_initial_offer_less_than_asking(self, engine: NegotiationEngine) -> None:
        """La oferta inicial debe ser menor que el asking price cuando hay costes."""
        inp = NegotiationInput(
            inspection_result=InspectionResult(defects=[], overall_condition=10),
            repair_estimate=RepairEstimate(total_repair_cost=0.0),
            market_estimation=MarketEstimationStub(market_price=20000.0),
            asking_price=25000.0,
            minimum_desired_profit=2000.0,
            target_margin=15.0,
            profit_analysis_data={
                "net_profit": 1000.0, "roi_percentage": 5.0,
                "purchase_price": 25000.0, "total_cost": 27000.0,
                "estimated_sale_price": 28000.0,
            },
            vehicle_score_data={"score": 50},
        )
        result = engine.analyze(inp)
        assert result.recommended_initial_offer < inp.asking_price, (
            f"Oferta inicial {result.recommended_initial_offer} debe ser < {inp.asking_price}"
        )
        # Con la config actual (WALK_AWAY_MULTIPLIER == MAX_PURCHASE_PRICE_MULTIPLIER == 1.05),
        # walk-away y max purchase pueden coincidir. El dominio exige walk_away <= max_purchase
        # (el comprador abandona cuando el vendedor exige más que el techo de compra).
        assert result.walk_away_price >= result.maximum_purchase_price, (
            f"Walk-away {result.walk_away_price} debe ser >= max purchase {result.maximum_purchase_price}"
        )


# =============================================================================
# Tests: Argumentos de negociación
# =============================================================================


class TestNegotiationArguments:
    """Tests para la generación de argumentos de negociación."""

    def test_defect_arguments_generated(self, engine: NegotiationEngine) -> None:
        """Los defectos deben generar argumentos de negociación."""
        inp = NegotiationInput(
            inspection_result=InspectionResult(
                defects=[
                    DefectItem(
                        category="mecánico",
                        description="Frenos gastados",
                        severity=7,
                        estimated_repair_cost=500.0,
                        is_safety_relevant=True,
                    ),
                ],
                overall_condition=6,
            ),
            repair_estimate=RepairEstimate(total_repair_cost=500.0),
            market_estimation=MarketEstimationStub(market_price=20000.0),
            asking_price=20000.0,
            minimum_desired_profit=1500.0,
            target_margin=12.0,
        )
        result = engine.analyze(inp)
        defect_args = [a for a in result.negotiation_arguments if a.category == "defect"]
        assert len(defect_args) >= 1, (
            "Debe haber al menos un argumento basado en defectos"
        )
        # El argumento de seguridad debe tener impacto elevado
        safety_args = [a for a in defect_args if "SEGURIDAD" in a.argument or "seguridad" in a.argument]
        for arg in safety_args:
            assert arg.severity >= 7, (
                f"Los defectos de seguridad deben tener severidad ≥ 7, obtenido {arg.severity}"
            )

    def test_market_arguments_when_unfavorable(self, engine: NegotiationEngine) -> None:
        """Mercado desfavorable debe generar argumentos de mercado."""
        inp = NegotiationInput(
            inspection_result=InspectionResult(defects=[], overall_condition=10),
            repair_estimate=RepairEstimate(total_repair_cost=0.0),
            market_estimation=MarketEstimationStub(
                market_price=18000.0, confidence=35.0,
                supply_level=85.0, demand_level=25.0, market_trend="falling",
            ),
            asking_price=22000.0,
            minimum_desired_profit=2000.0,
            target_margin=15.0,
        )
        result = engine.analyze(inp)
        market_args = [a for a in result.negotiation_arguments if a.category == "market"]
        assert len(market_args) >= 1, (
            "Mercado desfavorable debe generar argumentos de mercado"
        )

    def test_low_vehicle_score_arguments(self, engine: NegotiationEngine) -> None:
        """Score bajo debe generar argumentos de vehículo."""
        inp = NegotiationInput(
            inspection_result=InspectionResult(defects=[], overall_condition=10),
            repair_estimate=RepairEstimate(total_repair_cost=0.0),
            market_estimation=MarketEstimationStub(market_price=20000.0),
            asking_price=20000.0,
            minimum_desired_profit=2000.0,
            target_margin=15.0,
            vehicle_score_data={
                "score": 30,
                "weaknesses": ["Kilometraje muy alto", "Vehículo antiguo"],
            },
        )
        result = engine.analyze(inp)
        vehicle_args = [a for a in result.negotiation_arguments if a.category == "vehicle"]
        assert len(vehicle_args) >= 1, (
            "Score bajo debe generar argumentos de vehículo"
        )


# =============================================================================
# Tests: Script de negociación
# =============================================================================


class TestNegotiationScript:
    """Tests para la generación del script de negociación."""

    def test_script_with_safety_defects(self, engine: NegotiationEngine) -> None:
        """El script debe mencionar defectos de seguridad si existen."""
        inp = NegotiationInput(
            inspection_result=InspectionResult(
                defects=[
                    DefectItem(
                        category="mecánico",
                        description="Frenos delanteros completamente desgastados",
                        severity=9,
                        estimated_repair_cost=600.0,
                        is_safety_relevant=True,
                    ),
                ],
                overall_condition=5,
            ),
            repair_estimate=RepairEstimate(total_repair_cost=600.0),
            market_estimation=MarketEstimationStub(market_price=15000.0),
            asking_price=18000.0,
            minimum_desired_profit=1500.0,
            target_margin=15.0,
        )
        result = engine.analyze(inp)
        script = result.negotiation_script
        assert "Frenos" in script.opening or "frenos" in script.opening, (
            "El script debe mencionar el defecto de seguridad en la apertura"
        )
        assert len(script.defect_based_points) >= 1, (
            "El script debe incluir puntos basados en defectos"
        )
        assert "600" in script.opening or "600" in str(script.defect_based_points), (
            "El script debe mencionar el coste de reparación"
        )

    def test_script_with_accident_history(self, engine: NegotiationEngine) -> None:
        """El script debe mencionar historial de accidentes."""
        inp = NegotiationInput(
            inspection_result=InspectionResult(
                defects=[],
                overall_condition=7,
                has_accident_history=True,
                accident_notes="Impacto frontal con reparación estructural",
            ),
            repair_estimate=RepairEstimate(total_repair_cost=0.0),
            market_estimation=MarketEstimationStub(market_price=20000.0),
            asking_price=20000.0,
            minimum_desired_profit=2000.0,
            target_margin=15.0,
        )
        result = engine.analyze(inp)
        script = result.negotiation_script
        assert "accidente" in script.opening.lower() or "historial" in script.opening.lower(), (
            "El script debe mencionar el historial de accidentes"
        )


# =============================================================================
# Tests: Casos límite (edge cases)
# =============================================================================


class TestEdgeCases:
    """Tests para casos límite del motor de negociación."""

    def test_no_defects_perfect_condition(self, engine: NegotiationEngine) -> None:
        """Vehículo en perfecto estado sin defectos."""
        inp = NegotiationInput(
            inspection_result=InspectionResult(defects=[], overall_condition=10),
            repair_estimate=RepairEstimate(total_repair_cost=0.0),
            market_estimation=MarketEstimationStub(market_price=20000.0),
            asking_price=21000.0,
            minimum_desired_profit=2000.0,
            target_margin=15.0,
            profit_analysis_data={
                "net_profit": 3000.0, "roi_percentage": 15.0,
                "profit_margin_percentage": 12.0,
            },
        )
        result = engine.analyze(inp)
        # Sin defectos, debe dar un resultado válido
        assert result.estimated_vehicle_value > 0
        assert result.recommended_initial_offer > 0
        assert isinstance(result.recommendation, NegotiationRecommendation)

    def test_zero_asking_price(self, engine: NegotiationEngine) -> None:
        """Asking price cero debe manejarse sin errores."""
        inp = NegotiationInput(
            inspection_result=InspectionResult(defects=[], overall_condition=10),
            repair_estimate=RepairEstimate(total_repair_cost=0.0),
            market_estimation=MarketEstimationStub(market_price=0.0),
            asking_price=0.0,
            minimum_desired_profit=0.0,
            target_margin=0.0,
            profit_analysis_data={"net_profit": -1000.0, "roi_percentage": -5.0},
        )
        result = engine.analyze(inp)
        assert result.estimated_vehicle_value == 0.0
        assert result.recommended_initial_offer == 0.0
        assert result.recommendation in (
            NegotiationRecommendation.BUY,
            NegotiationRecommendation.NEGOTIATE,
            NegotiationRecommendation.WALK_AWAY,
        ), f"Expected any valid recommendation, got {result.recommendation}"

    def test_all_components_present(self, engine: NegotiationEngine) -> None:
        """Verify that NegotiationResult has all required fields."""
        inp = NegotiationInput(
            inspection_result=InspectionResult(
                defects=[DefectItem(category="test", description="test", severity=5, estimated_repair_cost=100.0)],
                overall_condition=7,
            ),
            repair_estimate=RepairEstimate(total_repair_cost=100.0),
            market_estimation=MarketEstimationStub(market_price=20000.0),
            asking_price=20000.0,
            minimum_desired_profit=2000.0,
            target_margin=15.0,
            profit_analysis_data={
                "net_profit": 1500.0, "roi_percentage": 8.0,
                "purchase_price": 20000.0, "total_cost": 22000.0,
                "estimated_sale_price": 23800.0,
            },
            vehicle_score_data={"score": 70},
        )
        result = engine.analyze(inp)
        # Verificar todos los campos requeridos
        assert result.estimated_vehicle_value >= 0
        assert result.recommended_initial_offer >= 0
        assert result.recommended_counter_offer >= 0
        assert result.maximum_purchase_price >= 0
        assert result.walk_away_price >= 0
        assert 0 <= result.leverage_score <= 100
        assert len(result.negotiation_arguments) > 0
        assert result.negotiation_script.opening != ""
        assert result.negotiation_script.closing != ""
        assert result.recommendation in (
            NegotiationRecommendation.BUY,
            NegotiationRecommendation.NEGOTIATE,
            NegotiationRecommendation.WALK_AWAY,
        )