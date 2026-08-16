"""Unit tests for Spanish recommendation/risk labels (REC.1)."""

from __future__ import annotations

import pytest

from app.services.recommendation_labels import recommendation_label_es, risk_label_es


@pytest.mark.parametrize(
    "code,expected",
    [
        ("BUY_NOW", "Comprar ya"),
        ("buy_now", "Comprar ya"),
        ("WATCH", "Vigilar"),
        ("watch", "Vigilar"),
        ("NEGOTIATE", "Negociar"),
        ("REJECT", "Descartar"),
        ("BUY", "Comprar"),
        ("CONSIDER", "Considerar"),
        ("WALK_AWAY", "Abandonar"),
        ("PASS", "Pasar"),
        ("STRONG_BUY", "Strong Buy"),
    ],
)
def test_recommendation_labels(code: str, expected: str) -> None:
    assert recommendation_label_es(code) == expected


def test_recommendation_labels_none() -> None:
    assert recommendation_label_es(None) == ""
    assert recommendation_label_es("") == ""


@pytest.mark.parametrize(
    "code,expected",
    [
        ("LOW", "Bajo"),
        ("MEDIUM", "Medio"),
        ("HIGH", "Alto"),
        ("CRITICAL", "Crítico"),
        ("NONE", "Ninguno"),
        ("UNKNOWN", "Desconocido"),
    ],
)
def test_risk_labels(code: str, expected: str) -> None:
    assert risk_label_es(code) == expected


def test_risk_labels_none() -> None:
    assert risk_label_es(None) == ""
    assert risk_label_es("") == ""
