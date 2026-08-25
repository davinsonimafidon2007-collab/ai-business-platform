"""Registry de agents reales (AUDIT.AGENTS.1).

Fuente única de verdad para ``GET /api/v1/agents``: sustituye al stub que
devolvía telemetría inventada. Los metadatos se derivan de los propios
agents (name, role, description) y las fábricas del DI garantizan que cada
agent listado es construible con los services reales.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from app.agents.alert_agent import AlertAgent
from app.agents.base import BaseAgent
from app.agents.budget_search_agent import BudgetSearchAgent
from app.agents.negotiation_agent import NegotiationAgent
from app.agents.opportunity_agent import OpportunityAgent
from app.agents.scoring_agent import ScoringAgent
from app.agents.search_agent import SearchAgent

if TYPE_CHECKING:
    from app.services.search_engine import SearchEngineService


def _default_factories(
    search_engine: SearchEngineService | None = None,
) -> dict[str, Callable[[], BaseAgent[Any, Any]]]:
    """Fábricas por defecto; ``search_engine`` opcional para Search/Budget/Pipeline."""
    return {
        "search": lambda: SearchAgent(search_engine=search_engine),
        "scoring": ScoringAgent,
        "opportunity": OpportunityAgent,
        "negotiation": NegotiationAgent,
        "alert": AlertAgent,
        "budget_search": lambda: BudgetSearchAgent(search_engine=search_engine),
    }


def build_registry(
    search_engine: SearchEngineService | None = None,
) -> dict[str, BaseAgent[Any, Any]]:
    """Construye todas las instancias de agents registradas."""
    return {
        agent_id: factory()
        for agent_id, factory in _default_factories(search_engine).items()
    }


def describe_agents(
    search_engine: SearchEngineService | None = None,
) -> list[dict[str, Any]]:
    """Describe los agents registrados con estado real (todos cableados al DI)."""
    registry = build_registry(search_engine)
    return [
        {
            "id": agent_id,
            "name": instance.name,
            "role": instance.role,
            "description": instance.description,
            "status": "active",
            "timeout_seconds": instance.timeout_seconds,
        }
        for agent_id, instance in sorted(registry.items())
    ]


__all__ = ["build_registry", "describe_agents"]
