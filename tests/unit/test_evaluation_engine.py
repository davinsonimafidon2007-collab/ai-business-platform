"""Tests para el motor de evaluación de vehículos.

Tras Task B.3, el bloque económico se delega en ProfitAnalyzer (perfil SPAIN).
Estos tests verifican el scoring propio y que los valores económicos
coinciden con ProfitAnalyzer para el mismo vehículo/perfil.
"""

from __future__ import annotations

import pytest

from app.models.vehicle import Vehicle
from app.services.evaluation_engine import EvaluationEngine, EvaluationResult
from app.services.profit_analyzer import ProfitAnalyzer


@pytest.fixture
def evaluation_engine():
    """Fixture que crea un EvaluationEngine para tests."""
    return EvaluationEngine(import_cost_profile="SPAIN")


@pytest.fixture
def sample_vehicle():
    """Fixture que crea un vehículo de ejemplo."""
    return Vehicle(
        id="test-vehicle-id",
        brand="BMW",
        model="X5",
        year=2020,
        mileage=50000,
        price=35000.0,
        fuel_type="Diesel",
        transmission="Automatic",
        category="SUV",
    )


@pytest.fixture
def cheap_vehicle():
    """Fixture que crea un vehículo barato."""
    return Vehicle(
        id="cheap-vehicle-id",
        brand="Toyota",
        model="Corolla",
        year=2018,
        mileage=80000,
        price=15000.0,
        fuel_type="Gasoline",
        transmission="Manual",
        category="Sedan",
    )


@pytest.fixture
def old_vehicle():
    """Fixture que crea un vehículo antiguo."""
    return Vehicle(
        id="old-vehicle-id",
        brand="Volkswagen",
        model="Golf",
        year=2010,
        mileage=150000,
        price=8000.0,
        fuel_type="Diesel",
        transmission="Manual",
        category="Compact",
    )


def test_evaluate_vehicle_returns_result(evaluation_engine, sample_vehicle):
    """Test que verifica que la evaluación retorna un resultado válido."""
    result = evaluation_engine.evaluate(sample_vehicle)

    assert isinstance(result, EvaluationResult)
    assert result.vehicle_cost == 35000.0
    assert result.transport_cost > 0
    assert result.total_cost > 0
    assert result.estimated_sale_price_es > 0
    assert 0 <= result.score <= 100
    assert result.classification in ["verde", "amarillo", "rojo"]
    assert isinstance(result.warnings, list)
    assert isinstance(result.recommendation, str)
    assert len(result.recommendation) > 0


def test_vehicle_cost_matches_profit_analyzer(evaluation_engine, sample_vehicle):
    """El coste del vehículo coincide con ProfitAnalyzer."""
    result = evaluation_engine.evaluate(sample_vehicle)
    analysis = ProfitAnalyzer().analyze(
        sample_vehicle, profile_name="SPAIN"
    )
    assert result.vehicle_cost == analysis.purchase_price


def test_total_cost_matches_profit_analyzer(evaluation_engine, sample_vehicle):
    """El coste total coincide con ProfitAnalyzer (misma fuente de verdad)."""
    result = evaluation_engine.evaluate(sample_vehicle)
    analysis = ProfitAnalyzer().analyze(
        sample_vehicle, profile_name="SPAIN"
    )
    assert result.total_cost == analysis.total_cost


def test_vehicle_cost_zero_when_no_price(evaluation_engine):
    """Test que verifica el comportamiento cuando no hay precio."""
    vehicle = Vehicle(brand="BMW", model="X5", year=2020)
    result = evaluation_engine.evaluate(vehicle)

    assert result.vehicle_cost == 0.0
    assert "no tiene precio de compra definido" in result.warnings


def test_transport_cost_uses_spain_profile(evaluation_engine):
    """El transporte usa el perfil SPAIN (1200 €), no categoría del vehículo."""
    from app.config.import_costs import get_profile

    profile = get_profile("SPAIN")
    vehicle = Vehicle(brand="BMW", model="X5", year=2020, price=35000.0, category="SUV")
    result = evaluation_engine.evaluate(vehicle)
    assert result.transport_cost == profile.transport_cost


def test_import_tax_matches_spain_tax_rate(evaluation_engine):
    """El impuesto usa taza fiscal del perfil SPAIN (10%)."""
    from app.config.import_costs import get_profile

    profile = get_profile("SPAIN")
    vehicle = Vehicle(brand="BMW", model="X5", year=2020, price=35000.0)
    result = evaluation_engine.evaluate(vehicle)
    assert result.taxes_cost == 35000.0 * profile.tax_rate


def test_registration_cost_uses_spain_profile(evaluation_engine):
    """La matriculación usa el perfil SPAIN, no porcentaje del viejo engine."""
    from app.config.import_costs import get_profile

    profile = get_profile("SPAIN")
    vehicle = Vehicle(brand="BMW", model="X5", year=2020, price=35000.0)
    result = evaluation_engine.evaluate(vehicle)
    assert result.registration_cost == profile.registration_cost


def test_total_cost_includes_all_components(evaluation_engine, sample_vehicle):
    """El coste total descompone de forma coherente (con commission + repair)."""
    result = evaluation_engine.evaluate(sample_vehicle)
    analysis = ProfitAnalyzer().analyze(
        sample_vehicle, profile_name="SPAIN"
    )

    total_from_components = (
        result.vehicle_cost
        + result.transport_cost
        + result.registration_cost
        + result.itv_cost
        + result.gestoria_cost
        + result.taxes_cost
        + analysis.cost_breakdown.commission_cost
        + analysis.cost_breakdown.repair_estimate
    )
    assert abs(result.total_cost - total_from_components) < 0.01


def test_itv_cost_matches_spain_inspection(evaluation_engine, sample_vehicle):
    """La ITV usa el perfil SPAIN (inspection_cost=90)."""
    from app.config.import_costs import get_profile

    profile = get_profile("SPAIN")
    result = evaluation_engine.evaluate(sample_vehicle)
    assert result.itv_cost == profile.inspection_cost


def test_gestoria_cost_uses_profile_miscellaneous(evaluation_engine, sample_vehicle):
    """La gestoría usa miscellaneous + paperwork del perfil."""
    from app.config.import_costs import get_profile

    profile = get_profile("SPAIN")
    result = evaluation_engine.evaluate(sample_vehicle)
    # cost_breakdown.miscellaneous_cost = misc + paperwork (480)
    assert result.gestoria_cost == profile.miscellaneous_cost + profile.paperwork_cost


def test_estimated_sale_price_matches_profit_analyzer(evaluation_engine, sample_vehicle):
    """El precio estimado de venta coincide con ProfitAnalyzer (multiplicador default)."""
    result = evaluation_engine.evaluate(sample_vehicle)
    analysis = ProfitAnalyzer().analyze(
        sample_vehicle, profile_name="SPAIN"
    )
    assert result.estimated_sale_price_es == analysis.estimated_sale_price


def test_profit_matches_profit_analyzer_net(evaluation_engine, sample_vehicle):
    """El beneficio coincide con net_profit de ProfitAnalyzer."""
    result = evaluation_engine.evaluate(sample_vehicle)
    analysis = ProfitAnalyzer().analyze(
        sample_vehicle, profile_name="SPAIN"
    )
    assert result.gross_profit == analysis.net_profit


def test_profit_margin_matches_profit_analyzer_roi(evaluation_engine, sample_vehicle):
    """El margen coincide con roi_percentage de ProfitAnalyzer."""
    result = evaluation_engine.evaluate(sample_vehicle)
    analysis = ProfitAnalyzer().analyze(
        sample_vehicle, profile_name="SPAIN"
    )
    assert result.profit_margin_percent == analysis.roi_percentage


def test_score_calculation_high_margin(evaluation_engine):
    """Test que verifica el score con margen alto."""
    vehicle = Vehicle(brand="Toyota", model="Corolla", year=2022, price=20000.0, mileage=20000)
    result = evaluation_engine.evaluate(vehicle)

    assert result.score >= 40


def test_score_calculation_low_margin(evaluation_engine):
    """Test que verifica el score con margen bajo."""
    vehicle = Vehicle(brand="BMW", model="X5", year=2020, price=80000.0, mileage=50000)
    result = evaluation_engine.evaluate(vehicle)

    assert result.score < 90


def test_classification_verde(evaluation_engine):
    """Test que verifica clasificación verde."""
    vehicle = Vehicle(brand="Toyota", model="Corolla", year=2022, price=20000.0, mileage=20000)
    result = evaluation_engine.evaluate(vehicle)

    if result.score >= 70 and result.profit_margin_percent >= 15:
        assert result.classification == "verde"


def test_classification_amarillo(evaluation_engine):
    """Test que verifica clasificación amarillo."""
    vehicle = Vehicle(brand="BMW", model="X5", year=2020, price=50000.0, mileage=60000)
    result = evaluation_engine.evaluate(vehicle)

    if 40 <= result.score < 70 and 8 <= result.profit_margin_percent < 15:
        assert result.classification == "amarillo"


def test_classification_rojo(evaluation_engine):
    """Test que verifica clasificación rojo."""
    vehicle = Vehicle(brand="BMW", model="X5", year=2010, price=60000.0, mileage=200000)
    result = evaluation_engine.evaluate(vehicle)

    if result.score < 40 or result.profit_margin_percent < 8:
        assert result.classification == "rojo"


def test_warnings_generated_for_no_price(evaluation_engine):
    """Test que verifica que se generan advertencias cuando no hay precio."""
    vehicle = Vehicle(brand="BMW", model="X5", year=2020)
    result = evaluation_engine.evaluate(vehicle)

    assert len(result.warnings) > 0
    assert any("precio de compra" in warning for warning in result.warnings)


def test_recommendation_verde(evaluation_engine):
    """Test que verifica la recomendación para clasificación verde."""
    vehicle = Vehicle(brand="Toyota", model="Corolla", year=2022, price=20000.0, mileage=20000)
    result = evaluation_engine.evaluate(vehicle)

    if result.classification == "verde":
        assert "recomendado" in result.recommendation.lower()


def test_recommendation_rojo(evaluation_engine):
    """Test que verifica la recomendación para clasificación rojo."""
    vehicle = Vehicle(brand="BMW", model="X5", year=2010, price=60000.0, mileage=200000)
    result = evaluation_engine.evaluate(vehicle)

    if result.classification == "rojo":
        assert "no recomendado" in result.recommendation.lower()


def test_score_range_0_to_100(evaluation_engine):
    """Test que verifica que el score está siempre entre 0 y 100."""
    vehicle_bad = Vehicle(brand="BMW", model="X5", year=1990, price=100000.0, mileage=300000)
    result_bad = evaluation_engine.evaluate(vehicle_bad)
    assert 0 <= result_bad.score <= 100

    vehicle_good = Vehicle(brand="Toyota", model="Corolla", year=2023, price=20000.0, mileage=5000)
    result_good = evaluation_engine.evaluate(vehicle_good)
    assert 0 <= result_good.score <= 100


def test_evaluation_result_dataclass(evaluation_engine, sample_vehicle):
    """Test que verifica que EvaluationResult es un dataclass."""
    result = evaluation_engine.evaluate(sample_vehicle)

    for attr in [
        "vehicle_cost", "transport_cost", "registration_cost", "itv_cost",
        "gestoria_cost", "taxes_cost", "total_cost", "estimated_sale_price_es",
        "gross_profit", "profit_margin_percent", "score", "classification",
        "warnings", "recommendation",
    ]:
        assert hasattr(result, attr)


def test_evaluation_with_all_vehicle_fields(evaluation_engine):
    """Test que verifica la evaluación con todos los campos del vehículo."""
    vehicle = Vehicle(
        brand="BMW",
        model="X5",
        year=2020,
        mileage=50000,
        price=35000.0,
        fuel_type="Diesel",
        transmission="Automatic",
        category="SUV",
        color="Black",
        location="Munich, Germany",
    )
    result = evaluation_engine.evaluate(vehicle)

    assert result.vehicle_cost == 35000.0
    assert result.total_cost > 35000.0
    assert result.classification in ["verde", "amarillo", "rojo"]


def test_evaluation_consistency(evaluation_engine, sample_vehicle):
    """Test que verifica que la evaluación es consistente (mismo input = mismo output)."""
    result1 = evaluation_engine.evaluate(sample_vehicle)
    result2 = evaluation_engine.evaluate(sample_vehicle)

    assert result1.vehicle_cost == result2.vehicle_cost
    assert result1.transport_cost == result2.transport_cost
    assert result1.total_cost == result2.total_cost
    assert result1.estimated_sale_price_es == result2.estimated_sale_price_es
    assert result1.score == result2.score
    assert result1.classification == result2.classification


def test_recommendation_aligned_with_profit_analyzer(evaluation_engine, sample_vehicle):
    """La recomendación se alinea con ProfitAnalyzer (BUY/CONSIDER/REJECT)."""
    result = evaluation_engine.evaluate(sample_vehicle)
    analysis = ProfitAnalyzer().analyze(
        sample_vehicle, profile_name="SPAIN"
    )
    from app.services.profit_analyzer import Recommendation

    if analysis.recommendation == Recommendation.BUY:
        assert "recomendado" in result.recommendation.lower()
    elif analysis.recommendation == Recommendation.REJECT:
        assert "no recomendado" in result.recommendation.lower()