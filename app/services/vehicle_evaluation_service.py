from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.models.vehicle_evaluation import VehicleEvaluation
from app.repositories.vehicle_evaluation_repository import VehicleEvaluationRepository


class VehicleEvaluationService:
    def __init__(self, repository: VehicleEvaluationRepository) -> None:
        self.repository = repository

    async def create_evaluation(self, data: dict) -> VehicleEvaluation:
        evaluation = VehicleEvaluation(**data)
        return await self.repository.create(evaluation)

    async def get_evaluation(self, evaluation_id: str | UUID) -> VehicleEvaluation | None:
        return await self.repository.get_by_id(evaluation_id)

    async def get_evaluation_by_vehicle(self, vehicle_id: str | UUID) -> VehicleEvaluation | None:
        return await self.repository.get_by_vehicle_id(vehicle_id)

    async def list_evaluations(self, skip: int = 0, limit: int = 100) -> list[VehicleEvaluation]:
        return await self.repository.list_all(skip=skip, limit=limit)

    async def update_evaluation(self, evaluation: VehicleEvaluation, data: dict) -> VehicleEvaluation:
        for key, value in data.items():
            if value is not None:
                setattr(evaluation, key, value)
        evaluation.updated_at = datetime.now(timezone.utc)
        return await self.repository.update(evaluation)

    async def delete_evaluation(self, evaluation: VehicleEvaluation) -> None:
        await self.repository.delete(evaluation)