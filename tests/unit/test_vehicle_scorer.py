"""Tests para el VehicleScorer — Motor de puntuación objective de vehículos."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from app.config.scoring import (
    SCORE_ACCEPTABLE,
    SCORE_EXCELLENT,
    SCORE_GOOD,
    SCORE_VERY_GOOD,
)
from app.services.vehicle_scorer import (
    ScoreReason,
    VehicleScore,
    VehicleScorer,
)

# =============================================================================
# Fixture helpers: crea objetos duck-typed que cumplen VehicleData
# =============================================================================


@dataclass
class VehicleStub:
    """Stub mínimo para pruebas de VehicleScorer."""

    price: float | None = None
    mileage: int | None = None
    year: int | None = None
    fuel_type: str | None = None
    transmission: str | None = None
    power_hp: int | None = None
    description: str | None = None
    images: Any = None
    brand: str | None = "TestBrand"
    model: str | None = "TestModel"


@pytest.fixture
def scorer() -> VehicleScorer:
    return VehicleScorer()


@pytest.fixture
def perfect_vehicle() -> VehicleStub:
    """Vehículo excelente en todos los aspectos."""
    return VehicleStub(
        price=15000.0,
        mileage=15000,
        year=2024,
        fuel_type="electric",
        transmission="automatic",
        power_hp=150,
        description="Vehículo en perfecto estado, revisión oficial, garaje, historial completo.",
        images=["img1.jpg", "img2.jpg", "img3.jpg"],
        brand="Tesla",
        model="Model 3",
    )


@pytest.fixture
def terrible_vehicle() -> VehicleStub:
    """Vehículo malo en todos los aspectos."""
    return VehicleStub(
        price=None,
        mileage=300000,
        year=2000,
        fuel_type=None,
        transmission=None,
        power_hp=None,
        description=None,
        images=None,
        brand=None,
        model=None,
    )


# =============================================================================
# Tests básicos de estructura
# =============================================================================


class TestVehicleScoreStructure:
    """Verifica que la estructura de VehicleScore es correcta."""

    def test_score_reason_creation(self) -> None:
        reason = ScoreReason(
            reason="Test reason",
            impact=10.0,
            is_positive=True,
            category="test",
        )
        assert reason.reason == "Test reason"
        assert reason.impact == 10.0
        assert reason.is_positive is True
        assert reason.category == "test"

    def test_vehicle_score_defaults(self) -> None:
        score = VehicleScore(score=50, category="Bueno")
        assert score.score == 50
        assert score.category == "Bueno"
        assert score.reasons == []
        assert score.strengths == []
        assert score.weaknesses == []

    def test_vehicle_score_with_lists(self) -> None:
        reasons = [ScoreReason("R1", 5.0, True, "cat1")]
        score = VehicleScore(
            score=80,
            category="Excelente",
            reasons=reasons,
            strengths=["S1"],
            weaknesses=["W1"],
        )
        assert score.score == 80
        assert score.category == "Excelente"
        assert len(score.reasons) == 1
        assert score.strengths == ["S1"]
        assert score.weaknesses == ["W1"]


class TestVehicleScorerInstantiation:
    """Verifica que el scorer se instancia correctamente."""

    def test_create_scorer(self) -> None:
        scorer = VehicleScorer()
        result = scorer.score(VehicleStub(price=10000.0, year=2020, mileage=50000))
        assert result is not None
        assert callable(scorer.score)
        assert callable(scorer.score_from_dto)

    def test_score_returns_vehicle_score(self, scorer: VehicleScorer, perfect_vehicle: VehicleStub) -> None:
        result = scorer.score(perfect_vehicle)
        assert isinstance(result, VehicleScore)
        assert isinstance(result.score, int)
        assert 0 <= result.score <= 100
        assert isinstance(result.category, str)
        assert isinstance(result.reasons, list)
        assert isinstance(result.strengths, list)
        assert isinstance(result.weaknesses, list)


# =============================================================================
# Tests de categorías
# =============================================================================


class TestCategoryMapping:
    """Verifica que la categorización es correcta."""

    def test_excellent_category(self, scorer: VehicleScorer, perfect_vehicle: VehicleStub) -> None:
        result = scorer.score(perfect_vehicle)
        assert result.category == "Excelente"
        assert result.score >= SCORE_EXCELLENT

    def test_malo_category(self, scorer: VehicleScorer, terrible_vehicle: VehicleStub) -> None:
        result = scorer.score(terrible_vehicle)
        assert result.category == "Malo"
        assert result.score < 30

    def test_bueno_category(self, scorer: VehicleScorer) -> None:
        # year=2020 → age=6 → moderate bonus; 3 images for better ad quality
        vehicle = VehicleStub(
            price=25000.0,
            mileage=80000,
            year=2020,
            fuel_type="diesel",
            transmission="manual",
            power_hp=90,
            description="Coche en buen estado",
            images=["img1.jpg", "img2.jpg", "img3.jpg"],
            brand="Ford",
            model="Focus",
        )
        result = scorer.score(vehicle)
        assert SCORE_GOOD <= result.score < SCORE_VERY_GOOD
        assert result.category == "Bueno"

    def test_aceptable_category(self, scorer: VehicleScorer) -> None:
        # mileage=120k (moderate, ≤150k), year=2017 (age=9, old penalizado)
        vehicle = VehicleStub(
            price=5000.0,
            mileage=120000,
            year=2017,
            fuel_type="petrol",
            transmission="manual",
            power_hp=60,
            description="Coche",
            images=["img1.jpg"],
            brand="Seat",
            model="Ibiza",
        )
        result = scorer.score(vehicle)
        assert SCORE_ACCEPTABLE <= result.score < SCORE_GOOD
        assert result.category == "Aceptable"

    def test_category_key_and_label_alignment(self) -> None:
        from app.services.vehicle_scorer import SCORE_CATEGORY_LABELS_ES

        assert VehicleScorer._get_category_key(95) == "excellent"
        assert VehicleScorer._get_category(95) == "Excelente"
        assert SCORE_CATEGORY_LABELS_ES["poor"] == "Malo"

    def test_score_populates_category_key_and_label(self, scorer: VehicleScorer, perfect_vehicle: VehicleStub) -> None:
        result = scorer.score(perfect_vehicle)
        assert result.category == "Excelente"
        assert result.category_key == "excellent"
        assert result.category_label_es == "Excelente"


# =============================================================================
# Tests de precio
# =============================================================================


class TestPriceEvaluation:
    """Tests para la evaluación del precio."""

    def test_no_price_penalty(self, scorer: VehicleScorer) -> None:
        vehicle = VehicleStub(price=None)
        result = scorer.score(vehicle)
        assert any("sin precio" in r.reason.lower() and not r.is_positive for r in result.reasons)
        assert "Vehículo sin precio definido" in result.weaknesses

    def test_zero_price_penalty(self, scorer: VehicleScorer) -> None:
        vehicle = VehicleStub(price=0.0)
        result = scorer.score(vehicle)
        assert any("sin precio" in r.reason.lower() and not r.is_positive for r in result.reasons)

    def test_price_defined_bonus(self, scorer: VehicleScorer) -> None:
        vehicle = VehicleStub(price=20000.0)
        result = scorer.score(vehicle)
        assert any("precio definido" in r.reason.lower() and r.is_positive for r in result.reasons)
        assert any("precio competitivo" in r.reason.lower() and r.is_positive for r in result.reasons)


# =============================================================================
# Tests de kilometraje
# =============================================================================


class TestMileageEvaluation:
    """Tests para la evaluación del kilometraje."""

    def test_low_mileage_bonus(self, scorer: VehicleScorer) -> None:
        vehicle = VehicleStub(mileage=10000)
        result = scorer.score(vehicle)
        assert any("bajo kilometraje" in r.reason.lower() and r.is_positive for r in result.reasons)

    def test_moderate_mileage(self, scorer: VehicleScorer) -> None:
        vehicle = VehicleStub(mileage=80000)
        result = scorer.score(vehicle)
        assert any("kilometraje moderado" in r.reason.lower() for r in result.reasons)

    def test_high_mileage_penalty(self, scorer: VehicleScorer) -> None:
        vehicle = VehicleStub(mileage=180000)
        result = scorer.score(vehicle)
        assert any("kilometraje alto" in r.reason.lower() and not r.is_positive for r in result.reasons)

    def test_very_high_mileage_penalty(self, scorer: VehicleScorer) -> None:
        vehicle = VehicleStub(mileage=300000)
        result = scorer.score(vehicle)
        assert any("kilometraje muy alto" in r.reason.lower() and not r.is_positive for r in result.reasons)

    def test_mileage_not_specified(self, scorer: VehicleScorer) -> None:
        vehicle = VehicleStub(mileage=None)
        result = scorer.score(vehicle)
        assert any("kilometraje no especificado" in r.reason.lower() for r in result.reasons)


# =============================================================================
# Tests de antigüedad
# =============================================================================


class TestAgeEvaluation:
    """Tests para la evaluación de la antigüedad."""

    def test_recent_vehicle_bonus(self, scorer: VehicleScorer) -> None:
        vehicle = VehicleStub(year=2024)
        result = scorer.score(vehicle)
        assert any("reciente" in r.reason.lower() and r.is_positive for r in result.reasons)

    def test_moderate_age_bonus(self, scorer: VehicleScorer) -> None:
        vehicle = VehicleStub(year=2021)
        result = scorer.score(vehicle)
        assert any("antigüedad moderada" in r.reason.lower() for r in result.reasons)

    def test_old_vehicle_penalty(self, scorer: VehicleScorer) -> None:
        vehicle = VehicleStub(year=2008)
        result = scorer.score(vehicle)
        assert any("antiguo" in r.reason.lower() and not r.is_positive for r in result.reasons)

    def test_very_old_vehicle_penalty(self, scorer: VehicleScorer) -> None:
        vehicle = VehicleStub(year=1995)
        result = scorer.score(vehicle)
        assert any("excesivamente antiguo" in r.reason.lower() and not r.is_positive for r in result.reasons)

    def test_year_not_specified(self, scorer: VehicleScorer) -> None:
        vehicle = VehicleStub(year=None)
        result = scorer.score(vehicle)
        assert any("año de fabricación no especificado" in r.reason.lower() for r in result.reasons)

    def test_future_year(self, scorer: VehicleScorer) -> None:
        vehicle = VehicleStub(year=2030)
        result = scorer.score(vehicle)
        # Should treat as recent (positive impact)
        positive_age = [r for r in result.reasons if r.category == "age" and r.is_positive]
        assert len(positive_age) > 0


# =============================================================================
# Tests de combustible
# =============================================================================


class TestFuelTypeEvaluation:
    """Tests para la evaluación del tipo de combustible."""

    @pytest.mark.parametrize("fuel_type,expected_positive", [
        ("electric", True),
        ("hybrid", True),
        ("diesel", True),
        ("gasoline", True),
        ("petrol", True),
        ("lpg", True),
        ("cng", True),
        ("hydrogen", True),
        ("ethanol", True),
        (None, False),
    ])
    def test_fuel_type_scoring(self, scorer: VehicleScorer, fuel_type: str | None, expected_positive: bool) -> None:
        vehicle = VehicleStub(fuel_type=fuel_type)
        result = scorer.score(vehicle)
        fuel_reasons = [r for r in result.reasons if r.category == "fuel_type"]
        assert len(fuel_reasons) == 1
        if expected_positive:
            assert fuel_reasons[0].is_positive
        else:
            assert not fuel_reasons[0].is_positive

    def test_electric_scores_higher_than_diesel(self, scorer: VehicleScorer) -> None:
        electric = scorer.score(VehicleStub(fuel_type="electric"))
        diesel = scorer.score(VehicleStub(fuel_type="diesel"))
        electric_fuel_impact = sum(r.impact for r in electric.reasons if r.category == "fuel_type")
        diesel_fuel_impact = sum(r.impact for r in diesel.reasons if r.category == "fuel_type")
        assert electric_fuel_impact > diesel_fuel_impact


# =============================================================================
# Tests de transmisión
# =============================================================================


class TestTransmissionEvaluation:
    """Tests para la evaluación del tipo de transmisión."""

    @pytest.mark.parametrize("transmission,expected_positive", [
        ("automatic", True),
        ("manual", True),
        ("semi-automatic", True),
        ("dsg", True),
        ("cvt", True),
        ("tiptronic", True),
        (None, False),
    ])
    def test_transmission_scoring(self, scorer: VehicleScorer, transmission: str | None, expected_positive: bool) -> None:
        vehicle = VehicleStub(transmission=transmission)
        result = scorer.score(vehicle)
        trans_reasons = [r for r in result.reasons if r.category == "transmission"]
        assert len(trans_reasons) == 1
        if expected_positive:
            assert trans_reasons[0].is_positive
        else:
            assert not trans_reasons[0].is_positive

    def test_automatic_scores_higher_than_manual(self, scorer: VehicleScorer) -> None:
        auto = scorer.score(VehicleStub(transmission="automatic"))
        manual = scorer.score(VehicleStub(transmission="manual"))
        auto_impact = sum(r.impact for r in auto.reasons if r.category == "transmission")
        manual_impact = sum(r.impact for r in manual.reasons if r.category == "transmission")
        assert auto_impact > manual_impact


# =============================================================================
# Tests de potencia
# =============================================================================


class TestPowerEvaluation:
    """Tests para la evaluación de la potencia."""

    def test_optimal_power_bonus(self, scorer: VehicleScorer) -> None:
        vehicle = VehicleStub(power_hp=150)
        result = scorer.score(vehicle)
        assert any("potencia óptima" in r.reason.lower() and r.is_positive for r in result.reasons)

    def test_moderate_power_bonus(self, scorer: VehicleScorer) -> None:
        vehicle = VehicleStub(power_hp=80)
        result = scorer.score(vehicle)
        assert any("potencia moderada" in r.reason.lower() for r in result.reasons)

    def test_power_out_of_range_penalty(self, scorer: VehicleScorer) -> None:
        vehicle = VehicleStub(power_hp=500)
        result = scorer.score(vehicle)
        assert any("potencia fuera de rango" in r.reason.lower() and not r.is_positive for r in result.reasons)

    def test_low_power_out_of_range(self, scorer: VehicleScorer) -> None:
        vehicle = VehicleStub(power_hp=30)
        result = scorer.score(vehicle)
        assert any("potencia fuera de rango" in r.reason.lower() and not r.is_positive for r in result.reasons)

    def test_power_not_specified(self, scorer: VehicleScorer) -> None:
        vehicle = VehicleStub(power_hp=None)
        result = scorer.score(vehicle)
        assert any("potencia no especificada" in r.reason.lower() for r in result.reasons)


# =============================================================================
# Tests de completitud
# =============================================================================


class TestCompletenessEvaluation:
    """Tests para la evaluación de la completitud de la información."""

    def test_complete_vehicle(self, scorer: VehicleScorer, perfect_vehicle: VehicleStub) -> None:
        result = scorer.score(perfect_vehicle)
        assert any("información completa" in r.reason.lower() for r in result.reasons)

    def test_incomplete_vehicle(self, scorer: VehicleScorer, terrible_vehicle: VehicleStub) -> None:
        result = scorer.score(terrible_vehicle)
        completeness_reasons = [r for r in result.reasons if r.category == "completeness"]
        assert len(completeness_reasons) >= 1
        assert any(not r.is_positive for r in completeness_reasons)

    def test_partial_information(self, scorer: VehicleScorer) -> None:
        """Vehículo con algunos campos faltantes."""
        vehicle = VehicleStub(
            brand="BMW",
            model="Serie 3",
            price=25000.0,
            year=2020,
            mileage=50000,
            # fuel_type, transmission, power_hp missing
        )
        result = scorer.score(vehicle)
        completeness_reasons = [r for r in result.reasons if r.category == "completeness"]
        assert len(completeness_reasons) >= 1
        # Should have some penalty (3 fields missing out of 8)
        penalty_reasons = [r for r in completeness_reasons if not r.is_positive]
        assert len(penalty_reasons) > 0


# =============================================================================
# Tests de calidad del anuncio
# =============================================================================


class TestAdQualityEvaluation:
    """Tests para la evaluación de la calidad del anuncio."""

    def test_no_images_penalty(self, scorer: VehicleScorer) -> None:
        vehicle = VehicleStub(images=None, description="Test")
        result = scorer.score(vehicle)
        assert any("sin imágenes" in r.reason.lower() and not r.is_positive for r in result.reasons)

    def test_single_image(self, scorer: VehicleScorer) -> None:
        vehicle = VehicleStub(images=["img1.jpg"], description="Test")
        result = scorer.score(vehicle)
        assert any("1 imagen" in r.reason.lower() and r.is_positive for r in result.reasons)

    def test_multiple_images(self, scorer: VehicleScorer) -> None:
        vehicle = VehicleStub(
            images=["img1.jpg", "img2.jpg", "img3.jpg", "img4.jpg", "img5.jpg"],
            description="Test",
        )
        result = scorer.score(vehicle)
        assert any("5 imagenes disponibles" in r.reason.lower() and r.is_positive for r in result.reasons)

    def test_images_as_comma_separated_string(self, scorer: VehicleScorer) -> None:
        vehicle = VehicleStub(
            images="img1.jpg,img2.jpg,img3.jpg",
            description="Test",
        )
        result = scorer.score(vehicle)
        assert any("3 imagenes disponibles" in r.reason.lower() for r in result.reasons)

    def test_no_description_penalty(self, scorer: VehicleScorer) -> None:
        vehicle = VehicleStub(images=["img1.jpg"], description=None)
        result = scorer.score(vehicle)
        assert any("sin descripción" in r.reason.lower() and not r.is_positive for r in result.reasons)

    def test_long_description_bonus(self, scorer: VehicleScorer) -> None:
        vehicle = VehicleStub(
            images=["img1.jpg"],
            description="Vehículo en perfecto estado de conservación. " * 10,
        )
        result = scorer.score(vehicle)
        assert any("descripción detallada" in r.reason.lower() and r.is_positive for r in result.reasons)

    def test_short_description_bonus(self, scorer: VehicleScorer) -> None:
        vehicle = VehicleStub(
            images=["img1.jpg"],
            description="Coche en buen estado, revisiones al día.",
        )
        result = scorer.score(vehicle)
        assert any("descripción breve" in r.reason.lower() for r in result.reasons)


# =============================================================================
# Tests de integración (escenarios completos)
# =============================================================================


class TestFullScenarios:
    """Escenarios completos que validan el scoring global."""

    def test_perfect_vehicle_scores_excellent(self, scorer: VehicleScorer, perfect_vehicle: VehicleStub) -> None:
        result = scorer.score(perfect_vehicle)
        assert result.category == "Excelente"
        assert result.score >= 90
        assert len(result.strengths) >= 5
        assert len(result.weaknesses) == 0

    def test_terrible_vehicle_scores_malo(self, scorer: VehicleScorer, terrible_vehicle: VehicleStub) -> None:
        result = scorer.score(terrible_vehicle)
        assert result.category == "Malo"
        assert result.score < 30
        assert len(result.weaknesses) >= 3

    def test_mid_range_vehicle(self, scorer: VehicleScorer) -> None:
        """Vehículo promedio con algunas carencias."""
        vehicle = VehicleStub(
            price=18000.0,
            mileage=95000,
            year=2020,
            fuel_type="diesel",
            transmission="manual",
            power_hp=110,
            description="Coche en buen estado general.",
            images=["img1.jpg", "img2.jpg"],
            brand="Volkswagen",
            model="Golf",
        )
        result = scorer.score(vehicle)
        assert 50 <= result.score <= 85
        assert result.category in ("Bueno", "Muy bueno", "Aceptable")
        assert len(result.reasons) > 0

    def test_high_mileage_old_vehicle(self, scorer: VehicleScorer) -> None:
        """Vehículo con mucho kilometraje y antiguo."""
        vehicle = VehicleStub(
            price=3000.0,
            mileage=280000,
            year=2005,
            fuel_type="diesel",
            transmission="manual",
            power_hp=90,
            description="Coche viejo",
            images=[],
            brand="Renault",
            model="Clio",
        )
        result = scorer.score(vehicle)
        assert result.category == "Malo"
        assert result.score < 40

    def test_low_mileage_new_vehicle(self, scorer: VehicleScorer) -> None:
        """Vehículo nuevo con pocos km."""
        vehicle = VehicleStub(
            price=35000.0,
            mileage=5000,
            year=2024,
            fuel_type="hybrid",
            transmission="automatic",
            power_hp=180,
            description="Nuevo, apenas rodado, con todas las prestaciones.",
            images=["img1.jpg", "img2.jpg", "img3.jpg", "img4.jpg"],
            brand="Toyota",
            model="Corolla",
        )
        result = scorer.score(vehicle)
        assert result.category in ("Excelente", "Muy bueno")
        assert result.score >= 80

    def test_vehicle_with_empty_images_string(self, scorer: VehicleScorer) -> None:
        """Vehículo con images como string vacío."""
        vehicle = VehicleStub(
            price=10000.0,
            mileage=60000,
            year=2015,
            fuel_type="petrol",
            transmission="manual",
            power_hp=100,
            description="Coche correcto",
            images="",
            brand="Opel",
            model="Astra",
        )
        result = scorer.score(vehicle)
        assert any("sin imágenes" in r.reason.lower() for r in result.reasons)

    def test_different_fuel_type_case_insensitive(self, scorer: VehicleScorer) -> None:
        """El scorer debe ser case-insensitive con tipos de combustible."""
        lower = scorer.score(VehicleStub(fuel_type="electric"))
        upper = scorer.score(VehicleStub(fuel_type="Electric"))
        mixed = scorer.score(VehicleStub(fuel_type="ELECTRIC"))
        assert lower.score == upper.score == mixed.score


# =============================================================================
# Tests de score_from_dto
# =============================================================================


class TestScoreFromDTO:
    """Tests para el método score_from_dto."""

    def test_score_from_dto_basic(self, scorer: VehicleScorer) -> None:
        result = scorer.score_from_dto(
            price=20000.0,
            mileage=30000,
            year=2022,
            fuel_type="electric",
            transmission="automatic",
            power_hp=200,
            description="Coche en perfecto estado",
            images=["img1.jpg", "img2.jpg"],
            brand="Tesla",
            model="Model Y",
        )
        assert isinstance(result, VehicleScore)
        assert result.score >= 80

    def test_score_from_dto_minimal(self, scorer: VehicleScorer) -> None:
        """Vehículo con datos mínimos."""
        result = scorer.score_from_dto(
            brand="Ford",
            model="Fiesta",
            price=5000.0,
        )
        assert isinstance(result, VehicleScore)
        assert 0 <= result.score <= 100

    def test_score_from_dto_empty(self, scorer: VehicleScorer) -> None:
        """Vehículo sin datos."""
        result = scorer.score_from_dto()
        assert isinstance(result, VehicleScore)
        assert result.score < 30

    def test_score_from_dto_with_extra_kwargs(self, scorer: VehicleScorer) -> None:
        """kwargs extra deben ser ignorados."""
        result = scorer.score_from_dto(
            brand="Audi",
            model="A4",
            price=30000.0,
            mileage=20000,
            year=2023,
            fuel_type="diesel",
            transmission="automatic",
            power_hp=190,
            description="Impecable",
            images=["img1.jpg"],
            extra_field="should be ignored",
            another_extra=123,
        )
        assert isinstance(result, VehicleScore)
        assert result.score >= 70


# =============================================================================
# Tests de regresión y casos borde
# =============================================================================


class TestEdgeCases:
    """Casos borde que podrían causar errores."""

    def test_score_range_bounds(self, scorer: VehicleScorer) -> None:
        """El score siempre debe estar entre 0 y 100."""
        # Vehículo pésimo
        bad = VehicleStub(
            price=None,
            mileage=999999,
            year=1900,
            fuel_type=None,
            transmission=None,
            power_hp=None,
            description=None,
            images=None,
            brand=None,
            model=None,
        )
        result = scorer.score(bad)
        assert 0 <= result.score <= 100

        # Vehículo excelente
        good = VehicleStub(
            price=50000.0,
            mileage=100,
            year=2025,
            fuel_type="electric",
            transmission="automatic",
            power_hp=200,
            description="Excelente " * 50,
            images=["a.jpg"] * 20,
            brand="BMW",
            model="i4",
        )
        result = scorer.score(good)
        assert 0 <= result.score <= 100

    def test_zero_mileage(self, scorer: VehicleScorer) -> None:
        """0 km debe tratarse como bajo kilometraje."""
        vehicle = VehicleStub(mileage=0)
        result = scorer.score(vehicle)
        assert any("bajo kilometraje" in r.reason.lower() for r in result.reasons)

    def test_negative_price(self, scorer: VehicleScorer) -> None:
        """Precio negativo debe tratarse como sin precio."""
        vehicle = VehicleStub(price=-100.0)
        result = scorer.score(vehicle)
        assert any("sin precio" in r.reason.lower() for r in result.reasons)

    def test_empty_string_fields(self, scorer: VehicleScorer) -> None:
        """Campos con string vacío deben contar como faltantes."""
        vehicle = VehicleStub(
            brand="",
            model="",
            price=None,
            mileage=None,
            year=None,
            fuel_type="",
            transmission="",
            power_hp=None,
            description="",
            images=None,
        )
        result = scorer.score(vehicle)
        # Should have completeness penalty
        comp_reasons = [r for r in result.reasons if r.category == "completeness"]
        assert any(not r.is_positive for r in comp_reasons)

    def test_many_reasons_returned(self, scorer: VehicleScorer, perfect_vehicle: VehicleStub) -> None:
        """Un vehículo completo debe generar múltiples razones."""
        result = scorer.score(perfect_vehicle)
        assert len(result.reasons) >= 8  # Al menos una razón por categoría

    def test_strengths_and_weaknesses_mutually_exclusive(
        self, scorer: VehicleScorer, perfect_vehicle: VehicleStub
    ) -> None:
        """Fortalezas y debilidades no deben solaparse."""
        result = scorer.score(perfect_vehicle)
        for s in result.strengths:
            assert s not in result.weaknesses
        for w in result.weaknesses:
            assert w not in result.strengths


# =============================================================================
# Tests de consistencia
# =============================================================================


class TestConsistency:
    """Pruebas de consistencia: mismos datos → mismos resultados."""

    def test_deterministic_results(self, scorer: VehicleScorer) -> None:
        """El scorer debe ser determinista."""
        vehicle = VehicleStub(
            price=15000.0,
            mileage=75000,
            year=2019,
            fuel_type="diesel",
            transmission="manual",
            power_hp=120,
            description="Coche correcto",
            images=["img.jpg"],
            brand="Seat",
            model="Leon",
        )

        result1 = scorer.score(vehicle)
        result2 = scorer.score(vehicle)

        assert result1.score == result2.score
        assert result1.category == result2.category
        assert len(result1.reasons) == len(result2.reasons)
        assert result1.strengths == result2.strengths
        assert result1.weaknesses == result2.weaknesses

    def test_different_instances_same_result(self, perfect_vehicle: VehicleStub) -> None:
        """Diferentes instancias del scorer deben producir el mismo resultado."""
        scorer1 = VehicleScorer()
        scorer2 = VehicleScorer()

        r1 = scorer1.score(perfect_vehicle)
        r2 = scorer2.score(perfect_vehicle)

        assert r1.score == r2.score
        assert r1.category == r2.category

