from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.opportunity import Opportunity
from app.models.opportunity_phase import OpportunityPhase


class OpportunityPhaseRepository:
    """Repository for OpportunityPhase persistence operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_for_opportunity(
        self, opportunity_id: str | UUID
    ) -> list[OpportunityPhase]:
        result = await self.session.execute(
            select(OpportunityPhase)
            .where(OpportunityPhase.opportunity_id == str(opportunity_id))
            .order_by(OpportunityPhase.order, OpportunityPhase.created_at)
        )
        return list(result.scalars().all())

    async def get_by_id(self, phase_id: str) -> OpportunityPhase | None:
        result = await self.session.execute(
            select(OpportunityPhase).where(OpportunityPhase.id == phase_id)
        )
        return result.scalar_one_or_none()

    async def save(self, phase: OpportunityPhase) -> OpportunityPhase:
        self.session.add(phase)
        await self.session.commit()
        await self.session.refresh(phase)
        return phase

    async def update_from_action(
        self,
        phase: OpportunityPhase,
        action: str,
        feedback: str | None = None,
    ) -> OpportunityPhase:
        now = datetime.now(UTC)
        if action == "approve":
            if phase.status == "pending_approval":
                phase.status = "completed"
            phase.completed_at = now
        elif action == "reject":
            phase.status = "aborted"
            phase.completed_at = now
        elif action == "request_changes":
            phase.status = "in_progress"
            phase.feedback = feedback
        elif action == "start":
            phase.status = "in_progress"
            phase.started_at = now

        phase.updated_at = now
        return await self.save(phase)

    async def seed_for_opportunity(
        self, opportunity: Opportunity
    ) -> list[OpportunityPhase]:
        """Create default workflow phases if none exist."""
        existing = await self.get_for_opportunity(opportunity.id)
        if existing:
            return existing

        phases = [
            OpportunityPhase(
                opportunity_id=opportunity.id,
                title="Evaluación inicial",
                description="Puntuación del vehículo, mercado y rentabilidad.",
                status="completed",
                order=1,
                agent="evaluation-engine",
            ),
            OpportunityPhase(
                opportunity_id=opportunity.id,
                title="Oferta / Negociación",
                description="Propuesta de compra y argumentos.",
                status="pending_approval",
                order=2,
                agent="negotiation-engine",
            ),
            OpportunityPhase(
                opportunity_id=opportunity.id,
                title="Compra",
                description="Cierre de operación.",
                status="pending",
                order=3,
                agent="user",
            ),
            OpportunityPhase(
                opportunity_id=opportunity.id,
                title="Importación",
                description="Transporte, matriculación e impuestos.",
                status="pending",
                order=4,
                agent="logistics",
            ),
        ]
        for phase in phases:
            self.session.add(phase)
        await self.session.commit()
        for phase in phases:
            await self.session.refresh(phase)
        return phases
