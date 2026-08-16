from app.models.vehicle_evaluation import VehicleEvaluation


def test_vehicle_evaluation_model_has_expected_columns() -> None:
    columns = {column.name for column in VehicleEvaluation.__table__.columns}

    expected = {
        "id", "vehicle_id", "estimated_market_price_es", "estimated_import_cost",
        "estimated_registration_cost", "estimated_total_cost", "estimated_profit",
        "profit_margin_percent", "score", "classification", "warnings",
        "recommendation", "created_at", "updated_at",
    }
    assert expected.issubset(columns)


def test_vehicle_evaluation_model_defaults() -> None:
    evaluation = VehicleEvaluation(vehicle_id="some-vehicle-id")

    assert evaluation.id is not None
    assert evaluation.vehicle_id == "some-vehicle-id"
    assert evaluation.created_at is not None
    assert evaluation.updated_at is not None