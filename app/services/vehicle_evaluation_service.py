from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.models.vehicle import Vehicle
from app.models.vehicle_evaluation import VehicleEvaluation
from app.repositories.vehicle_evaluation_repository import VehicleEvaluationRepository
from app.services.evaluation_engine import EvaluationEngine, EvaluationResult


class VehicleEvaluationService:
    def __init__(self, repository: VehicleEvaluationRepository, evaluation_engine: EvaluationEngine | None = None) -> None:
        self.repository = repository
        self.evaluation_engine = evaluation_engine or EvaluationEngine()

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

    async def evaluate_vehicle(self, vehicle: Vehicle) -> VehicleEvaluation:
        """Evalúa un vehículo y crea/actualiza la evaluación.

        Args:
            vehicle: Vehículo a evaluar.

        Returns:
            VehicleEvaluation con los resultados de la evaluación.
        """
        # Calcular evaluación
        result: EvaluationResult = self.evaluation_engine.evaluate(vehicle)

        # Verificar si ya existe una evaluación para este vehículo
        existing_evaluation = await self.repository.get_by_vehicle_id(vehicle.id)

        if existing_evaluation:
            # Actualizar evaluación existente
            existing_evaluation.estimated_market_price_es = result.estimated_sale_price_es
            existing_evaluation.estimated_import_cost = result.total_cost
            existing_evaluation.estimated_registration_cost = result.registration_cost
            existing_evaluation.estimated_total_cost = result.total_cost
            existing_evaluation.estimated_profit = result.gross_profit
            existing_evaluation.profit_margin_percent = result.profit_margin_percent
            existing_evaluation.score = result.score
            existing_evaluation.classification = result.classification
            existing_evaluation.warnings = ", ".join(result.warnings) if result.warnings else None
            existing_evaluation.recommendation = result.recommendation
            existing_evaluation.updated_at = datetime.now(timezone.utc)

            return await self.repository.update(existing_evaluation)

        # Crear nueva evaluación
        evaluation = VehicleEvaluation(
            vehicle_id=vehicle.id,
            estimated_market_price_es=result.estimated_sale_price_es,
            estimated_import_cost=result.total_cost,
            estimated_registration_cost=result.registration_cost,
            estimated_total_cost=result.total_cost,
            estimated_profit=result.gross_profit,
            profit_margin_percent=result.profit_margin_percent,
            score=result.score,
            classification=result.classification,
            warnings=", ".join(result.warnings) if result.warnings else None,
            recommendation=result.recommendation,
        )

        return await self.repository.create(evaluation)
