"""Tests mínimos de las relationships SQLAlchemy añadidas (Task P1-002 / ARCH-002).

Verifica que los modelos críticos definen `relationship()` con `back_populates`
correctamente configurado mediante inspección del mapper.
"""

from __future__ import annotations

from sqlalchemy.orm import class_mapper

from app.models.api_key import ApiKey
from app.models.deal import Deal
from app.models.inspection import (
    InspectionObservation,
    InspectionPhoto,
    InspectionSession,
)
from app.models.opportunity import Opportunity
from app.models.refresh_token import RefreshToken
from app.models.search import Search
from app.models.search_history import SearchHistory
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.vehicle_evaluation import VehicleEvaluation


def _rel_keys(model) -> set[str]:
    return {r.key for r in class_mapper(model).relationships}


def test_user_relationships_configured() -> None:
    rels = _rel_keys(User)
    assert {
        "vehicles",
        "searches",
        "deals",
        "api_keys",
        "refresh_tokens",
        "search_histories",
    }.issubset(rels)


def test_vehicle_relationships_configured() -> None:
    rels = _rel_keys(Vehicle)
    assert {
        "user",
        "evaluations",
        "opportunities",
        "deals",
        "inspection_sessions",
    }.issubset(rels)


def test_deal_relationships_configured() -> None:
    rels = _rel_keys(Deal)
    assert {"user", "vehicle", "opportunity"}.issubset(rels)


def test_opportunity_relationships_configured() -> None:
    rels = _rel_keys(Opportunity)
    assert {"vehicle", "deals"}.issubset(rels)


def test_search_relationships_configured() -> None:
    rels = _rel_keys(Search)
    assert "user" in rels


def test_search_history_relationships_configured() -> None:
    rels = _rel_keys(SearchHistory)
    assert "user" in rels


def test_vehicle_evaluation_relationships_configured() -> None:
    rels = _rel_keys(VehicleEvaluation)
    assert "vehicle" in rels


def test_api_key_relationships_configured() -> None:
    rels = _rel_keys(ApiKey)
    assert "user" in rels


def test_refresh_token_relationships_configured() -> None:
    rels = _rel_keys(RefreshToken)
    assert "user" in rels


def test_inspection_relationships_configured() -> None:
    session_rels = _rel_keys(InspectionSession)
    assert {"vehicle", "user", "observations", "photos"}.issubset(session_rels)

    observation_rels = _rel_keys(InspectionObservation)
    assert {"session", "photos"}.issubset(observation_rels)

    photo_rels = _rel_keys(InspectionPhoto)
    assert {"observation", "session"}.issubset(photo_rels)


def test_back_populates_are_bidirectional() -> None:
    """Verifica que los pares back_populates se referencian mutuamente."""
    def backpop(model, key: str) -> str | None:
        rel = next(r for r in class_mapper(model).relationships if r.key == key)
        return rel.back_populates

    # User <-> Vehicle
    assert backpop(User, "vehicles") == "user"
    assert backpop(Vehicle, "user") == "vehicles"
    # User <-> Search
    assert backpop(User, "searches") == "user"
    assert backpop(Search, "user") == "searches"
    # User <-> Deal
    assert backpop(User, "deals") == "user"
    assert backpop(Deal, "user") == "deals"
    # User <-> ApiKey
    assert backpop(User, "api_keys") == "user"
    assert backpop(ApiKey, "user") == "api_keys"
    # User <-> RefreshToken
    assert backpop(User, "refresh_tokens") == "user"
    assert backpop(RefreshToken, "user") == "refresh_tokens"
    # User <-> SearchHistory
    assert backpop(User, "search_histories") == "user"
    assert backpop(SearchHistory, "user") == "search_histories"
    # User <-> InspectionSession
    assert backpop(User, "inspection_sessions") == "user"
    assert backpop(InspectionSession, "user") == "inspection_sessions"
    # Vehicle <-> Evaluation
    assert backpop(Vehicle, "evaluations") == "vehicle"
    assert backpop(VehicleEvaluation, "vehicle") == "evaluations"
    # Vehicle <-> Opportunity
    assert backpop(Vehicle, "opportunities") == "vehicle"
    assert backpop(Opportunity, "vehicle") == "opportunities"
    # Vehicle <-> Deal
    assert backpop(Vehicle, "deals") == "vehicle"
    assert backpop(Deal, "vehicle") == "deals"
    # Vehicle <-> InspectionSession
    assert backpop(Vehicle, "inspection_sessions") == "vehicle"
    assert backpop(InspectionSession, "vehicle") == "inspection_sessions"
    # Deal <-> Opportunity
    assert backpop(Deal, "opportunity") == "deals"
    assert backpop(Opportunity, "deals") == "opportunity"
    # Session <-> Observation
    assert backpop(InspectionSession, "observations") == "session"
    assert backpop(InspectionObservation, "session") == "observations"
    # Session <-> Photo
    assert backpop(InspectionSession, "photos") == "session"
    assert backpop(InspectionPhoto, "session") == "photos"
    # Observation <-> Photo
    assert backpop(InspectionObservation, "photos") == "observation"
    assert backpop(InspectionPhoto, "observation") == "photos"
