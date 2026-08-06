"""MKT.2 — MarketEstimationSchema expone explanation."""

from __future__ import annotations

from types import SimpleNamespace

from app.api.v1.routes.search import _build_search_result_item
from app.api.v1.schemas.common import MarketEstimationSchema


def test_market_estimation_schema_accepts_explanation() -> None:
    schema = MarketEstimationSchema(
        market_price=9900.0,
        confidence=72.0,
        comparable_count=8,
        notes=["pricing=underpriced"],
        explanation="El anuncio está por debajo del mercado estimado.",
    )
    assert schema.explanation.startswith("El anuncio")
    dumped = schema.model_dump()
    assert "explanation" in dumped
    assert dumped["explanation"]


def test_market_estimation_schema_default_explanation_empty() -> None:
    schema = MarketEstimationSchema(market_price=1000.0, confidence=50.0)
    assert schema.explanation == ""


def test_build_search_result_item_maps_explanation() -> None:
    vehicle = SimpleNamespace(
        external_id="x1",
        source="autoscout24",
        brand="BMW",
        model="320d",
        year=2019,
        mileage=120000,
        price=8500.0,
        fuel_type="Diesel",
        transmission="Manual",
        location="Berlin",
        url="https://example.com/1",
        images=[],
        description=None,
        title="BMW 320d",
        power_hp=None,
        color=None,
        first_registration=None,
        sellers=None,
        seller_type=None,
    )
    me = SimpleNamespace(
        market_price=9900.0,
        confidence=70.0,
        supply_level=50.0,
        demand_level=50.0,
        market_trend="stable",
        comparable_count=10,
        notes=["pricing=underpriced", "median=9800"],
        explanation="El anuncio (8500 EUR) está por debajo del mercado estimado (9900 EUR).",
    )
    result = SimpleNamespace(
        vehicle=vehicle,
        vehicle_score=None,
        market_estimation=me,
        profit_analysis=None,
        opportunity=None,
        negotiation=None,
    )
    item = _build_search_result_item(result)
    assert item.market_estimation is not None
    assert "por debajo" in item.market_estimation.explanation.lower()
    assert item.market_estimation.notes[0] == "pricing=underpriced"


def test_schema_provider_sources() -> None:
    s = MarketEstimationSchema(
        market_price=1.0,
        confidence=50.0,
        provider_sources=["mobile_de", "es_market_fixture"],
    )
    assert "es_market_fixture" in s.provider_sources


def test_mapper_parses_providers_note() -> None:
    me = SimpleNamespace(
        market_price=9000.0,
        confidence=60.0,
        supply_level=50.0,
        demand_level=50.0,
        market_trend="stable",
        comparable_count=3,
        notes=["mean=9000", "providers=mobile_de,es_market_fixture", "pricing=fair"],
        explanation="texto",
    )
    vehicle = SimpleNamespace(
        external_id="x1",
        source="autoscout24",
        brand="BMW",
        model="320d",
        year=2019,
        mileage=120000,
        price=8500.0,
        fuel_type="Diesel",
        transmission="Manual",
        location="Berlin",
        url="https://example.com/1",
        images=[],
        description=None,
        title="BMW 320d",
        power_hp=None,
        color=None,
        first_registration=None,
        sellers=None,
        seller_type=None,
    )
    result = SimpleNamespace(
        vehicle=vehicle,
        vehicle_score=None,
        market_estimation=me,
        profit_analysis=None,
        opportunity=None,
        negotiation=None,
    )
    item = _build_search_result_item(result)
    assert item.market_estimation is not None
    assert item.market_estimation.provider_sources == ["mobile_de", "es_market_fixture"]
