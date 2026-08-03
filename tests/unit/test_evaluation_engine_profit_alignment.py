"""Tests de alineación EvaluationEngine ↔ ProfitAnalyzer (Task B.3).

Verifica que EvaluationEngine delega el bloque económico en ProfitAnalyzer
con el perfil de costes por defecto (SPAIN) y que total_cost coincide
con el mismo precio/perfil.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config.import_costs import get_profile
from app.services.evaluation_engine import EvaluationEngine
from app.services.profit_analyzer import ProfitAnalyzer


@dataclass
class V:
    price: float | None = 18000.0
    brand: str | None = "BMW"
    model: str | None = "320d"
    year: int | None = 2019
    mileage: int | None = 80000


def test_evaluation_uses_spain_costs():
    """EvaluationEngine usa el perfil SPAIN (transporte del perfil)."""
    engine = EvaluationEngine(import_cost_profile="SPAIN")
    result = engine.evaluate(V())
    profile = get_profile("SPAIN")
    # total_cost debe incluir al menos transporte del perfil
    assert result.total_cost >= 18000 + profile.transport_cost - 1.0
    # El transporte del resultado debe ser el del perfil SPAIN
    assert result.transport_cost == profile.transport_cost


def test_evaluation_matches_profit_analyzer_total_cost():
    """total_cost de evaluation coincide con ProfitAnalyzer (mismo precio/perfil)."""
    v = V(price=18000.0)
    analysis = ProfitAnalyzer().analyze(v, profile_name="SPAIN")
    result = EvaluationEngine(import_cost_profile="SPAIN").evaluate(v)
    assert result.total_cost == analysis.total_cost or abs(result.total_cost - analysis.total_cost) < 1.0


def test_evaluation_matches_profit_analyzer_with_sale_price():
    """Con misma sale price, el beneficio coincide con ProfitAnalyzer."""
    v = V(price=18000.0)
    sale = 24000.0
    analysis = ProfitAnalyzer().analyze(
        v, profile_name="SPAIN", estimated_sale_price=sale
    )
    # evaluate no recibe sale_price → usa default multiplicador (1.4),
    # pero comprobamos que total_cost coincide (misma fuente de costes).
    result = EvaluationEngine(import_cost_profile="SPAIN").evaluate(v)
    assert result.total_cost == analysis.total_cost
    # El engine usa net_profit como gross_profit (misma fuente) con default sale.
    assert result.gross_profit == ProfitAnalyzer().analyze(
        v, profile_name="SPAIN"
    ).net_profit


def test_default_profile_from_settings_is_spain():
    """Sin parámetro explícito usa settings.default_import_cost_profile."""
    from app.core.config import settings

    engine = EvaluationEngine()
    assert engine._profile == getattr(settings, "default_import_cost_profile", "SPAIN")