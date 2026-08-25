import pytest
from pydantic import ValidationError

from app.schemas.vehicle import VehicleCreate, VehicleRead, VehicleUpdate


def test_vehicle_create_accepts_valid_data() -> None:
    vehicle = VehicleCreate(
        source="mobile.de",
        external_id="ext-001",
        brand="BMW",
        model="X5",
        year=2020,
        price=35000.0,
    )

    assert vehicle.source == "mobile.de"
    assert vehicle.external_id == "ext-001"
    assert vehicle.brand == "BMW"
    assert vehicle.model == "X5"
    assert vehicle.year == 2020
    assert vehicle.price == 35000.0


def test_vehicle_create_rejects_missing_required_fields() -> None:
    with pytest.raises(ValidationError):
        VehicleCreate()


def test_vehicle_read_allows_model_attributes() -> None:
    vehicle = VehicleRead(
        id="123e4567-e89b-12d3-a456-426614174000",
        user_id="00000000-0000-4000-8000-000000000001",
        source="autoscout24",
        external_id="ext-002",
        brand="Audi",
        model="A4",
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
    )

    assert vehicle.id == "123e4567-e89b-12d3-a456-426614174000"
    assert (
        vehicle.user_id == "00000000-0000-4000-8000-000000000001"
    )
    assert vehicle.source == "autoscout24"
    assert vehicle.brand == "Audi"
    assert vehicle.model == "A4"


def test_vehicle_update_allows_partial_updates() -> None:
    vehicle = VehicleUpdate(price=25000.0, year=2019)

    assert vehicle.price == 25000.0
    assert vehicle.year == 2019
