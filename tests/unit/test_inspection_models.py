"""Tests for inspection SQLAlchemy models."""

from app.models.inspection import InspectionObservation, InspectionPhoto, InspectionSession


def test_session_serializes_summary_and_timestamps() -> None:
    session = InspectionSession(vehicle_id="00000000-0000-0000-0000-000000000001", summary={"risk_level": "LOW"})
    data = session.to_dict()
    assert data["summary"] == {"risk_level": "LOW"}
    assert data["created_at"] is not None


def test_session_returns_none_for_invalid_stored_summary() -> None:
    session = InspectionSession(vehicle_id="00000000-0000-0000-0000-000000000001")
    session._summary_json = "not-json"
    assert session.summary is None


def test_observation_and_photo_serialize_fields() -> None:
    observation = InspectionObservation(session_id="session", category_id="exterior", item_id="pintura", status="BAD", estimated_repair_cost=100, severity="MEDIUM")
    photo = InspectionPhoto(session_id="session", observation_id=observation.id, file_path="/photos/car.jpg")
    assert observation.to_dict()["estimated_repair_cost"] == 100
    assert photo.to_dict()["ai_analysis_status"] == "PENDING"
