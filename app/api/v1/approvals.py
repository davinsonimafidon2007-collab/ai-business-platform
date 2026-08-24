"""Stub para /api/v1/approvals — evita 404 en frontend.

El flujo real de aprobaciones usa `opportunity_phases` con
`pending_approval`. Este stub lista fases pendientes globales para que
`frontend/src/app/hooks/useApprovals.ts` no entre en error.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.dependencies.auth import get_current_user
from app.models.opportunity_phase import OpportunityPhase
from app.models.user import User

router = APIRouter(prefix="/approvals", tags=["Approvals"])


@router.get("")
async def list_approvals(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    """Lista aprobaciones pendientes — deriva de opportunity_phases."""
    try:
        result = await session.execute(
            select(OpportunityPhase).where(OpportunityPhase.status == "pending_approval").limit(50)
        )
        phases = result.scalars().all()
        return [
            {
                "id": p.id,
                "opportunity_id": p.opportunity_id,
                "title": p.title,
                "category": p.agent or "general",
                "description": p.description or "",
                "priority": "MEDIO",
                "status": "pending",
                "created_at": p.created_at.isoformat() if p.created_at else "",
            }
            for p in phases
        ]
    except Exception:
        # Si la tabla no existe aún (migración no corrida), devuelve vacío
        return []
