from app.models.vehicle import Vehicle


def test_vehicle_model_has_expected_columns() -> None:
    columns = {column.name for column in Vehicle.__table__.columns}

    expected = {
        "id", "source", "external_id", "url", "brand", "model", "version",
        "year", "mileage", "fuel_type", "transmission", "power_hp",
        "displacement_cc", "doors", "color", "emissions", "location",
        "seller_type", "first_registration", "price", "currency", "vin",
        "description", "images", "equipment", "created_at", "updated_at",
    }
    assert expected.issubset(columns)


def test_vehicle_model_defaults() -> None:
    vehicle = Vehicle(source="mobile.de", external_id="ext-123", brand="BMW", model="X5")

    assert vehicle.id is not None
    assert vehicle.source == "mobile.de"
    assert vehicle.external_id == "ext-123"
    assert vehicle.brand == "BMW"
    assert vehicle.model == "X5"
    assert vehicle.created_at is not None
    assert vehicle.updated_at is not None