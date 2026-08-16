"""Unit tests for PROFIT.1 cost_breakdown_labels."""

from __future__ import annotations

from types import SimpleNamespace

from app.services.cost_breakdown_labels import build_cost_lines


def test_build_cost_lines_labels_es() -> None:
    cb = SimpleNamespace(
        purchase_price=10000.0,
        transport_cost=800.0,
        registration_cost=200.0,
        taxes=2100.0,
        inspection_cost=50.0,
        repair_estimate=0.0,
        commission_cost=0.0,
        miscellaneous_cost=0.0,
        _COMPONENTS=(
            ("purchase_price", "Precio de compra", "fixed"),
            ("transport_cost", "Transporte", "fixed"),
            ("registration_cost", "Matriculación", "fixed"),
            ("taxes", "Impuestos (IVA / transferencias)", "variable"),
            ("inspection_cost", "ITV / inspección", "fixed"),
            ("repair_estimate", "Reparaciones estimadas", "variable"),
        ),
    )

    lines = build_cost_lines(cb)

    keys = [x["key"] for x in lines]
    assert "purchase_price" in keys
    assert any(x["label_es"] == "Precio de compra" for x in lines)
    assert any(x["label_es"] == "Transporte" for x in lines)
    assert all("amount" in x for x in lines)
    assert all(isinstance(x["amount"], float) for x in lines)
    # 0.0 is a valid amount (only None is skipped)
    assert any(x["key"] == "repair_estimate" and x["amount"] == 0.0 for x in lines)


def test_build_cost_lines_none_returns_empty() -> None:
    assert build_cost_lines(None) == []


def test_build_cost_lines_dict_like() -> None:
    cb = {
        "purchase_price": 5000.0,
        "transport_cost": 400.0,
        "miscellaneous_cost": None,
    }
    lines = build_cost_lines(cb)
    assert [x["key"] for x in lines] == ["purchase_price", "transport_cost"]
    assert all(x["amount"] > 0 for x in lines)


def test_build_cost_lines_order_respects_components() -> None:
    cb = SimpleNamespace(
        purchase_price=100.0,
        transport_cost=100.0,
        _COMPONENTS=(
            ("transport_cost", "Transporte", "fixed"),
            ("purchase_price", "Precio de compra", "fixed"),
        ),
    )
    lines = build_cost_lines(cb)
    assert [x["key"] for x in lines] == ["transport_cost", "purchase_price"]
