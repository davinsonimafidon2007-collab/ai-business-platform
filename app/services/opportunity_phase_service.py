"""Service for opportunity workflow phases."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.opportunity import Opportunity
from app.models.opportunity_phase import OpportunityPhase
from app.repositories.opportunity_phase_repository import OpportunityPhaseRepository


class OpportunityPhaseService:
    """Business logic for opportunity workflow phases."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = OpportunityPhaseRepository(session)

    async def list_phases(self, opportunity_id: str) -> list[OpportunityPhase]:
        return await self.repo.get_for_opportunity(opportunity_id)

    async def get_phase(self, phase_id: str) -> OpportunityPhase | None:
        return await self.repo.get_by_id(phase_id)

    async def apply_action(
        self,
        opportunity: Opportunity,
        phase_id: str,
        action: str,
        feedback: str | None = None,
    ) -> OpportunityPhase:
        phase = await self.get_phase(phase_id)
        if phase is None or phase.opportunity_id != opportunity.id:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Phase not found for this opportunity",
            )

        allowed = {"approve", "reject", "request_changes", "start"}
        if action not in allowed:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action '{action}'. Allowed: {sorted(allowed)}",
            )

        return await self.repo.update_from_action(phase, action, feedback=feedback)

    async def ensure_seeded(self, opportunity: Opportunity) -> list[OpportunityPhase]:
        return await self.repo.seed_for_opportunity(opportunity)

    @staticmethod
    def to_read(phase: OpportunityPhase) -> dict:
        return {
            "id": phase.id,
            "opportunity_id": phase.opportunity_id,
            "title": phase.title,
            "description": phase.description,
            "status": phase.status,
            "agent": phase.agent,
            "order": phase.order,
            "started_at": phase.started_at.isoformat() if phase.started_at else None,
            "completed_at": phase.completed_at.isoformat() if phase.completed_at else None,
            "feedback": phase.feedback,
            "created_at": phase.created_at.isoformat() if phase.created_at else None,
            "updated_at": phase.updated_at.isoformat() if phase.updated_at else None,
        }
