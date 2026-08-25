"""API de agents (AUDIT.AGENTS.1) — registry real + ejecución del pipeline.

Reemplaza al stub que devolvía telemetría inventada: ahora los metadatos
vienen del registry de ``app.agents.registry`` (agents reales, cableados al
DI) y ``POST /pipeline/run`` ejecuta el pipeline SEARCH → ALERT con los
agents reales.

Nota honestidad (mocks): los agents son funciones de dominio sin estado
persistido; no existe aún contador de tareas/latencia/éxito por agent, así
que esos campos se exponen a cero con ``metrics_available=false`` en vez de
simular valores.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.agents.base import (
    AgentError,
    AgentExecutionError,
    AgentTimeoutError,
    AgentValidationError,
)
from app.agents.registry import describe_agents
from app.api.v1.dependencies import get_pipeline_orchestrator
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.orchestrator.pipeline import PipelineInput, PipelineOutput

router = APIRouter(prefix="/agents", tags=["Agents"])


class AgentInfo(BaseModel):
    """Metadatos de un agent registrado."""

    id: str
    name: str
    role: str
    description: str
    status: Literal["active"]
    timeout_seconds: float
    tasks_completed: int = Field(0, description="Sin tracking por agent aún")
    avg_time: str = Field("-", description="Sin tracking por agent aún")
    success_rate: float = Field(0.0, description="Sin tracking por agent aún")
    metrics_available: bool = False


@router.get("")
async def list_agents(
    current_user: User = Depends(get_current_user),
) -> list[AgentInfo]:
    """Lista los agents del dominio desde el registry real."""
    return [AgentInfo(**entry) for entry in describe_agents()]


@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
) -> AgentInfo:
    """Detalle de un agent; 404 si no existe (antes devolvía datos inventados)."""
    for entry in describe_agents():
        if entry["id"] == agent_id:
            return AgentInfo(**entry)
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Agent '{agent_id}' no encontrado",
    )


@router.post("/pipeline/run", response_model=PipelineOutput)
async def run_pipeline(
    pipeline_input: PipelineInput,
    orchestrator: Any = Depends(get_pipeline_orchestrator),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Ejecuta el pipeline completo (búsqueda end-to-end + reglas de alerta)."""
    try:
        return await orchestrator.run(pipeline_input)
    except AgentValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AgentTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except AgentExecutionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except AgentError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
