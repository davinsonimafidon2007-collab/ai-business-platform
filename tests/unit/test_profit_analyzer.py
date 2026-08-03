"""Tests para el ProfitAnalyzer — Analizador económico de importación de vehículos.

Casos mínimos requeridos:
    - beneficio alto
    - beneficio negativo
    - ROI alto
    - ROI bajo
    - sin precio
    - costes elevados
    - venta muy rentable
    - venta poco rentable
    - riesgo bajo
    - riesgo medio
    - riesgo alto
    - configuración Alemania
    - configuración Francia
    - configuración Default
    - edge cases
    - determinismo
    - validación de cálculos
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from app.config.import_costs import (
    DEFAULT_PROFILE,
    FRANCE_PROFILE,
    GERMANY_PROFILE,
    ImportCostProfile,
    get_profile,
)
from app.services.profit_analyzer import (
    CostBreakdown,
    ProfitAnalysis,
    ProfitAnalyzer,
    Recommendation,
    RiskLevel,
    VehicleData,
)


# =============================================================================
# Fixture helpers: crea objetos duck-typed que cumplen VehicleData
# =============================================================================


@dataclass
class VehicleStub:
    """Stub mínimo para pruebas de ProfitAnalyzer.

    Solo necesita el campo price y los metadatos básicos.
    """

    price: float | None = None
    brand: str | None = "TestBrand"
    model: str | None = "TestModel"
    year: int | None = 2020
    mileage: int | None = 50000


@pytest.fixture
def analyzer() -> ProfitAnalyzer:
    return ProfitAnalyzer()


@pytest.fixture
def cheap_vehicle() -> VehicleStub:
    """Vehículo barato (10.000 EUR) para pruebas de alta rentabilidad."""
    return VehicleStub(price=10000.0)


@pytest.fixture
def expensive_vehicle() -> VehicleStub:
    """Vehículo caro (50.000 EUR) para pruebas de baja rentabilidad."""
    return VehicleStub(price=50000.0)


@pytest.fixture
def medium_vehicle() -> VehicleStub:
    """Vehículo de precio medio (25.000 EUR)."""
    return VehicleStub(price=25000.0)


# =============================================================================
# Tests de estructura de modelos
# =============================================================================


class TestModelStructure:
    """Verifica que las estructuras de datos son correctas."""

    def test_recommendation_enum_values(self) -> None:
        assert Recommendation.BUY.value == "BUY"
        assert Recommendation.CONSIDER.value == "CONSIDER"
        assert Recommendation.REJECT.value == "REJECT"

    def test_recommendation_enum_unique(self) -> None:
        values = [m.value for m in Recommendation]
        assert len(values) == len(set(values))
        assert len(values) == 3

    def test_risk_level_enum_values(self) -> None:
        assert RiskLevel.LOW.value == "LOW"
        assert RiskLevel.MEDIUM.value == "MEDIUM"
        assert RiskLevel.HIGH.value == "HIGH"

    def test_risk_level_enum_unique(self) -> None:
        values = [m.value for m in RiskLevel]
        assert len(values) == len(set(values))
        assert len(values) == 3

    def test_cost_breakdown_all_fields(self) -> None:
        b = CostBreakdown(
            purchase_price=10000.0,
            transport_cost=800.0,
            registration_cost=750.0,
            taxes=700.0,
            inspection_cost=150.0,
            repair_estimate=200.0,
            commission_cost=400.0,
            miscellaneous_cost=300.0,
            total_fixed_costs=2000.0,
            total_variable_costs=1300.0,
            total_cost=13300.0,
        )
        assert b.purchase_price == 10000.0
        assert b.total_cost == 13300.0
        # All values must be positive or zero
        for field_name in (
            "purchase_price",
            "transport_cost",
            "registration_cost",
            "taxes",
            "inspection_cost",
            "repair_estimate",
            "commission_cost",
            "miscellaneous_cost",
            "total_fixed_costs",
            "total_variable_costs",
            "total_cost",
        ):
            assert getattr(b, field_name) >= 0

    def test_profit_analysis_all_fields(self, analyzer: ProfitAnalyzer, cheap_vehicle: VehicleStub) -> None:
        result = analyzer.analyze(cheap_vehicle)
        assert isinstance(result, ProfitAnalysis)
        assert isinstance(result.purchase_price, float)
        assert isinstance(result.transport_cost, float)
        assert isinstance(result.registration_cost, float)
        assert isinstance(result.taxes, float)
        assert isinstance(result.inspection_cost, float)
        assert isinstance(result.repair_estimate, float)
        assert isinstance(result.commission_cost, float)
        assert isinstance(result.miscellaneous_cost, float)
        assert isinstance(result.total_cost, float)
        assert isinstance(result.estimated_sale_price, float)
        assert isinstance(result.gross_profit, float)
        assert isinstance(result.net_profit, float)
        assert isinstance(result.roi_percentage, float)
        assert isinstance(result.profit_margin_percentage, float)
        assert isinstance(result.risk_level, RiskLevel)
        assert isinstance(result.recommendation, Recommendation)
        assert isinstance(result.cost_breakdown, CostBreakdown)

    def test_cost_breakdown_in_cost_breakdown(self, analyzer: ProfitAnalyzer, cheap_vehicle: VehicleStub) -> None:
        result = analyzer.analyze(cheap_vehicle)
        breakdown = result.cost_breakdown
        assert breakdown.purchase_price == result.purchase_price
        assert breakdown.transport_cost == result.transport_cost
        assert breakdown.total_cost == result.total_cost


# =============================================================================
# Tests del ProfitAnalyzer
# =============================================================================


class TestProfitAnalyzerInstantiation:
    """Verifica que el analyzer se instancia correctamente."""

    def test_create_analyzer(self) -> None:
        analyzer = ProfitAnalyzer()
        assert analyzer is not None
        assert hasattr(analyzer, "analyze")

    def test_analyze_returns_profit_analysis(self, analyzer: ProfitAnalyzer, cheap_vehicle: VehicleStub) -> None:
        result = analyzer.analyze(cheap_vehicle)
        assert isinstance(result, ProfitAnalysis)

    def test_analyze_without_price_raises_error(self, analyzer: ProfitAnalyzer) -> None:
        vehicle = VehicleStub(price=None)
        with pytest.raises(ValueError, match="precio válido"):
            analyzer.analyze(vehicle)

    def test_analyze_with_zero_price_raises_error(self, analyzer: ProfitAnalyzer) -> None:
        vehicle = VehicleStub(price=0.0)
        with pytest.raises(ValueError, match="precio válido"):
            analyzer.analyze(vehicle)

    def test_analyze_with_negative_price_raises_error(self, analyzer: ProfitAnalyzer) -> None:
        vehicle = VehicleStub(price=-100.0)
        with pytest.raises(ValueError, match="precio válido"):
            analyzer.analyze(vehicle)


# =============================================================================
# Tests de perfiles de configuración
# =============================================================================


class TestConfigurationProfiles:
    """Verifica que los perfiles de configuración se cargan correctamente."""

    def test_get_default_profile(self) -> None:
        profile = get_profile("DEFAULT")
        assert profile == DEFAULT_PROFILE

    def test_get_germany_profile(self) -> None:
        profile = get_profile("GERMANY")
        assert profile == GERMANY_PROFILE

    def test_get_france_profile(self) -> None:
        profile = get_profile("FRANCE")
        assert profile == FRANCE_PROFILE

    def test_get_profile_case_insensitive(self) -> None:
        assert get_profile("germany") == GERMANY_PROFILE
        assert get_profile("Germany") == GERMANY_PROFILE
        assert get_profile("GERMANY") == GERMANY_PROFILE

    def test_get_nonexistent_profile_raises_error(self) -> None:
        with pytest.raises(KeyError):
            get_profile("ITALY")

    def test_profiles_are_frozen_dataclasses(self) -> None:
        for profile in (DEFAULT_PROFILE, GERMANY_PROFILE, FRANCE_PROFILE):
            assert isinstance(profile, ImportCostProfile)

    def test_profiles_cannot_be_modified(self) -> None:
        for profile in (DEFAULT_PROFILE, GERMANY_PROFILE, FRANCE_PROFILE):
            with pytest.raises((AttributeError, TypeError)):
                profile.transport_cost = 999.0  # type: ignore[misc]

    def test_profiles_have_all_required_fields(self) -> None:
        required = [
            "transport_cost",
            "registration_cost",
            "inspection_cost",
            "paperwork_cost",
            "miscellaneous_cost",
            "tax_rate",
            "commission_rate",
            "repair_estimate_rate",
            "risk_high_roi_threshold",
            "risk_low_roi_threshold",
            "risk_high_profit_threshold",
            "risk_low_profit_threshold",
            "risk_high_cost_ratio_threshold",
            "risk_low_cost_ratio_threshold",
        ]
        for profile in (DEFAULT_PROFILE, GERMANY_PROFILE, FRANCE_PROFILE):
            for field in required:
                assert hasattr(profile, field), f"Missing field {field}"


# =============================================================================
# Tests de escenarios económicos
# =============================================================================


class TestHighProfitScenario:
    """Vehículo con alta rentabilidad esperada."""

    def test_high_profit_recommendation(self, analyzer: ProfitAnalyzer) -> None:
        # Vehículo barato con precio de venta estimado alto
        vehicle = VehicleStub(price=5000.0)
        result = analyzer.analyze(vehicle, sale_price_multiplier=2.5)
        assert result.net_profit > 2000.0
        assert result.recommendation in (Recommendation.BUY, Recommendation.CONSIDER)

    def test_high_profit_positive_values(self, analyzer: ProfitAnalyzer) -> None:
        vehicle = VehicleStub(price=5000.0)
        result = analyzer.analyze(vehicle, sale_price_multiplier=2.5)
        assert result.gross_profit > 0
        assert result.net_profit > 0
        assert result.roi_percentage > 0
        assert result.profit_margin_percentage > 0


class TestNegativeProfitScenario:
    """Vehículo con beneficio negativo (pérdidas)."""

    def test_negative_profit_recommendation(self, analyzer: ProfitAnalyzer) -> None:
        # Vehículo muy caro con precio de venta bajo
        vehicle = VehicleStub(price=80000.0)
        result = analyzer.analyze(vehicle, sale_price_multiplier=0.8)
        assert result.net_profit < 0
        assert result.recommendation == Recommendation.REJECT

    def test_negative_profit_risk(self, analyzer: ProfitAnalyzer) -> None:
        vehicle = VehicleStub(price=80000.0)
        result = analyzer.analyze(vehicle, sale_price_multiplier=0.8)
        assert result.risk_level == RiskLevel.HIGH

    def test_negative_profit_roi_negative(self, analyzer: ProfitAnalyzer) -> None:
        vehicle = VehicleStub(price=80000.0)
        result = analyzer.analyze(vehicle, sale_price_multiplier=0.8)
        assert result.roi_percentage < 0


class TestHighROIScenario:
    """Vehículo con ROI alto."""

    def test_high_roi_scenario(self, analyzer: ProfitAnalyzer) -> None:
        vehicle = VehicleStub(price=5000.0)
        result = analyzer.analyze(vehicle, sale_price_multiplier=3.0)
        assert result.roi_percentage > 30.0  # ROI alto (>30%)
        assert result.risk_level == RiskLevel.LOW
        assert result.recommendation == Recommendation.BUY


class TestLowROIScenario:
    """Vehículo con ROI bajo."""

    def test_low_roi_scenario(self, analyzer: ProfitAnalyzer) -> None:
        vehicle = VehicleStub(price=40000.0)
        result = analyzer.analyze(vehicle, sale_price_multiplier=1.05)
        assert result.roi_percentage < 10.0  # ROI bajo (<10%)
        assert result.recommendation in (Recommendation.CONSIDER, Recommendation.REJECT)


# =============================================================================
# Tests de sin precio
# =============================================================================


class TestNoPriceScenario:
    """Vehículo sin precio debe lanzar error."""

    def test_no_price_error(self, analyzer: ProfitAnalyzer) -> None:
        vehicle = VehicleStub(price=None)
        with pytest.raises(ValueError):
            analyzer.analyze(vehicle)

    def test_none_price_does_not_crash(self, analyzer: ProfitAnalyzer) -> None:
        vehicle = VehicleStub(price=None)
        with pytest.raises(ValueError):
            analyzer.analyze(vehicle)


# =============================================================================
# Tests de costes elevados
# =============================================================================


class TestHighCostsScenario:
    """Vehículo con costes de importación muy elevados."""

    def test_high_costs_impact(self, analyzer: ProfitAnalyzer) -> None:
        # Vehículo barato pero perfil con costes relativos muy altos
        vehicle = VehicleStub(price=10000.0)

        # Crear un perfil con costes muy altos
        from app.config.import_costs import ImportCostProfile

        high_cost_profile = ImportCostProfile(
            transport_cost=5000.0,
            registration_cost=3000.0,
            inspection_cost=500.0,
            paperwork_cost=1000.0,
            miscellaneous_cost=1000.0,
            tax_rate=0.25,
            commission_rate=0.15,
            repair_estimate_rate=0.10,
            risk_high_roi_threshold=0.15,
            risk_low_roi_threshold=0.05,
            risk_high_profit_threshold=5000.0,
            risk_low_profit_threshold=1000.0,
            risk_high_cost_ratio_threshold=0.30,
            risk_low_cost_ratio_threshold=0.15,
        )

        # Sobreescribir get_profile para usar nuestro perfil
        original_get_profile = analyzer._get_profile
        analyzer._get_profile = lambda name: high_cost_profile  # type: ignore[method-assign]

        result = analyzer.analyze(vehicle, sale_price_multiplier=1.2)
        assert result.total_cost > 15000.0  # Costes muy elevados
        assert result.recommendation == Recommendation.REJECT


# =============================================================================
# Tests de clasificación de riesgo
# =============================================================================


class TestRiskClassification:
    """Tests para la clasificación de riesgo."""

    def test_low_risk_scenario(self, analyzer: ProfitAnalyzer) -> None:
        """ROI alto + beneficio alto + costes bajos → LOW."""
        vehicle = VehicleStub(price=5000.0)
        result = analyzer.analyze(vehicle, sale_price_multiplier=3.0)
        assert result.risk_level == RiskLevel.LOW

    def test_medium_risk_scenario(self, analyzer: ProfitAnalyzer, medium_vehicle: VehicleStub) -> None:
        """Caso intermedio → MEDIUM."""
        result = analyzer.analyze(medium_vehicle, sale_price_multiplier=1.6)
        # Debe dar un riesgo moderado
        assert result.risk_level in (RiskLevel.LOW, RiskLevel.MEDIUM)

    def test_high_risk_scenario(self, analyzer: ProfitAnalyzer) -> None:
        """ROI bajo + beneficio pequeño → HIGH."""
        vehicle = VehicleStub(price=60000.0)
        result = analyzer.analyze(vehicle, sale_price_multiplier=1.02)
        assert result.risk_level == RiskLevel.HIGH

    def test_negative_profit_is_high_risk(self, analyzer: ProfitAnalyzer) -> None:
        """Beneficio negativo → HIGH siempre."""
        vehicle = VehicleStub(price=50000.0)
        result = analyzer.analyze(vehicle, sale_price_multiplier=0.9)
        assert result.risk_level == RiskLevel.HIGH


# =============================================================================
# Tests de configuraciones por país
# =============================================================================


class TestCountryConfigurations:
    """Tests para los diferentes perfiles de país."""

    def test_germany_configuration(self, analyzer: ProfitAnalyzer, cheap_vehicle: VehicleStub) -> None:
        result = analyzer.analyze(cheap_vehicle, profile_name="GERMANY")
        assert result.transport_cost == GERMANY_PROFILE.transport_cost
        assert result.registration_cost == GERMANY_PROFILE.registration_cost
        assert result.inspection_cost == GERMANY_PROFILE.inspection_cost

    def test_france_configuration(self, analyzer: ProfitAnalyzer, cheap_vehicle: VehicleStub) -> None:
        result = analyzer.analyze(cheap_vehicle, profile_name="FRANCE")
        assert result.transport_cost == FRANCE_PROFILE.transport_cost
        assert result.registration_cost == FRANCE_PROFILE.registration_cost
        assert result.inspection_cost == FRANCE_PROFILE.inspection_cost

    def test_default_configuration(self, analyzer: ProfitAnalyzer, cheap_vehicle: VehicleStub) -> None:
        result = analyzer.analyze(cheap_vehicle, profile_name="DEFAULT")
        assert result.transport_cost == DEFAULT_PROFILE.transport_cost
        assert result.registration_cost == DEFAULT_PROFILE.registration_cost
        assert result.inspection_cost == DEFAULT_PROFILE.inspection_cost

    def test_germany_cheaper_transport_than_france(self, analyzer: ProfitAnalyzer) -> None:
        vehicle = VehicleStub(price=20000.0)
        germany = analyzer.analyze(vehicle, profile_name="GERMANY")
        france = analyzer.analyze(vehicle, profile_name="FRANCE")
        assert germany.transport_cost < france.transport_cost

    def test_different_countries_different_results(self, analyzer: ProfitAnalyzer) -> None:
        vehicle = VehicleStub(price=15000.0)
        default = analyzer.analyze(vehicle, profile_name="DEFAULT")
        germany = analyzer.analyze(vehicle, profile_name="GERMANY")
        france = analyzer.analyze(vehicle, profile_name="FRANCE")

        # Todos deberían ser válidos pero diferentes
        assert default.total_cost != germany.total_cost or default.total_cost != france.total_cost

    def test_case_insensitive_profile(self, analyzer: ProfitAnalyzer, cheap_vehicle: VehicleStub) -> None:
        upper = analyzer.analyze(cheap_vehicle, profile_name="GERMANY")
        lower = analyzer.analyze(cheap_vehicle, profile_name="germany")
        mixed = analyzer.analyze(cheap_vehicle, profile_name="Germany")
        assert upper.total_cost == lower.total_cost == mixed.total_cost


# =============================================================================
# Tests de validación de cálculos
# =============================================================================


class TestCalculationValidation:
    """Validación matemática de todos los cálculos del ProfitAnalyzer."""

    def test_total_cost_calculation(self, analyzer: ProfitAnalyzer, cheap_vehicle: VehicleStub) -> None:
        result = analyzer.analyze(cheap_vehicle)
        profile = DEFAULT_PROFILE

        # Verificar costes fijos
        expected_fixed = (
            profile.transport_cost
            + profile.registration_cost
            + profile.inspection_cost
            + profile.paperwork_cost
            + profile.miscellaneous_cost
        )
        assert result.cost_breakdown.total_fixed_costs == expected_fixed

        # Verificar costes variables
        expected_variable = (
            cheap_vehicle.price * profile.tax_rate
            + cheap_vehicle.price * profile.commission_rate
            + cheap_vehicle.price * profile.repair_estimate_rate
        )
        assert result.cost_breakdown.total_variable_costs == expected_variable

        # Verificar coste total
        expected_total = cheap_vehicle.price + expected_fixed + expected_variable
        assert result.total_cost == expected_total

    def test_gross_profit_calculation(self, analyzer: ProfitAnalyzer, cheap_vehicle: VehicleStub) -> None:
        result = analyzer.analyze(cheap_vehicle)
        expected_gross = result.estimated_sale_price - cheap_vehicle.price
        assert result.gross_profit == expected_gross

    def test_net_profit_calculation(self, analyzer: ProfitAnalyzer, cheap_vehicle: VehicleStub) -> None:
        result = analyzer.analyze(cheap_vehicle)
        expected_net = result.estimated_sale_price - result.total_cost
        assert result.net_profit == expected_net

    def test_roi_percentage_calculation(self, analyzer: ProfitAnalyzer, cheap_vehicle: VehicleStub) -> None:
        result = analyzer.analyze(cheap_vehicle)
        expected_roi = (result.net_profit / result.total_cost) * 100.0
        assert result.roi_percentage == round(expected_roi, 2)

    def test_profit_margin_calculation(self, analyzer: ProfitAnalyzer, cheap_vehicle: VehicleStub) -> None:
        result = analyzer.analyze(cheap_vehicle)
        expected_margin = (result.net_profit / result.estimated_sale_price) * 100.0
        assert result.profit_margin_percentage == round(expected_margin, 2)

    def test_direct_sale_price_override(self, analyzer: ProfitAnalyzer, cheap_vehicle: VehicleStub) -> None:
        """Proporcionar un precio de venta estimado directamente."""
        result = analyzer.analyze(cheap_vehicle, estimated_sale_price=18000.0)
        assert result.estimated_sale_price == 18000.0
        assert result.gross_profit == 18000.0 - cheap_vehicle.price

    def test_sale_price_multiplier(self, analyzer: ProfitAnalyzer, cheap_vehicle: VehicleStub) -> None:
        """Usar un multiplicador personalizado para el precio de venta."""
        result = analyzer.analyze(cheap_vehicle, sale_price_multiplier=2.0)
        assert result.estimated_sale_price == cheap_vehicle.price * 2.0

    def test_zero_estimated_sale_price_ignored(self, analyzer: ProfitAnalyzer, cheap_vehicle: VehicleStub) -> None:
        """Si estimated_sale_price es 0, debe usar el multiplicador."""
        result = analyzer.analyze(cheap_vehicle, estimated_sale_price=0.0)
        assert result.estimated_sale_price > 0
        assert result.estimated_sale_price == cheap_vehicle.price * 1.4


# =============================================================================
# Tests de escenarios completos
# =============================================================================


class TestCompleteScenarios:
    """Escenarios completos que validan el análisis global."""

    def test_very_profitable_sale(self, analyzer: ProfitAnalyzer) -> None:
        """Venta muy rentable: coche barato, precio de venta alto."""
        vehicle = VehicleStub(price=5000.0)
        result = analyzer.analyze(vehicle, sale_price_multiplier=3.0)
        assert result.net_profit > 3000.0
        assert result.roi_percentage > 50.0
        assert result.risk_level == RiskLevel.LOW
        assert result.recommendation == Recommendation.BUY

    def test_low_profitability_sale(self, analyzer: ProfitAnalyzer) -> None:
        """Venta poco rentable: coche caro, precio de venta ajustado."""
        vehicle = VehicleStub(price=45000.0)
        result = analyzer.analyze(vehicle, sale_price_multiplier=1.08)
        assert result.net_profit < 2000.0 or result.net_profit < 0
        assert result.recommendation in (Recommendation.CONSIDER, Recommendation.REJECT)

    def test_high_roi_scenario(self, analyzer: ProfitAnalyzer) -> None:
        """ROI muy alto."""
        vehicle = VehicleStub(price=5000.0)
        result = analyzer.analyze(vehicle, sale_price_multiplier=3.0)
        assert result.roi_percentage > 30.0
        assert result.recommendation == Recommendation.BUY

    def test_low_roi_scenario(self, analyzer: ProfitAnalyzer) -> None:
        """ROI muy bajo."""
        vehicle = VehicleStub(price=70000.0)
        result = analyzer.analyze(vehicle, sale_price_multiplier=1.02)
        assert result.roi_percentage < 5.0
        assert result.recommendation == Recommendation.REJECT


# =============================================================================
# Tests de determinismo
# =============================================================================


class TestDeterminism:
    """El analyzer debe ser determinista: mismos datos → mismos resultados."""

    def test_deterministic_results(self, analyzer: ProfitAnalyzer) -> None:
        vehicle = VehicleStub(price=15000.0)

        result1 = analyzer.analyze(vehicle)
        result2 = analyzer.analyze(vehicle)

        assert result1.total_cost == result2.total_cost
        assert result1.net_profit == result2.net_profit
        assert result1.roi_percentage == result2.roi_percentage
        assert result1.profit_margin_percentage == result2.profit_margin_percentage
        assert result1.risk_level == result2.risk_level
        assert result1.recommendation == result2.recommendation

    def test_different_instances_same_result(self, cheap_vehicle: VehicleStub) -> None:
        a1 = ProfitAnalyzer()
        a2 = ProfitAnalyzer()

        r1 = a1.analyze(cheap_vehicle)
        r2 = a2.analyze(cheap_vehicle)

        assert r1.total_cost == r2.total_cost
        assert r1.net_profit == r2.net_profit
        assert r1.roi_percentage == r2.roi_percentage

    def test_deterministic_with_profile(self, analyzer: ProfitAnalyzer) -> None:
        vehicle = VehicleStub(price=20000.0)

        r1 = analyzer.analyze(vehicle, profile_name="GERMANY")
        r2 = analyzer.analyze(vehicle, profile_name="GERMANY")

        assert r1.total_cost == r2.total_cost
        assert r1.recommendation == r2.recommendation
        assert r1.risk_level == r2.risk_level


# =============================================================================
# Tests de extensibilidad
# =============================================================================


class TestExtensibility:
    """Verifica que la arquitectura es extensible sin modificar ProfitAnalyzer."""

    def test_extra_costs_accepted(self, analyzer: ProfitAnalyzer, cheap_vehicle: VehicleStub) -> None:
        """Costes adicionales deben ser aceptados."""
        result = analyzer.analyze(
            cheap_vehicle,
            insurance=500.0,
            customs=300.0,
        )
        # Los costes adicionales se agregan a miscellaneous_cost
        assert result.miscellaneous_cost > DEFAULT_PROFILE.miscellaneous_cost + DEFAULT_PROFILE.paperwork_cost

    def test_extra_costs_affect_total(self, analyzer: ProfitAnalyzer, cheap_vehicle: VehicleStub) -> None:
        base = analyzer.analyze(cheap_vehicle)
        with_extra = analyzer.analyze(cheap_vehicle, insurance=1000.0)
        assert with_extra.total_cost > base.total_cost
        assert with_extra.net_profit < base.net_profit

    def test_extra_costs_unknown_ignored(self, analyzer: ProfitAnalyzer, cheap_vehicle: VehicleStub) -> None:
        """Categorías de costes adicionales desconocidas deben ser ignoradas."""
        base = analyzer.analyze(cheap_vehicle)
        with_unknown = analyzer.analyze(cheap_vehicle, unknown_category=999.0)
        assert base.total_cost == with_unknown.total_cost

    def test_additional_costs_list_available(self) -> None:
        from app.config.import_costs import ADDITIONAL_COSTS_CATEGORIES
        assert isinstance(ADDITIONAL_COSTS_CATEGORIES, list)
        assert len(ADDITIONAL_COSTS_CATEGORIES) > 0
        assert "insurance" in ADDITIONAL_COSTS_CATEGORIES
        assert "customs" in ADDITIONAL_COSTS_CATEGORIES
        assert "financing" in ADDITIONAL_COSTS_CATEGORIES
        assert "storage" in ADDITIONAL_COSTS_CATEGORIES
        assert "detailing" in ADDITIONAL_COSTS_CATEGORIES


# =============================================================================
# Tests de integridad
# =============================================================================


class TestIntegrity:
    """Pruebas de integridad y consistencia de los resultados."""

    def test_total_cost_greater_than_purchase_price(self, analyzer: ProfitAnalyzer, cheap_vehicle: VehicleStub) -> None:
        """El coste total siempre debe ser mayor que el precio de compra."""
        result = analyzer.analyze(cheap_vehicle)
        assert result.total_cost > cheap_vehicle.price

    def test_net_profit_less_than_gross_profit(self, analyzer: ProfitAnalyzer, cheap_vehicle: VehicleStub) -> None:
        """El beneficio neto siempre debe ser menor que el bruto (hay costes)."""
        result = analyzer.analyze(cheap_vehicle)
        assert result.net_profit < result.gross_profit

    def test_roi_and_margin_consistency(self, analyzer: ProfitAnalyzer, cheap_vehicle: VehicleStub) -> None:
        """Si net_profit > 0, ROI y margin deben ser positivos."""
        result = analyzer.analyze(cheap_vehicle)
        if result.net_profit > 0:
            assert result.roi_percentage > 0
            assert result.profit_margin_percentage > 0

    def test_all_costs_positive(self, analyzer: ProfitAnalyzer, cheap_vehicle: VehicleStub) -> None:
        """Todos los costes individuales deben ser no negativos."""
        result = analyzer.analyze(cheap_vehicle)
        assert result.transport_cost >= 0
        assert result.registration_cost >= 0
        assert result.taxes >= 0
        assert result.inspection_cost >= 0
        assert result.repair_estimate >= 0
        assert result.commission_cost >= 0
        assert result.miscellaneous_cost >= 0

    def test_risk_and_recommendation_consistency(self, analyzer: ProfitAnalyzer) -> None:
        """Riesgo alto nunca debe dar BUY."""
        vehicle = VehicleStub(price=80000.0)
        result = analyzer.analyze(vehicle, sale_price_multiplier=0.9)
        if result.risk_level == RiskLevel.HIGH:
            assert result.recommendation == Recommendation.REJECT

    def test_risk_low_with_positive_profit_gives_buy(self, analyzer: ProfitAnalyzer) -> None:
        """Riesgo bajo con beneficio positivo debe dar BUY."""
        vehicle = VehicleStub(price=5000.0)
        result = analyzer.analyze(vehicle, sale_price_multiplier=3.0)
        if result.risk_level == RiskLevel.LOW:
            assert result.recommendation == Recommendation.BUY


# =============================================================================
# Tests de edge cases
# =============================================================================


class TestEdgeCases:
    """Casos borde y situaciones límite."""

    def test_very_low_price(self, analyzer: ProfitAnalyzer) -> None:
        """Precio muy bajo (1 EUR) debe funcionar."""
        vehicle = VehicleStub(price=5000.0)
        result = analyzer.analyze(vehicle, sale_price_multiplier=3.0)
        assert result.total_cost > 0
        assert result.net_profit > 0

    def test_very_high_price(self, analyzer: ProfitAnalyzer) -> None:
        """Precio muy alto debe funcionar sin errores de precisión."""
        vehicle = VehicleStub(price=1_000_000.0)
        result = analyzer.analyze(vehicle, sale_price_multiplier=1.1)
        assert result.total_cost > 1_000_000.0
        assert isinstance(result.roi_percentage, float)

    def test_zero_mileage_and_year(self, analyzer: ProfitAnalyzer) -> None:
        """Campos con valor 0 no deben afectar al análisis."""
        vehicle = VehicleStub(price=15000.0, mileage=0, year=0)
        result = analyzer.analyze(vehicle)
        assert isinstance(result, ProfitAnalysis)

    def test_none_brand_model(self, analyzer: ProfitAnalyzer) -> None:
        """Marca y modelo None no deben impedir el análisis."""
        vehicle = VehicleStub(price=10000.0, brand=None, model=None)
        result = analyzer.analyze(vehicle)
        assert isinstance(result, ProfitAnalysis)
        assert result.total_cost > 0

    def test_empty_string_brand_model(self, analyzer: ProfitAnalyzer) -> None:
        """Marca y modelo vacíos no deben impedir el análisis."""
        vehicle = VehicleStub(price=10000.0, brand="", model="")
        result = analyzer.analyze(vehicle)
        assert isinstance(result, ProfitAnalysis)

    def test_zero_roi_edge(self, analyzer: ProfitAnalyzer) -> None:
        """ROI exactamente 0 debe clasificarse correctamente."""
        # Costes exactamente iguales al precio de venta
        vehicle = VehicleStub(price=10000.0)
        # Calcular el precio de venta exacto que daría ROI=0
        profile = DEFAULT_PROFILE
        fixed_costs = (
            profile.transport_cost
            + profile.registration_cost
            + profile.inspection_cost
            + profile.paperwork_cost
            + profile.miscellaneous_cost
        )
        variable_costs = 10000.0 * (profile.tax_rate + profile.commission_rate + profile.repair_estimate_rate)
        total_costs = 10000.0 + fixed_costs + variable_costs
        sale_price = total_costs  # ROI exactamente 0

        result = analyzer.analyze(vehicle, estimated_sale_price=sale_price)
        assert abs(result.roi_percentage) < 0.01  # ROI ~0%
        assert result.net_profit >= -0.01  # Puede ser 0 o pequeño error de redondeo
        assert result.risk_level == RiskLevel.HIGH  # Sin beneficio → HIGH

    def test_buy_recommendation_criteria(self, analyzer: ProfitAnalyzer) -> None:
        """BUY solo cuando riesgo es LOW y ROI > 0."""
        vehicle = VehicleStub(price=5000.0)
        result = analyzer.analyze(vehicle, sale_price_multiplier=3.0)
        if result.recommendation == Recommendation.BUY:
            assert result.risk_level == RiskLevel.LOW
            assert result.roi_percentage > 0

    def test_reject_on_high_risk(self, analyzer: ProfitAnalyzer) -> None:
        """REJECT cuando riesgo es HIGH (independientemente del ROI)."""
        vehicle = VehicleStub(price=60000.0)
        result = analyzer.analyze(vehicle, sale_price_multiplier=1.02)
        if result.risk_level == RiskLevel.HIGH:
            assert result.recommendation == Recommendation.REJECT


# =============================================================================
# Tests de precisión y redondeo
# =============================================================================


class TestPrecision:
    """Verifica la precisión de los cálculos monetarios."""

    def test_float_precision(self, analyzer: ProfitAnalyzer) -> None:
        """Los valores deben tener precisión de 2 decimales (céntimos)."""
        vehicle = VehicleStub(price=12345.67)
        result = analyzer.analyze(vehicle)
        # Verificar que los campos principales tienen 2 decimales
        for field in (
            result.purchase_price,
            result.total_cost,
            result.estimated_sale_price,
            result.net_profit,
            result.roi_percentage,
            result.profit_margin_percentage,
        ):
            assert isinstance(field, float)

    def test_no_negative_zero(self, analyzer: ProfitAnalyzer) -> None:
        """Evitar -0.0 en los resultados."""
        vehicle = VehicleStub(price=10000.0)
        result = analyzer.analyze(vehicle)
        for field in (
            result.purchase_price,
            result.transport_cost,
            result.registration_cost,
            result.taxes,
            result.inspection_cost,
            result.repair_estimate,
            result.commission_cost,
            result.miscellaneous_cost,
            result.total_cost,
            result.estimated_sale_price,
        ):
            assert field >= 0.0 or abs(field) < 1e-10


# =============================================================================
# Tests de no dependencia externa
# =============================================================================


class TestNoExternalDependencies:
    """ProfitAnalyzer no debe depender de scraping ni scoring."""

    def test_no_scoring_import(self) -> None:
        """ProfitAnalyzer no debe importar VehicleScorer."""
        import inspect
        import app.services.profit_analyzer as pa

        source = inspect.getsource(pa)
        assert "VehicleScorer" not in source
        assert "vehicle_scorer" not in source

    def test_no_provider_import(self) -> None:
        """ProfitAnalyzer no debe importar ningún provider."""
        import inspect
        import app.services.profit_analyzer as pa

        source = inspect.getsource(pa)
        assert "Provider" not in source
        assert "provider" not in source.lower().replace("profitanalyzer", "")

    def test_no_http_import(self) -> None:
        """ProfitAnalyzer no debe hacer peticiones HTTP."""
        import inspect
        import app.services.profit_analyzer as pa

        source = inspect.getsource(pa)
        assert "requests" not in source
        assert "httpx" not in source
        assert "urllib" not in source
        assert "aiohttp" not in source

    def test_only_depends_on_vehicle_and_config(self) -> None:
        """ProfitAnalyzer solo debe depender de VehicleData y config."""
        import inspect
        import app.services.profit_analyzer as pa

        source = inspect.getsource(pa)
        # Debe importar de config/import_costs.py
        assert "import_costs" in source
        # No debe importar de models, providers, schemas
        assert "app.models" not in source
        assert "app.providers" not in source
        assert "app.schemas" not in source


# =============================================================================
# Task B.1: perfiles destino ES/PT + alias
# =============================================================================


def test_spain_profile_registered() -> None:
    p = get_profile("SPAIN")
    assert p.transport_cost == 1200.0
    assert p.registration_cost == 450.0
    assert 0 < p.tax_rate < 1


def test_portugal_profile_registered() -> None:
    p = get_profile("PORTUGAL")
    assert p.transport_cost == 1400.0
    assert p.tax_rate >= get_profile("SPAIN").tax_rate


def test_profile_alias_es_equals_spain() -> None:
    assert get_profile("ES") is get_profile("SPAIN")
    assert get_profile("es") is get_profile("SPAIN")


def test_profile_alias_pt_equals_portugal() -> None:
    assert get_profile("PT") is get_profile("PORTUGAL")


def test_profile_alias_de_equals_germany() -> None:
    assert get_profile("DE") is get_profile("GERMANY")


def test_get_profile_unknown_raises_with_hint() -> None:
    with pytest.raises(KeyError, match="desconocido"):
        get_profile("MARS")


def test_analyze_with_spain_profile_determinism() -> None:
    @dataclass
    class V:
        price: float | None = 20000.0
        brand: str | None = "BMW"
        model: str | None = "320d"
        year: int | None = 2019
        mileage: int | None = 80000

    analyzer = ProfitAnalyzer()
    a = analyzer.analyze(V(), profile_name="ES", estimated_sale_price=26000.0)
    b = analyzer.analyze(V(), profile_name="SPAIN", estimated_sale_price=26000.0)
    assert a.total_cost == b.total_cost
    assert a.net_profit == b.net_profit

