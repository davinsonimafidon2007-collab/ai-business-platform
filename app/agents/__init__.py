"""Agents de dominio: capa fina de orquestación sobre los services reales.

Todos heredan de ``BaseAgent`` (interfaz ``run`` única con schemas Pydantic,
logging, timeout y taxonomía de errores) y delegan el trabajo pesado en los
services de ``app.services``:

- SearchAgent -> SearchEngineService
- ScoringAgent -> VehicleScorer (incluye re-scoring por cambio de precio)
- OpportunityAgent -> OpportunityFinder
- NegotiationAgent -> NegotiationEngine
- AlertAgent -> reglas umbral (notificación real en OpportunityAlertService)
- BudgetSearchAgent -> SearchEngineService + perfiles de costes de importación
"""

from app.agents.alert_agent import AlertAgent
from app.agents.base import (
    AgentError,
    AgentExecutionError,
    AgentTimeoutError,
    AgentValidationError,
    BaseAgent,
)
from app.agents.budget_search_agent import BudgetSearchAgent
from app.agents.negotiation_agent import NegotiationAgent
from app.agents.opportunity_agent import OpportunityAgent
from app.agents.scoring_agent import ScoringAgent
from app.agents.search_agent import SearchAgent

__all__ = [
    "AgentError",
    "AgentExecutionError",
    "AgentTimeoutError",
    "AgentValidationError",
    "AlertAgent",
    "BaseAgent",
    "BudgetSearchAgent",
    "NegotiationAgent",
    "OpportunityAgent",
    "ScoringAgent",
    "SearchAgent",
]
