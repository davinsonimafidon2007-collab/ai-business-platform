"""TEST.OPP.LABELS.1 — labels ES en OpportunityRead (schema + helpers)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.api.v1.schemas.opportunity import OpportunityRead, OpportunityVehicleSummary
from app.services.recommendation_labels import recommendation_label_es, risk_label_es


def test_opportunity_read_accepts_label_fields() -> None:
    row = OpportunityRead(
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
        recommendation="BUY_NOW",
        risk_level="LOW",
        recommendation_label_es=recommendation_label_es("BUY_NOW"),
        risk_label_es=risk_label_es("LOW"),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    assert row.recommendation_label_es == "Comprar ya"
    assert row.risk_label_es == "Bajo"
    payload = row.model_dump()
    assert payload["recommendation_label_es"] == "Comprar ya"
    assert payload["risk_label_es"] == "Bajo"


def test_opportunity_label_helpers_negotiate_high() -> None:
    assert recommendation_label_es("NEGOTIATE") == "Negociar"
    assert risk_label_es("HIGH") == "Alto"


def test_opportunity_read_defaults_empty_labels() -> None:
    row = OpportunityRead(
        id="opp-2",
        recommendation="WATCH",
        risk_level="MEDIUM",
    )
    # defaults schema ""
    assert row.recommendation_label_es == ""
    assert row.risk_label_es == ""
    # quien mapea en la route debe rellenar; el schema permite vacío
    filled = row.model_copy(
        update={
            "recommendation_label_es": recommendation_label_es(row.recommendation),
            "risk_label_es": risk_label_es(row.risk_level),
        }
    )
    assert filled.recommendation_label_es == "Vigilar"
    assert filled.risk_label_es == "Medio"

