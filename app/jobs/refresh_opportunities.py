"""RefreshOpportunityJob — Recalcula el análisis de oportunidad de cada vehículo.

Para cada vehículo almacenado, ejecuta EvaluationEngine (el mismo motor que usa
POST /vehicles/{id}/evaluation) y guarda/actualiza el registro de Opportunity
correspondiente.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.config import settings
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
                from app.repositories.user_repository import UserRepository
                from app.repositories.vehicle_repository import VehicleRepository
                from app.services.evaluation_engine import EvaluationEngine
                from app.services.opportunity_alert_service import OpportunityAlertService
                from app.services.telegram_alert_service import TelegramAlertService

                opp_repo = OpportunityRepository(session)
                vehicle_repo = VehicleRepository(session)
                user_repo = UserRepository(session)
                alert_service = OpportunityAlertService()
                telegram_service = TelegramAlertService()
                engine = EvaluationEngine(
                    import_cost_profile=getattr(
                        settings, "default_import_cost_profile", None
                    )
                )

                page_size = 200
                skip = 0
                updated_count = 0
                failed_count = 0
                total_seen = 0

                while True:
                    vehicles = await vehicle_repo.list_all(skip=skip, limit=page_size)
                    if not vehicles:
                        break

                    total_seen += len(vehicles)
                    logger.info(
                        "Processing vehicles batch skip=%d count=%d",
                        skip,
                        len(vehicles),
                    )

                    for vehicle in vehicles:
                        try:
                            result = engine.evaluate(vehicle)

                            existing = await opp_repo.get_by_vehicle_id(vehicle.id)
                            risk = _CLASSIFICATION_TO_RISK.get(
                                result.classification, "MEDIUM"
                            )

                            if existing:
                                opp = existing[0]
                                opp.opportunity_score = float(result.score)
                                opp.recommendation = result.recommendation
                                opp.roi = round(result.profit_margin_percent, 2)
                                opp.risk = risk
                                opp.profit = round(result.gross_profit, 2)
                                opp.analyzed_at = datetime.now(UTC)
                            else:
                                opp = Opportunity(
                                    vehicle_id=vehicle.id,
                                    opportunity_score=float(result.score),
                                    recommendation=result.recommendation,
                                    roi=round(result.profit_margin_percent, 2),
                                    risk=risk,
                                    profit=round(result.gross_profit, 2),
                                    analyzed_at=datetime.now(UTC),
                                )

                            await opp_repo.save(opp)

                            # Buscar owner una sola vez (corrección N+1, agregación canales)
                            try:
                                owner = await user_repo.get_by_id(vehicle.user_id)
                            except Exception:
                                logger.warning("owner lookup failed vehicle %s", vehicle.id, exc_info=True)
                                owner = None

                            # Alertas email (Task C.2)
                            try:
                                if owner is not None:
                                    await alert_service.maybe_notify(
                                        user_email=owner.email,
                                        opportunity=opp,
                                        vehicle=vehicle,
                                    )
                            except Exception:
                                logger.warning(
                                    "opportunity_alert failed for vehicle %s",
                                    vehicle.id,
                                    exc_info=True,
                                )

                            # Push notification (TASK-010, FASE 5): FCM al dueño
                            try:
                                if owner is not None:
                                    from app.services.push_service import (
                                        notify_opportunity_created,
                                    )

                                    await notify_opportunity_created(
                                        user_id=str(owner.id),
                                        opportunity_data={
                                            "brand": getattr(vehicle, "brand", ""),
                                            "model": getattr(vehicle, "model", ""),
                                            "roi": getattr(opp, "roi", None),
                                            "id": str(getattr(opp, "id", "")),
                                        },
                                    )
                            except Exception:
                                logger.warning(
                                    "push_notification failed for vehicle %s",
                                    vehicle.id,
                                    exc_info=True,
                                )

                            # Alertas Telegram (Task C.3): notify al canal configurado
                            try:
                                await telegram_service.send_opportunity_alert(
                                    opportunity=opp,
                                    vehicle=vehicle,
                                    evaluation=result,
                                )
                            except Exception:
                                logger.warning(
                                    "telegram_alert failed for vehicle %s",
                                    vehicle.id,
                                    exc_info=True,
                                )

                            updated_count += 1
                        except Exception:
                            logger.exception(
                                "Failed to recalculate opportunity for vehicle %s",
                                vehicle.id,
                            )
                            failed_count += 1

                    if len(vehicles) < page_size:
                        break
                    skip += page_size

                logger.info(
                    "Opportunity recalculation complete. "
                    "Updated: %d, Failed: %d, Total seen: %d",
                    updated_count,
                    failed_count,
                    total_seen,
                )

                return JobResult(
                    success=failed_count == 0,
                    message=(
                        f"Recalculated {updated_count} opportunities "
                        f"({failed_count} failed) across {total_seen} vehicles"
                    ),
                    data={
                        "vehicle_count": total_seen,
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
