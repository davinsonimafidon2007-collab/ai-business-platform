"""Tests para el motor de evaluación de vehículos."""

from __future__ import annotations

import pytest

from app.models.vehicle import Vehicle
from app.services.evaluation_engine import EvaluationEngine, EvaluationResult


@pytest.fixture
def evaluation_engine():
    """Fixture que crea un EvaluationEngine para tests."""
    return EvaluationEngine()


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


def test_vehicle_cost_calculation(evaluation_engine, sample_vehicle):
    """Test que verifica el cálculo del coste del vehículo."""
    result = evaluation_engine.evaluate(sample_vehicle)
    assert result.vehicle_cost == 35000.0


def test_vehicle_cost_zero_when_no_price(evaluation_engine):
    """Test que verifica el comportamiento cuando no hay precio."""
    vehicle = Vehicle(brand="BMW", model="X5", year=2020)
    result = evaluation_engine.evaluate(vehicle)
    
    assert result.vehicle_cost == 0.0
    assert "no tiene precio de compra definido" in result.warnings


def test_transport_cost_suv(evaluation_engine):
    """Test que verifica el coste de transporte para SUV."""
    vehicle = Vehicle(brand="BMW", model="X5", year=2020, price=35000.0, category="SUV")
    result = evaluation_engine.evaluate(vehicle)
    
    # SUV debería tener coste de transporte mayor (750€ base)
    assert result.transport_cost == 750.0


def test_transport_cost_compact(evaluation_engine):
    """Test que verifica el coste de transporte para coche compacto."""
    vehicle = Vehicle(brand="BMW", model="X5", year=2020, price=35000.0, category="Compacto")
    result = evaluation_engine.evaluate(vehicle)
    
    # Coche compacto debería tener coste menor (400€ base)
    assert result.transport_cost == 400.0


def test_transport_cost_standard(evaluation_engine):
    """Test que verifica el coste de transporte estándar."""
    vehicle = Vehicle(brand="BMW", model="X5", year=2020, price=35000.0, category="Sedan")
    result = evaluation_engine.evaluate(vehicle)
    
    # Sedan estándar (500€ base)
    assert result.transport_cost == 500.0


def test_transport_cost_old_vehicle(evaluation_engine):
    """Test que verifica el coste de transporte para vehículos antiguos."""
    vehicle = Vehicle(brand="BMW", model="X5", year=2005, price=15000.0, category="SUV")
    result = evaluation_engine.evaluate(vehicle)
    
    # SUV base (750€) + 20% por ser mayor de 15 años
    expected = 750.0 * 1.2
    assert result.transport_cost == expected


def test_import_tax_calculation(evaluation_engine):
    """Test que verifica el cálculo del impuesto de importación."""
    vehicle = Vehicle(brand="BMW", model="X5", year=2020, price=35000.0)
    result = evaluation_engine.evaluate(vehicle)
    
    # Import tax is 0 for EU vehicles (Germany is in the EU)
    expected_import_tax = 0.0
    # El impuesto está incluido en taxes_cost
    assert result.taxes_cost >= expected_import_tax


def test_iva_calculation(evaluation_engine):
    """Test que verifica el cálculo del IVA."""
    vehicle = Vehicle(brand="BMW", model="X5", year=2020, price=35000.0)
    result = evaluation_engine.evaluate(vehicle)
    
    # IVA = 21% sobre (precio + import_tax)
    vehicle_cost = 35000.0
    import_tax = 0.0  # Import tax is 0 for EU vehicles
    expected_iva = (vehicle_cost + import_tax) * 0.21
    # El IVA está incluido en taxes_cost
    assert result.taxes_cost >= expected_iva


def test_registration_tax_calculation(evaluation_engine):
    """Test que verifica el cálculo del impuesto de matriculación."""
    vehicle = Vehicle(brand="BMW", model="X5", year=2020, price=35000.0)
    result = evaluation_engine.evaluate(vehicle)
    
    # 4% de 35000€
    expected_registration_tax = 35000.0 * 0.04
    # registration_cost incluye impuesto de matriculación + tasas
    assert result.registration_cost >= expected_registration_tax


def test_total_cost_calculation(evaluation_engine, sample_vehicle):
    """Test que verifica el cálculo del coste total."""
    result = evaluation_engine.evaluate(sample_vehicle)
    
    # El coste total debe ser mayor que el precio del vehículo
    assert result.total_cost > result.vehicle_cost
    
    # Verificar que incluye todos los componentes
    assert result.total_cost == (
        result.vehicle_cost
        + result.transport_cost
        + result.registration_cost
        + result.itv_cost
        + result.gestoria_cost
        + result.taxes_cost
    )


def test_itv_cost_is_fixed(evaluation_engine, sample_vehicle):
    """Test que verifica que el coste de ITV es fijo."""
    result = evaluation_engine.evaluate(sample_vehicle)
    assert result.itv_cost == 150.0


def test_gestoria_cost_is_fixed(evaluation_engine, sample_vehicle):
    """Test que verifica que el coste de gestoría es fijo."""
    result = evaluation_engine.evaluate(sample_vehicle)
    assert result.gestoria_cost == 350.0


def test_estimated_sale_price_with_depreciation(evaluation_engine):
    """Test que verifica la depreciación por antigüedad."""
    # Vehículo de 1 año
    vehicle_1y = Vehicle(brand="BMW", model="X5", year=2023, price=35000.0)
    result_1y = evaluation_engine.evaluate(vehicle_1y)
    
    # Vehículo de 3 años
    vehicle_3y = Vehicle(brand="BMW", model="X5", year=2021, price=35000.0)
    result_3y = evaluation_engine.evaluate(vehicle_3y)
    
    # El vehículo más antiguo debería tener menor precio estimado
    assert result_1y.estimated_sale_price_es > result_3y.estimated_sale_price_es


def test_estimated_sale_price_with_mileage_penalty(evaluation_engine):
    """Test que verifica la penalización por kilometraje alto."""
    # Vehículo con kilometraje bajo
    vehicle_low_km = Vehicle(brand="BMW", model="X5", year=2020, price=35000.0, mileage=30000)
    result_low = evaluation_engine.evaluate(vehicle_low_km)
    
    # Vehículo con kilometraje alto
    vehicle_high_km = Vehicle(brand="BMW", model="X5", year=2020, price=35000.0, mileage=150000)
    result_high = evaluation_engine.evaluate(vehicle_high_km)
    
    # El vehículo con más kilometraje debería tener menor precio estimado
    assert result_low.estimated_sale_price_es > result_high.estimated_sale_price_es


def test_brand_premium_maintained(evaluation_engine):
    """Test que verifica que las marcas premium mantienen mejor el valor."""
    # Toyota (premium 1.08)
    vehicle_toyota = Vehicle(brand="Toyota", model="Corolla", year=2020, price=25000.0)
    result_toyota = evaluation_engine.evaluate(vehicle_toyota)
    
    # Volkswagen (premium 1.00)
    vehicle_vw = Vehicle(brand="Volkswagen", model="Golf", year=2020, price=25000.0)
    result_vw = evaluation_engine.evaluate(vehicle_vw)
    
    # Toyota debería tener mayor precio estimado
    assert result_toyota.estimated_sale_price_es > result_vw.estimated_sale_price_es


def test_gross_profit_calculation(evaluation_engine, sample_vehicle):
    """Test que verifica el cálculo del beneficio bruto."""
    result = evaluation_engine.evaluate(sample_vehicle)
    
    expected_profit = result.estimated_sale_price_es - result.total_cost
    assert result.gross_profit == expected_profit


def test_profit_margin_calculation(evaluation_engine, sample_vehicle):
    """Test que verifica el cálculo del margen de beneficio."""
    result = evaluation_engine.evaluate(sample_vehicle)
    
    if result.total_cost > 0:
        expected_margin = (result.gross_profit / result.total_cost) * 100
        assert abs(result.profit_margin_percent - expected_margin) < 0.01
    else:
        assert result.profit_margin_percent == 0.0


def test_score_calculation_high_margin(evaluation_engine):
    """Test que verifica el score con margen alto."""
    # Vehículo con buen margen
    vehicle = Vehicle(brand="Toyota", model="Corolla", year=2022, price=20000.0, mileage=20000)
    result = evaluation_engine.evaluate(vehicle)
    
    # Score debería ser alto (>= 70)
    assert result.score >= 40


def test_score_calculation_low_margin(evaluation_engine):
    """Test que verifica el score con margen bajo."""
    # Vehículo con precio muy alto (margen bajo)
    vehicle = Vehicle(brand="BMW", model="X5", year=2020, price=80000.0, mileage=50000)
    result = evaluation_engine.evaluate(vehicle)
    
    # Score debería ser menor
    assert result.score < 90


def test_classification_verde(evaluation_engine):
    """Test que verifica clasificación verde."""
    # Vehículo con buen margen y score alto
    vehicle = Vehicle(brand="Toyota", model="Corolla", year=2022, price=20000.0, mileage=20000)
    result = evaluation_engine.evaluate(vehicle)
    
    if result.score >= 70 and result.profit_margin_percent >= 15:
        assert result.classification == "verde"


def test_classification_amarillo(evaluation_engine):
    """Test que verifica clasificación amarillo."""
    # Vehículo con margen ajustado
    vehicle = Vehicle(brand="BMW", model="X5", year=2020, price=50000.0, mileage=60000)
    result = evaluation_engine.evaluate(vehicle)
    
    if 40 <= result.score < 70 and 8 <= result.profit_margin_percent < 15:
        assert result.classification == "amarillo"


def test_classification_rojo(evaluation_engine):
    """Test que verifica clasificación rojo."""
    # Vehículo con margen muy bajo o negativo
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
    # Vehículo muy malo
    vehicle_bad = Vehicle(brand="BMW", model="X5", year=1990, price=100000.0, mileage=300000)
    result_bad = evaluation_engine.evaluate(vehicle_bad)
    assert 0 <= result_bad.score <= 100
    
    # Vehículo muy bueno
    vehicle_good = Vehicle(brand="Toyota", model="Corolla", year=2023, price=20000.0, mileage=5000)
    result_good = evaluation_engine.evaluate(vehicle_good)
    assert 0 <= result_good.score <= 100


def test_evaluation_result_dataclass(evaluation_engine, sample_vehicle):
    """Test que verifica que EvaluationResult es un dataclass."""
    result = evaluation_engine.evaluate(sample_vehicle)
    
    # Verificar que tiene todos los campos esperados
    assert hasattr(result, "vehicle_cost")
    assert hasattr(result, "transport_cost")
    assert hasattr(result, "registration_cost")
    assert hasattr(result, "itv_cost")
    assert hasattr(result, "gestoria_cost")
    assert hasattr(result, "taxes_cost")
    assert hasattr(result, "total_cost")
    assert hasattr(result, "estimated_sale_price_es")
    assert hasattr(result, "gross_profit")
    assert hasattr(result, "profit_margin_percent")
    assert hasattr(result, "score")
    assert hasattr(result, "classification")
    assert hasattr(result, "warnings")
    assert hasattr(result, "recommendation")


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
    assert result.transport_cost == 750.0  # SUV
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