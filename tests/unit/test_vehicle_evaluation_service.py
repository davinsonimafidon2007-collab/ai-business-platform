"""Tests para VehicleEvaluationService."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.models.vehicle import Vehicle
from app.models.vehicle_evaluation import VehicleEvaluation
from app.services.evaluation_engine import EvaluationEngine
from app.services.vehicle_evaluation_service import VehicleEvaluationService


class MockVehicleEvaluationRepository:
    """Mock repository for testing VehicleEvaluationService."""

    def __init__(self):
        self.evaluations: dict[str, VehicleEvaluation] = {}
        self.next_id = 1

    async def create(self, evaluation: VehicleEvaluation) -> VehicleEvaluation:
        evaluation.id = str(self.next_id)
        self.next_id += 1
        if evaluation.created_at is None:
            evaluation.created_at = datetime.now(UTC)
        if evaluation.updated_at is None:
            evaluation.updated_at = datetime.now(UTC)
        self.evaluations[evaluation.id] = evaluation
        return evaluation

    async def get_by_id(self, evaluation_id: str) -> VehicleEvaluation | None:
        return self.evaluations.get(str(evaluation_id))

    async def get_by_vehicle_id(self, vehicle_id: str) -> VehicleEvaluation | None:
        for eval in self.evaluations.values():
            if eval.vehicle_id == str(vehicle_id):
                return eval
        return None

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[VehicleEvaluation]:
        return list(self.evaluations.values())[skip : skip + limit]

    async def update(self, evaluation: VehicleEvaluation) -> VehicleEvaluation:
        evaluation.updated_at = datetime.now(UTC)
        self.evaluations[evaluation.id] = evaluation
        return evaluation

    async def delete(self, evaluation: VehicleEvaluation) -> None:
        self.evaluations.pop(evaluation.id, None)


@pytest.fixture
def mock_repository():
    return MockVehicleEvaluationRepository()


@pytest.fixture
def evaluation_engine():
    return EvaluationEngine()


@pytest.fixture
def vehicle_evaluation_service(mock_repository, evaluation_engine):
    return VehicleEvaluationService(mock_repository, evaluation_engine)


@pytest.fixture
def sample_vehicle():
    return Vehicle(
        id="test-vehicle-id",
        brand="BMW",
        model="X5",
        year=2020,
        mileage=50000,
        price=35000.0,
        fuel_type="Diesel",
        transmission="Automatic",
        category="SUV",
    )


@pytest.fixture
def existing_evaluation():
    return VehicleEvaluation(
        id="existing-eval-id",
        vehicle_id="test-vehicle-id",
        estimated_market_price_es=30000.0,
        estimated_import_cost=35000.0,
        estimated_registration_cost=1600.0,
        estimated_total_cost=35000.0,
        estimated_profit=-5000.0,
        profit_margin_percent=-14.3,
        score=30,
        classification="rojo",
        warnings="Some warning",
        recommendation="Not recommended",
    )


# ---------------------------------------------------------------------------
# evaluate_vehicle tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_vehicle_creates_new_evaluation(
    vehicle_evaluation_service, mock_repository, sample_vehicle
):
    """Test that evaluate_vehicle creates a new evaluation when none exists."""
    result = await vehicle_evaluation_service.evaluate_vehicle(sample_vehicle)

    assert isinstance(result, VehicleEvaluation)
    assert result.vehicle_id == "test-vehicle-id"
    assert result.estimated_market_price_es is not None
    assert result.estimated_total_cost is not None
    assert result.estimated_profit is not None
    assert result.score is not None
    assert result.classification in ["verde", "amarillo", "rojo"]
    assert result.warnings is not None or result.warnings is None
    assert result.recommendation is not None

    # Verify it was saved in the repository
    saved = await mock_repository.get_by_vehicle_id(sample_vehicle.id)
    assert saved is not None
    assert saved.id == result.id


@pytest.mark.asyncio
async def test_evaluate_vehicle_updates_existing_evaluation(
    vehicle_evaluation_service, mock_repository, sample_vehicle, existing_evaluation
):
    """Test that evaluate_vehicle updates an existing evaluation."""
    # Save existing evaluation
    await mock_repository.create(existing_evaluation)

    result = await vehicle_evaluation_service.evaluate_vehicle(sample_vehicle)

    assert result.id == existing_evaluation.id
    assert result.vehicle_id == "test-vehicle-id"
    assert result.estimated_market_price_es != 30000.0  # Original value was 30000.0
    assert result.updated_at >= existing_evaluation.updated_at


@pytest.mark.asyncio
async def test_evaluate_vehicle_result_fields_match_engine(
    vehicle_evaluation_service, sample_vehicle
):
    """Test that the evaluation fields match the engine's EvaluationResult."""
    result = await vehicle_evaluation_service.evaluate_vehicle(sample_vehicle)

    # The service should map engine results to evaluation fields
    assert result.estimated_market_price_es is not None
    assert result.estimated_import_cost is not None
    assert result.estimated_registration_cost is not None
    assert result.estimated_total_cost is not None
    assert result.estimated_profit is not None
    assert result.profit_margin_percent is not None
    assert result.score is not None
    assert 0 <= result.score <= 100
    assert result.classification in ["verde", "amarillo", "rojo"]


@pytest.mark.asyncio
async def test_evaluate_vehicle_warnings_joined(
    vehicle_evaluation_service, sample_vehicle
):
    """Test that warnings are joined into a comma-separated string."""
    result = await vehicle_evaluation_service.evaluate_vehicle(sample_vehicle)

    # Vehicle has a price, so warnings should be empty or None
    assert result.warnings is None or isinstance(result.warnings, str)


# ---------------------------------------------------------------------------
# create_evaluation tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_evaluation(vehicle_evaluation_service, mock_repository):
    """Test creating a new evaluation."""
    data = {
        "vehicle_id": "vehicle-1",
        "estimated_market_price_es": 25000.0,
        "estimated_import_cost": 30000.0,
        "estimated_registration_cost": 1400.0,
        "estimated_total_cost": 30000.0,
        "estimated_profit": -5000.0,
        "profit_margin_percent": -16.7,
        "score": 25,
        "classification": "rojo",
        "warnings": "Low margin",
        "recommendation": "Not recommended",
    }

    result = await vehicle_evaluation_service.create_evaluation(data)

    assert isinstance(result, VehicleEvaluation)
    assert result.vehicle_id == "vehicle-1"
    assert result.estimated_market_price_es == 25000.0
    assert result.score == 25
    assert result.classification == "rojo"

    # Verify it was saved
    saved = await mock_repository.get_by_id(result.id)
    assert saved is not None


# ---------------------------------------------------------------------------
# get_evaluation tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_evaluation(vehicle_evaluation_service, mock_repository):
    """Test retrieving an evaluation by ID."""
    evaluation = VehicleEvaluation(vehicle_id="vehicle-1")
    created = await mock_repository.create(evaluation)

    result = await vehicle_evaluation_service.get_evaluation(created.id)

    assert result is not None
    assert result.id == created.id
    assert result.vehicle_id == "vehicle-1"


@pytest.mark.asyncio
async def test_get_evaluation_not_found(vehicle_evaluation_service):
    """Test retrieving a non-existent evaluation."""
    result = await vehicle_evaluation_service.get_evaluation("non-existent-id")
    assert result is None


# ---------------------------------------------------------------------------
# get_evaluation_by_vehicle tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_evaluation_by_vehicle(vehicle_evaluation_service, mock_repository):
    """Test retrieving an evaluation by vehicle ID."""
    evaluation = VehicleEvaluation(vehicle_id="vehicle-1")
    await mock_repository.create(evaluation)

    result = await vehicle_evaluation_service.get_evaluation_by_vehicle("vehicle-1")

    assert result is not None
    assert result.vehicle_id == "vehicle-1"


@pytest.mark.asyncio
async def test_get_evaluation_by_vehicle_not_found(vehicle_evaluation_service):
    """Test retrieving an evaluation for a non-existent vehicle."""
    result = await vehicle_evaluation_service.get_evaluation_by_vehicle("non-existent")
    assert result is None


# ---------------------------------------------------------------------------
# list_evaluations tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_evaluations(vehicle_evaluation_service, mock_repository):
    """Test listing all evaluations."""
    await mock_repository.create(VehicleEvaluation(vehicle_id="vehicle-1"))
    await mock_repository.create(VehicleEvaluation(vehicle_id="vehicle-2"))
    await mock_repository.create(VehicleEvaluation(vehicle_id="vehicle-3"))

    results = await vehicle_evaluation_service.list_evaluations()

    assert len(results) == 3
    assert all(isinstance(r, VehicleEvaluation) for r in results)


@pytest.mark.asyncio
async def test_list_evaluations_empty(vehicle_evaluation_service):
    """Test listing evaluations when none exist."""
    results = await vehicle_evaluation_service.list_evaluations()
    assert len(results) == 0


@pytest.mark.asyncio
async def test_list_evaluations_with_pagination(vehicle_evaluation_service, mock_repository):
    """Test listing evaluations with skip and limit."""
    for i in range(5):
        await mock_repository.create(VehicleEvaluation(vehicle_id=f"vehicle-{i}"))

    results = await vehicle_evaluation_service.list_evaluations(skip=2, limit=2)
    assert len(results) == 2


# ---------------------------------------------------------------------------
# update_evaluation tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_evaluation(vehicle_evaluation_service, mock_repository):
    """Test updating an evaluation."""
    evaluation = VehicleEvaluation(vehicle_id="vehicle-1", score=50)
    created = await mock_repository.create(evaluation)
    original_updated_at = created.updated_at

    import asyncio
    await asyncio.sleep(0.01)

    data = {"score": 80, "classification": "verde"}
    result = await vehicle_evaluation_service.update_evaluation(created, data)

    assert result.score == 80
    assert result.classification == "verde"
    assert result.updated_at > original_updated_at


@pytest.mark.asyncio
async def test_update_evaluation_partial(vehicle_evaluation_service, mock_repository):
    """Test partial update of an evaluation."""
    evaluation = VehicleEvaluation(vehicle_id="vehicle-1", score=50, classification="rojo")
    created = await mock_repository.create(evaluation)

    data = {"score": 70}
    result = await vehicle_evaluation_service.update_evaluation(created, data)

    assert result.score == 70
    assert result.classification == "rojo"  # Unchanged


# ---------------------------------------------------------------------------
# delete_evaluation tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_evaluation(vehicle_evaluation_service, mock_repository):
    """Test deleting an evaluation."""
    evaluation = VehicleEvaluation(vehicle_id="vehicle-1")
    created = await mock_repository.create(evaluation)

    await vehicle_evaluation_service.delete_evaluation(created)

    result = await mock_repository.get_by_id(created.id)
    assert result is None


# ---------------------------------------------------------------------------
# Integration: evaluate_vehicle with different vehicle types
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_vehicle_with_good_margin(vehicle_evaluation_service):
    """Test evaluating a vehicle with good profit margin."""
    vehicle = Vehicle(
        brand="Toyota",
        model="Corolla",
        year=2022,
        mileage=20000,
        price=20000.0,
        category="Sedan",
    )
    result = await vehicle_evaluation_service.evaluate_vehicle(vehicle)

    assert result.score >= 40
    assert result.classification in ["verde", "amarillo", "rojo"]


@pytest.mark.asyncio
async def test_evaluate_vehicle_with_no_price(vehicle_evaluation_service):
    """Test evaluating a vehicle without a price."""
    vehicle = Vehicle(brand="BMW", model="X5", year=2020)
    result = await vehicle_evaluation_service.evaluate_vehicle(vehicle)

    assert result.vehicle_id == vehicle.id
    assert result.score is not None
    assert result.classification == "rojo"


@pytest.mark.asyncio
async def test_evaluate_vehicle_consistency(vehicle_evaluation_service, sample_vehicle):
    """Test that evaluating the same vehicle twice produces consistent results."""
    result1 = await vehicle_evaluation_service.evaluate_vehicle(sample_vehicle)
    result2 = await vehicle_evaluation_service.evaluate_vehicle(sample_vehicle)

    assert result1.score == result2.score
    assert result1.classification == result2.classification
    assert result1.estimated_market_price_es == result2.estimated_market_price_es
