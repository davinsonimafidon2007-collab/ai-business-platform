"""Stub para /api/v1/agents — evita 404 en frontend.

Los agentes reales son shims (SearchAgent, ScoringAgent, etc.) sin
persistencia. Este stub expone lista vacía para que
`frontend/src/app/hooks/useAgents.ts` no falle.
"""

from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("")
async def list_agents(
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """Lista agentes — stub vacío (agents son servicios internos)."""
    return []


@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    return {"id": agent_id, "name": agent_id, "role": "agent", "description": "", "status": "idle", "tasks_completed": 0, "avg_time": "0s", "success_rate": 0}
