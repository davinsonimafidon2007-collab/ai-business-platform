"""RefreshOpportunityJob — Recalcula el análisis de oportunidad de cada vehículo.

Para cada vehículo almacenado, ejecuta EvaluationEngine (el mismo motor que usa
POST /vehicles/{id}/evaluation) y guarda/actualiza el registro de Opportunity
correspondiente.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.jobs.base import Job, JobContext, JobResult

_CLASSIFICATION_TO_RISK = {
    "verde": "LOW",
    "amarillo": "MEDIUM",
    "rojo": "HIGH",
}


class RefreshOpportunityJob(Job):
    """Job periódico que recalcula el análisis de oportunidad de cada vehículo."""

    @property
    def name(self) -> str:
        return "refresh_opportunities"

    async def execute(self, context: JobContext) -> JobResult:
        logger = context.logger
        logger.info("Starting opportunity recalculation...")

        try:
            async with context.db_manager.get_session() as session:
                from app.models.opportunity import Opportunity
                from app.repositories.opportunity_repository import OpportunityRepository
                from app.repositories.vehicle_repository import VehicleRepository
                from app.services.evaluation_engine import EvaluationEngine

                opp_repo = OpportunityRepository(session)
                vehicle_repo = VehicleRepository(session)
                engine = EvaluationEngine()

                vehicles = await vehicle_repo.list_all(limit=1000)
                logger.info("Recalculating opportunities for %d vehicles", len(vehicles))

                updated_count = 0
                failed_count = 0

                for vehicle in vehicles:
                    try:
                        result = engine.evaluate(vehicle)

                        existing = await opp_repo.get_by_vehicle_id(vehicle.id)
                        risk = _CLASSIFICATION_TO_RISK.get(result.classification, "MEDIUM")

                        if existing:
                            opp = existing[0]
                            opp.opportunity_score = float(result.score)
                            opp.recommendation = result.recommendation
                            opp.roi = round(result.profit_margin_percent, 2)
                            opp.risk = risk
                            opp.profit = round(result.gross_profit, 2)
                            opp.analyzed_at = datetime.now(timezone.utc)
                        else:
                            opp = Opportunity(
                                vehicle_id=vehicle.id,
                                opportunity_score=float(result.score),
                                recommendation=result.recommendation,
                                roi=round(result.profit_margin_percent, 2),
                                risk=risk,
                                profit=round(result.gross_profit, 2),
                                analyzed_at=datetime.now(timezone.utc),
                            )

                        await opp_repo.save(opp)
                        updated_count += 1
                    except Exception:
                        logger.exception(
                            "Failed to recalculate opportunity for vehicle %s", vehicle.id
                        )
                        failed_count += 1

                logger.info(
                    "Opportunity recalculation complete. Updated: %d, Failed: %d",
                    updated_count,
                    failed_count,
                )

                return JobResult(
                    success=failed_count == 0,
                    message=f"Recalculated {updated_count} opportunities "
                    f"({failed_count} failed) across {len(vehicles)} vehicles",
                    data={
                        "vehicle_count": len(vehicles),
                        "updated_count": updated_count,
                        "failed_count": failed_count,
                    },
                )

        except Exception as exc:
            logger.exception("Opportunity recalculation failed: %s", exc)
            return JobResult(
                success=False,
                message=f"Opportunity recalculation failed: {exc}",
            )