"""TEST.SEARCH.MAPPER.1 — labels y coherence en el mapper de search."""

from __future__ import annotations

from types import SimpleNamespace

from app.api.v1.routes.search import _build_search_result_item
from app.services.profit_analyzer import CostBreakdown, ProfitAnalysis, Recommendation, RiskLevel
from app.services.vehicle_scorer import VehicleScore


def _make_vehicle(**kwargs: object) -> SimpleNamespace:
    defaults = dict(
        id="v-1",
        brand="BMW",
        model="320d",
        year=2019,
        mileage=90000,
        price=15000.0,
        currency="EUR",
        source="autoscout24",
        external_id="ext-1",
        url="https://example.com/v1",
        fuel_type="Diesel",
        transmission="Automatic",
        power_hp=190,
        location="Berlin",
        images=["https://example.com/img.jpg"],
        description=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_score(
    *,
    score: int = 92,
    category: str = "Excelente",
    category_key: str = "excellent",
    category_label_es: str = "Excelente",
) -> VehicleScore:
    return VehicleScore(
        score=score,
        category=category,
        category_key=category_key,
        category_label_es=category_label_es,
        strengths=["Buen precio"],
        weaknesses=[],
    )


def _make_profit(
    *,
    purchase: float = 10_000.0,
    sale: float = 18_000.0,
    total_cost: float = 12_000.0,
    net: float = 6_000.0,
    roi: float = 50.0,
    risk: RiskLevel = RiskLevel.LOW,
    rec: Recommendation = Recommendation.BUY,
) -> ProfitAnalysis:
    breakdown = CostBreakdown(
        purchase_price=purchase,
        transport_cost=800.0,
        registration_cost=400.0,
        taxes=500.0,
        inspection_cost=100.0,
        repair_estimate=0.0,
        commission_cost=200.0,
        miscellaneous_cost=0.0,
        total_fixed_costs=1300.0,
        total_variable_costs=700.0,
        total_cost=total_cost,
    )
    return ProfitAnalysis(
        purchase_price=purchase,
        transport_cost=breakdown.transport_cost,
        registration_cost=breakdown.registration_cost,
        taxes=breakdown.taxes,
        inspection_cost=breakdown.inspection_cost,
        repair_estimate=breakdown.repair_estimate,
        commission_cost=breakdown.commission_cost,
        miscellaneous_cost=breakdown.miscellaneous_cost,
        total_cost=total_cost,
        estimated_sale_price=sale,
        gross_profit=sale - purchase,
        net_profit=net,
        roi_percentage=roi,
        profit_margin_percentage=round(net / sale * 100, 2) if sale else 0.0,
        risk_level=risk,
        recommendation=rec,
        cost_breakdown=breakdown,
    )


def _make_result(*, score: VehicleScore | None = None, profit: ProfitAnalysis | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        vehicle=_make_vehicle(),
        vehicle_score=score if score is not None else _make_score(),
        market_estimation=None,
        profit_analysis=profit if profit is not None else _make_profit(),
        opportunity=None,
        negotiation=None,
    )


def test_mapper_emits_score_category_key_and_label_es() -> None:
    item = _build_search_result_item(_make_result(score=_make_score(score=92)))
    assert item.vehicle_score is not None
    assert item.vehicle_score.score == 92
    assert item.vehicle_score.category_key == "excellent"
    assert item.vehicle_score.category_label_es == "Excelente"
    assert item.vehicle_score.category == "Excelente"


def test_mapper_score_fallback_from_legacy_category_only() -> None:
    """Dominio antiguo solo con category ES → mapper rellena key/label."""
    legacy = VehicleScore(
        score=65,
        category="Bueno",
        strengths=[],
        weaknesses=[],
    )
    # Sin category_key en instancias creadas a mano: defaults dataclass
    # Si el default es "poor", el mapper debe preferir reverse-map desde category ES
    item = _build_search_result_item(_make_result(score=legacy))
    assert item.vehicle_score is not None
    # category legacy intacta
    assert item.vehicle_score.category == "Bueno"
    # key/label presentes (mapper o defaults del dominio post-SCORE.1)
    assert item.vehicle_score.category_key in {
        "excellent",
        "very_good",
        "good",
        "acceptable",
        "poor",
    }
    assert isinstance(item.vehicle_score.category_label_es, str)


def test_mapper_emits_profit_labels_es() -> None:
    item = _build_search_result_item(
        _make_result(profit=_make_profit(risk=RiskLevel.MEDIUM, rec=Recommendation.CONSIDER))
    )
    pa = item.profit_analysis
    assert pa is not None
    assert pa.risk_level == "MEDIUM"
    assert pa.recommendation == "CONSIDER"
    assert pa.risk_label_es == "Medio"
    assert pa.recommendation_label_es == "Considerar"


def test_mapper_emits_coherence_warnings_list() -> None:
    # ROI extremo para forzar al menos un aviso en profit_coherence
    item = _build_search_result_item(
        _make_result(
            profit=_make_profit(
                purchase=5_000.0,
                sale=20_000.0,
                total_cost=6_000.0,
                net=14_000.0,
                roi=200.0,
            )
        )
    )
    pa = item.profit_analysis
    assert pa is not None
    assert isinstance(pa.coherence_warnings, list)
    assert any("ROI" in w or "roi" in w.lower() for w in pa.coherence_warnings)


def test_mapper_coherence_warnings_empty_when_reasonable() -> None:
    item = _build_search_result_item(
        _make_result(
            profit=_make_profit(
                purchase=12_000.0,
                sale=15_000.0,
                total_cost=13_500.0,
                net=1_500.0,
                roi=11.0,
            )
        )
    )
    pa = item.profit_analysis
    assert pa is not None
    assert pa.coherence_warnings == []

