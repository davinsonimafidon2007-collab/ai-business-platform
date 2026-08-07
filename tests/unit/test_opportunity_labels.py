"""TEST.OPP.LABELS.1 — labels ES en OpportunityRead (schema + endpoint).

Cubre los campos existentes `recommendation_label_es` / `risk_label_es` y sus
aliases legibles `recommendation_label` / `risk_label`. No toca search.py.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.api.v1.schemas.opportunity import (
    OpportunityRead,
    OpportunityVehicleSummary,
)
from app.services.recommendation_labels import (
    recommendation_label_es,
    risk_label_es,
)


def _opp(recommendation: str | None = None, risk: str | None = None) -> OpportunityRead:
    return OpportunityRead(
        id="opp-1",
        vehicle=OpportunityVehicleSummary(
            id="v-1",
            brand="BMW",
            model="320d",
            year=2019,
            mileage=80000,
            price=17000.0,
            source="autoscout24",
            external_id="x1",
            url="https://example.com/x1",
        ),
        score=88.0,
        estimated_profit=3200.0,
        roi_percentage=15.5,
        recommendation=recommendation,
        risk_level=risk,
        recommendation_label_es=recommendation_label_es(recommendation),
        risk_label_es=risk_label_es(risk),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def test_known_labels() -> None:
    assert recommendation_label_es("BUY_NOW") == "Comprar ya"
    assert recommendation_label_es("NEGOTIATE") == "Negociar"
    assert risk_label_es("LOW") == "Bajo"
    assert risk_label_es("HIGH") == "Alto"


def test_case_insensitive() -> None:
    assert recommendation_label_es("negotiate") == "Negociar"
    assert risk_label_es("high") == "Alto"


def test_unknown_label_passthrough() -> None:
    assert recommendation_label_es("MYSTERY") == "Mystery"
    assert risk_label_es("WEIRD") == "Weird"


def test_none_and_empty() -> None:
    assert recommendation_label_es(None) == ""
    assert recommendation_label_es("") == ""
    assert risk_label_es(None) == ""
    assert risk_label_es("") == ""


def test_opportunity_read_serializes_labels() -> None:
    row = _opp(recommendation="BUY_NOW", risk="LOW")
    payload = row.model_dump()
    assert payload["recommendation_label_es"] == "Comprar ya"
    assert payload["risk_label_es"] == "Bajo"
    # aliases legibles (computed_field) expuestos en la respuesta
    assert payload["recommendation_label"] == "Comprar ya"
    assert payload["risk_label"] == "Bajo"


def test_opportunity_read_defaults_empty_labels() -> None:
    row = OpportunityRead(id="opp-2", recommendation="WATCH", risk_level="MEDIUM")
    assert row.recommendation_label_es == ""
    assert row.risk_label_es == ""
    filled = row.model_copy(
        update={
            "recommendation_label_es": recommendation_label_es(row.recommendation),
            "risk_label_es": risk_label_es(row.risk_level),
        }
    )
    assert filled.recommendation_label_es == "Vigilar"
    assert filled.risk_label_es == "Medio"
    assert filled.model_dump()["recommendation_label"] == "Vigilar"
    assert filled.model_dump()["risk_label"] == "Medio"
