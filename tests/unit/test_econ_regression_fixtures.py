from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.profit_analyzer import ProfitAnalyzer

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "econ_regression_cases.json"


def _load() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def cases() -> list[dict]:
    data = _load()
    assert data.get("cases"), "econ_regression_cases.json sin cases"
    return data["cases"]


@pytest.fixture(scope="module")
def tol() -> tuple[float, float]:
    data = _load()
    return (
        float(data.get("tolerance_abs_eur", 0.02)),
        float(data.get("tolerance_abs_roi_pp", 0.05)),
    )


@pytest.mark.parametrize("case_id", [
    "spain_10k_14k",
    "spain_18k_24k",
    "es_alias_18k_24k",
    "portugal_10k_15k",
    "pt_alias_12k_16k",
])
def test_golden_case(case_id: str, cases: list[dict], tol: tuple[float, float]) -> None:
    case = next(c for c in cases if c["id"] == case_id)
    tol_eur, tol_roi = tol
    analyzer = ProfitAnalyzer()
    vehicle = SimpleNamespace(price=float(case["purchase_price"]))
    result = analyzer.analyze(
        vehicle,
        profile_name=case["profile_name"],
        estimated_sale_price=float(case["estimated_sale_price"]),
    )
    total = float(result.total_cost)
    profit = float(result.net_profit)
    roi = float(result.roi_percentage)

    assert abs(total - float(case["expected_total_cost"])) <= tol_eur, (
        f"{case_id} total_cost {total} != {case['expected_total_cost']}"
    )
    assert abs(profit - float(case["expected_net_profit"])) <= tol_eur, (
        f"{case_id} net_profit {profit} != {case['expected_net_profit']}"
    )
    assert abs(roi - float(case["expected_roi_percentage"])) <= tol_roi, (
        f"{case_id} roi {roi} != {case['expected_roi_percentage']}"
    )


def test_es_matches_spain_same_inputs(cases: list[dict], tol: tuple[float, float]) -> None:
    spain = next(c for c in cases if c["id"] == "spain_18k_24k")
    es = next(c for c in cases if c["id"] == "es_alias_18k_24k")
    tol_eur, tol_roi = tol
    assert abs(float(spain["expected_total_cost"]) - float(es["expected_total_cost"])) <= tol_eur
    assert abs(float(spain["expected_net_profit"]) - float(es["expected_net_profit"])) <= tol_eur
    assert abs(float(spain["expected_roi_percentage"]) - float(es["expected_roi_percentage"])) <= tol_roi


def test_portugal_differs_from_spain_on_same_purchase() -> None:
    """Misma compra/venta: PT y ES no deben producir el mismo total_cost (perfiles distintos)."""
    analyzer = ProfitAnalyzer()
    v = SimpleNamespace(price=10000.0)
    es = analyzer.analyze(v, profile_name="SPAIN", estimated_sale_price=15000.0)
    pt = analyzer.analyze(v, profile_name="PORTUGAL", estimated_sale_price=15000.0)
    assert es.total_cost != pt.total_cost
