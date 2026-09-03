"""Tests para ProfitAnalyzer.calculate_max_purchase_price (TASK 2).

Cubre el cálculo inverso: dado un precio de venta y unos requisitos mínimos
de margen/ROI, ¿cuál es el precio de compra máximo que sigue cumpliéndolos?
"""

from __future__ import annotations

import pytest

from app.config.import_costs import get_profile
from app.services.profit_analyzer import MaxPurchasePriceResult, ProfitAnalyzer


@pytest.fixture
def analyzer() -> ProfitAnalyzer:
    return ProfitAnalyzer()


class TestBasicCalculation:
    def test_returns_max_purchase_price_result(self, analyzer: ProfitAnalyzer) -> None:
        result = analyzer.calculate_max_purchase_price(30000.0, "SPAIN")
        assert isinstance(result, MaxPurchasePriceResult)
        assert result.max_purchase_price > 0

    def test_higher_sale_price_allows_higher_purchase_price(
        self, analyzer: ProfitAnalyzer
    ) -> None:
        low = analyzer.calculate_max_purchase_price(20000.0, "SPAIN")
        high = analyzer.calculate_max_purchase_price(40000.0, "SPAIN")
        assert high.max_purchase_price > low.max_purchase_price

    def test_result_never_exceeds_sale_price(self, analyzer: ProfitAnalyzer) -> None:
        """El precio máximo de compra nunca puede superar el de venta:
        no tendría sentido pagar más de lo que se espera cobrar."""
        result = analyzer.calculate_max_purchase_price(20000.0, "SPAIN")
        assert result.max_purchase_price < 20000.0

    def test_forward_calculation_meets_minimum_margin(
        self, analyzer: ProfitAnalyzer
    ) -> None:
        """Verificación cruzada: comprar exactamente al max_purchase_price
        calculado debe producir (aprox.) el margen mínimo solicitado, no menos."""
        sale_price = 30000.0
        result = analyzer.calculate_max_purchase_price(
            sale_price, "SPAIN", min_margin_percentage=15.0, min_roi_percentage=10.0
        )

        class _V:
            price = result.max_purchase_price

        analysis = analyzer.analyze(_V(), profile_name="SPAIN", estimated_sale_price=sale_price)
        # Redondeado hacia abajo (conservador): el margen real debe ser >= el mínimo.
        assert analysis.profit_margin_percentage >= 15.0 - 0.5

    def test_forward_calculation_meets_minimum_margin_with_iedmt(
        self, analyzer: ProfitAnalyzer
    ) -> None:
        """Verificación cruzada con IEDMT (vendedor particular, España, CO2
        real): sin sumar IEDMT en el cálculo inverso, el precio máximo
        resultante superaba el que realmente cumple min_margin/min_roi al
        pasar por analyze() (que sí aplica IEDMT también a particulares:
        es un impuesto de matriculación, no de la transacción)."""
        sale_price = 30000.0
        co2_gkm = 150.0  # por encima del umbral: IEDMT > 0
        result = analyzer.calculate_max_purchase_price(
            sale_price,
            "SPAIN",
            min_margin_percentage=15.0,
            min_roi_percentage=10.0,
            co2_gkm=co2_gkm,
        )

        class _V:
            price = result.max_purchase_price
            emissions = "150 g/km"

        analysis = analyzer.analyze(_V(), profile_name="SPAIN", estimated_sale_price=sale_price)
        assert analysis.profit_margin_percentage >= 15.0 - 0.5

    def test_binding_constraint_is_margin_or_roi(self, analyzer: ProfitAnalyzer) -> None:
        result = analyzer.calculate_max_purchase_price(30000.0, "SPAIN")
        assert result.binding_constraint in ("margin", "roi")

    def test_higher_min_margin_reduces_max_purchase_price(
        self, analyzer: ProfitAnalyzer
    ) -> None:
        low_margin = analyzer.calculate_max_purchase_price(
            30000.0, "SPAIN", min_margin_percentage=10.0
        )
        high_margin = analyzer.calculate_max_purchase_price(
            30000.0, "SPAIN", min_margin_percentage=30.0
        )
        assert high_margin.max_purchase_price < low_margin.max_purchase_price

    def test_risk_buffer_reduces_max_purchase_price(self, analyzer: ProfitAnalyzer) -> None:
        no_buffer = analyzer.calculate_max_purchase_price(
            30000.0, "SPAIN", risk_buffer_percentage=0.0
        )
        with_buffer = analyzer.calculate_max_purchase_price(
            30000.0, "SPAIN", risk_buffer_percentage=10.0
        )
        assert with_buffer.max_purchase_price < no_buffer.max_purchase_price
        assert with_buffer.effective_sale_price == pytest.approx(27000.0, abs=0.01)

    def test_uses_profile_fixed_and_variable_costs(self, analyzer: ProfitAnalyzer) -> None:
        profile = get_profile("SPAIN")
        result = analyzer.calculate_max_purchase_price(30000.0, "SPAIN")
        expected_fixed = (
            profile.transport_cost
            + profile.registration_cost
            + profile.inspection_cost
            + profile.paperwork_cost
            + profile.miscellaneous_cost
        )
        assert result.fixed_costs == pytest.approx(expected_fixed, abs=0.01)


class TestDealerVsPrivate:
    def test_dealer_has_lower_max_purchase_price_than_private(
        self, analyzer: ProfitAnalyzer
    ) -> None:
        """AUD-009: IVA pleno (dealer) es más caro que régimen de margen
        (particular) → el precio máximo de compra debe ser menor."""
        private_result = analyzer.calculate_max_purchase_price(
            30000.0, "SPAIN", seller_type="private"
        )
        dealer_result = analyzer.calculate_max_purchase_price(
            30000.0, "SPAIN", seller_type="dealer"
        )
        assert dealer_result.max_purchase_price < private_result.max_purchase_price
        assert dealer_result.is_dealer is True
        assert private_result.is_dealer is False

    def test_unknown_seller_type_defaults_to_private(self, analyzer: ProfitAnalyzer) -> None:
        result = analyzer.calculate_max_purchase_price(
            30000.0, "SPAIN", seller_type="something-unrecognized"
        )
        assert result.is_dealer is False


class TestEdgeCases:
    def test_zero_sale_price_raises(self, analyzer: ProfitAnalyzer) -> None:
        with pytest.raises(ValueError):
            analyzer.calculate_max_purchase_price(0.0, "SPAIN")

    def test_negative_sale_price_raises(self, analyzer: ProfitAnalyzer) -> None:
        with pytest.raises(ValueError):
            analyzer.calculate_max_purchase_price(-1000.0, "SPAIN")

    def test_margin_of_100_percent_raises(self, analyzer: ProfitAnalyzer) -> None:
        with pytest.raises(ValueError):
            analyzer.calculate_max_purchase_price(
                30000.0, "SPAIN", min_margin_percentage=100.0
            )

    def test_negative_margin_raises(self, analyzer: ProfitAnalyzer) -> None:
        with pytest.raises(ValueError):
            analyzer.calculate_max_purchase_price(
                30000.0, "SPAIN", min_margin_percentage=-5.0
            )

    def test_negative_roi_raises(self, analyzer: ProfitAnalyzer) -> None:
        with pytest.raises(ValueError):
            analyzer.calculate_max_purchase_price(
                30000.0, "SPAIN", min_roi_percentage=-1.0
            )

    def test_negative_risk_buffer_raises(self, analyzer: ProfitAnalyzer) -> None:
        with pytest.raises(ValueError):
            analyzer.calculate_max_purchase_price(
                30000.0, "SPAIN", risk_buffer_percentage=-1.0
            )

    def test_risk_buffer_of_100_percent_raises(self, analyzer: ProfitAnalyzer) -> None:
        with pytest.raises(ValueError):
            analyzer.calculate_max_purchase_price(
                30000.0, "SPAIN", risk_buffer_percentage=100.0
            )

    def test_low_sale_price_can_yield_zero_max_purchase_price(
        self, analyzer: ProfitAnalyzer
    ) -> None:
        """Cuando los costes fijos por sí solos ya superan lo que permite el
        margen requerido, no hay ningún precio de compra positivo que
        cumpla el requisito: el resultado se limita a 0, no a un negativo."""
        result = analyzer.calculate_max_purchase_price(
            500.0, "SPAIN", min_margin_percentage=50.0
        )
        assert result.max_purchase_price == 0.0

    def test_zero_roi_requirement_is_valid(self, analyzer: ProfitAnalyzer) -> None:
        """min_roi_percentage=0 es un límite válido (romper apenas break-even)."""
        result = analyzer.calculate_max_purchase_price(
            30000.0, "SPAIN", min_roi_percentage=0.0
        )
        assert result.max_purchase_price > 0

    def test_result_is_rounded_to_cents(self, analyzer: ProfitAnalyzer) -> None:
        result = analyzer.calculate_max_purchase_price(30001.37, "SPAIN")
        # No debe haber más de 2 decimales (artefactos de punto flotante).
        cents = round(result.max_purchase_price * 100)
        assert abs(result.max_purchase_price * 100 - cents) < 1e-6
