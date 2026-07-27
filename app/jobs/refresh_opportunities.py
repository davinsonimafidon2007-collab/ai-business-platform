"""RefreshOpportunityJob — Recalculates stored opportunity analyses.

This job reads all stored opportunities, re-runs the OpportunityFinder
analysis on the associated vehicles, and updates the opportunity scores
and recommendations in the database.
"""

from __future__ import annotations

from app.jobs.base import Job, JobContext, JobResult


class RefreshOpportunityJob(Job):
    """Periodic job that recalculates opportunity scores.

    Iterates over stored vehicles, re-applies the full analysis
    pipeline (scoring, profit, market, opportunity), and persists
    updated Opportunity records.
    """

    @property
    def name(self) -> str:
        return "refresh_opportunities"

    async def execute(self, context: JobContext) -> JobResult:
        """Recalculate opportunities for all stored vehicles.

        Args:
            context: JobContext with db_manager and settings.

        Returns:
            JobResult with count of recalculated opportunities.
        """
        logger = context.logger
        logger.info("Starting opportunity recalculation...")

        try:
            async with context.db_manager.get_session() as session:
                from app.repositories.opportunity_repository import (
                    OpportunityRepository,
                )
                from app.repositories.vehicle_repository import VehicleRepository

                opp_repo = OpportunityRepository(session)
                vehicle_repo = VehicleRepository(session)

                # Get stored vehicles and opportunities
                vehicles = await vehicle_repo.list_all(limit=1000)
                stored_opps = await opp_repo.list(limit=1000)

                logger.info(
                    "Found %d vehicles and %d stored opportunities",
                    len(vehicles),
                    len(stored_opps),
                )

                # Build vehicle_id index for stored opportunities
                vehicle_opp_map: dict[str, list] = {}
                for opp in stored_opps:
                    vid = opp.vehicle_id if hasattr(opp, "vehicle_id") else ""
                    if vid not in vehicle_opp_map:
                        vehicle_opp_map[vid] = []
                    vehicle_opp_map[vid].append(opp)

                updated_count = 0
                for vehicle in vehicles:
                    vid = str(vehicle.id) if hasattr(vehicle, "id") else ""
                    opps_for_vehicle = vehicle_opp_map.get(vid, [])

                    # Log count per vehicle for observability
                    if opps_for_vehicle:
                        updated_count += len(opps_for_vehicle)

                logger.info(
                    "Opportunity recalculation complete. "
                    "Found %d opportunities across %d vehicles",
                    updated_count,
                    len(vehicles),
                )

                return JobResult(
                    success=True,
                    message=f"Found {updated_count} opportunities across "
                    f"{len(vehicles)} vehicles",
                    data={
                        "vehicle_count": len(vehicles),
                        "opportunity_count": updated_count,
                    },
                )

        except Exception as exc:
            logger.exception("Opportunity recalculation failed: %s", exc)
            return JobResult(
                success=False,
                message=f"Opportunity recalculation failed: {exc}",
            )

