"""Tests para app.services.confidence — única fuente de verdad de `confidence`.

Separa profitability (beneficio), risk (probabilidad de estar equivocado) y
confidence (fiabilidad de los datos usados). Ver TASK 2.
"""

from __future__ import annotations

from app.config.opportunity import CONFIDENCE_NO_MARKET_DATA_BASELINE
from app.services.confidence import estimate_confidence


class TestBasicBehavior:
    def test_uses_market_confidence_when_available(self) -> None:
        result = estimate_confidence(market_confidence=80.0, market_grounded=True)
        assert result == 80.0

    def test_never_exceeds_100(self) -> None:
        result = estimate_confidence(market_confidence=150.0, market_grounded=True)
        assert result <= 100.0

    def test_never_below_0(self) -> None:
        result = estimate_confidence(
            market_confidence=5.0,
            warnings=["disclaimer", "extra1", "extra2", "extra3", "extra4", "extra5"],
            weaknesses=["sin precio definido"] * 10,
            market_grounded=True,
        )
        assert result >= 0.0

    def test_no_market_data_uses_baseline(self) -> None:
        result = estimate_confidence(market_confidence=None, market_grounded=False)
        assert result == CONFIDENCE_NO_MARKET_DATA_BASELINE

    def test_market_not_grounded_caps_at_baseline_even_with_high_market_confidence(
        self,
    ) -> None:
        """Si el precio de venta no viene de comparables reales, la
        confianza no puede ser alta aunque exista una market_confidence
        residual alta de otra fuente — no se infla la confianza."""
        result = estimate_confidence(market_confidence=95.0, market_grounded=False)
        assert result <= CONFIDENCE_NO_MARKET_DATA_BASELINE


class TestPenalties:
    def test_missing_data_weakness_reduces_confidence(self) -> None:
        base = estimate_confidence(market_confidence=80.0, market_grounded=True)
        with_missing = estimate_confidence(
            market_confidence=80.0,
            weaknesses=["Sin comparativa de mercado: no se puede evaluar el precio"],
            market_grounded=True,
        )
        assert with_missing < base

    def test_unrelated_weakness_does_not_reduce_confidence(self) -> None:
        """Una debilidad que no señala datos faltantes (p. ej. kilometraje
        alto) no es un problema de confianza en los datos, es un problema
        de calidad del vehículo — no debe penalizar `confidence`."""
        base = estimate_confidence(market_confidence=80.0, market_grounded=True)
        with_weakness = estimate_confidence(
            market_confidence=80.0,
            weaknesses=["Kilometraje muy alto: 300,000 km"],
            market_grounded=True,
        )
        assert with_weakness == base

    def test_extra_warnings_reduce_confidence(self) -> None:
        base = estimate_confidence(
            market_confidence=80.0, warnings=["disclaimer"], market_grounded=True
        )
        with_extra = estimate_confidence(
            market_confidence=80.0,
            warnings=["disclaimer", "costes de importación anómalos"],
            market_grounded=True,
        )
        assert with_extra < base

    def test_disclaimer_alone_does_not_penalize(self) -> None:
        """ProfitAnalyzer siempre antepone un disclaimer estándar; por sí
        solo no debe penalizar (solo los avisos adicionales)."""
        with_only_disclaimer = estimate_confidence(
            market_confidence=80.0, warnings=["disclaimer estándar"], market_grounded=True
        )
        without_warnings = estimate_confidence(
            market_confidence=80.0, warnings=[], market_grounded=True
        )
        assert with_only_disclaimer == without_warnings

    def test_multiple_missing_fields_compound(self) -> None:
        one_missing = estimate_confidence(
            market_confidence=80.0,
            weaknesses=["sin precio definido"],
            market_grounded=True,
        )
        two_missing = estimate_confidence(
            market_confidence=80.0,
            weaknesses=["sin precio definido", "no especificado el kilometraje"],
            market_grounded=True,
        )
        assert two_missing < one_missing


class TestDeterminism:
    def test_same_inputs_produce_same_output(self) -> None:
        kwargs = dict(
            market_confidence=65.0,
            warnings=["disclaimer", "aviso extra"],
            weaknesses=["sin precio definido"],
            market_grounded=True,
        )
        assert estimate_confidence(**kwargs) == estimate_confidence(**kwargs)

    def test_result_has_two_decimal_precision(self) -> None:
        result = estimate_confidence(market_confidence=66.666, market_grounded=True)
        assert result == round(result, 2)
