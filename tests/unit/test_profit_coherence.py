"""Unit tests for ROI.1 profit coherence warnings."""

from __future__ import annotations

from app.services.profit_coherence import build_coherence_warnings


def test_roi_very_high_warns() -> None:
    w = build_coherence_warnings(
        purchase_price=5000,
        total_cost=6000,
        estimated_profit=20000,
        roi=300,
        market_price=25000,
    )
    assert any("150" in x or "alto" in x.lower() for x in w)


def test_normal_no_warnings() -> None:
    w = build_coherence_warnings(
        purchase_price=10000,
        total_cost=12000,
        estimated_profit=1500,
        roi=12.5,
        market_price=13500,
    )
    assert w == []


def test_non_positive_purchase_price_warns() -> None:
    w = build_coherence_warnings(
        purchase_price=0,
        total_cost=1000,
        estimated_profit=500,
        roi=10,
    )
    assert any("precio de compra no es positivo" in x for x in w)


def test_total_cost_less_than_purchase_price_warns() -> None:
    w = build_coherence_warnings(
        purchase_price=10000,
        total_cost=8000,
        estimated_profit=500,
        roi=5,
    )
    assert any("coste total es menor" in x for x in w)


def test_roi_very_negative_warns() -> None:
    w = build_coherence_warnings(
        purchase_price=10000,
        total_cost=12000,
        estimated_profit=-5000,
        roi=-60,
    )
    assert any("-50" in x or "inviable" in x.lower() for x in w)


def test_positive_profit_negative_roi_warns() -> None:
    w = build_coherence_warnings(
        purchase_price=10000,
        total_cost=9000,
        estimated_profit=100,
        roi=-5,
    )
    assert any("Beneficio positivo con ROI negativo" in x for x in w)


def test_negative_profit_positive_roi_warns() -> None:
    w = build_coherence_warnings(
        purchase_price=10000,
        total_cost=12000,
        estimated_profit=-100,
        roi=5,
    )
    assert any("Beneficio negativo con ROI positivo" in x for x in w)


def test_market_implied_mismatch_warns() -> None:
    w = build_coherence_warnings(
        purchase_price=10000,
        total_cost=12000,
        estimated_profit=1500,
        roi=12.5,
        market_price=20000,
    )
    # implied = 20000 - 12000 = 8000; |8000 - 1500| = 6500 > max(500, 0.15*1500)
    assert any("no cuadra" in x for x in w)


def test_missing_data_returns_empty() -> None:
    assert build_coherence_warnings(
        purchase_price=None,
        total_cost=None,
        estimated_profit=None,
        roi=None,
    ) == []
