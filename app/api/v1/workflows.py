"""Stub para /api/v1/workflows — evita 404 en frontend.

El pipeline real usa opportunity_phases y search_orders, no un recurso
`workflows` separado. Este stub devuelve lista vacía para que
`frontend/src/app/hooks/useWorkflows.ts` no entre en isError.
Cuando se implemente workflow engine real, reemplazar por lógica persistida.
"""

from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/workflows", tags=["Workflows"])


@router.get("")
async def list_workflows(
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """Lista workflows — stub vacío (no hay recurso workflows aún)."""
    return []


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    return {"id": workflow_id, "name": "Workflow", "status": "completed", "phases": 0, "completed_phases": 0, "last_run": None}
