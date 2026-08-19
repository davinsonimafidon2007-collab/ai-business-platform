from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import object_session
from sqlalchemy.util import greenlet_spawn

from app.schemas.search import ProviderIssue


class PipelineResult(BaseModel):
    """Resultado de la ejecución del pipeline end-to-end."""
    vehicles: list[Any] = Field(default_factory=list)
    opportunities: list[Any] = Field(default_factory=list)
    provider_issues: list[ProviderIssue] = Field(default_factory=list)


class PipelineOrchestrator:
    """Orquestador de pipeline de agentes de búsqueda y análisis."""

    def __init__(
        self,
        search_engine: Any = None,
        opportunity_finder: Any = None,
        profit_analyzer: Any = None,
    ) -> None:
        self.search_engine = search_engine
        self.opportunity_finder = opportunity_finder
        self.profit_analyzer = profit_analyzer

    async def _commit_order_session(self, search_order: Any) -> None:
        """Sincroniza y hace commit en la sesión de SQLAlchemy si existe."""
        sync_sess = object_session(search_order)
        if sync_sess is not None:
            await greenlet_spawn(sync_sess.commit)

    async def run_pipeline(self, search_order: Any) -> PipelineResult:
        """Ejecuta el pipeline completo para una orden de búsqueda."""
        search_order.status = "RUNNING"
        await self._commit_order_session(search_order)

        vehicles: list[Any] = []
        opportunities: list[Any] = []
        provider_issues: list[ProviderIssue] = []

        try:
            if self.search_engine is not None:
                search_res = await self.search_engine.search(search_order)
                if isinstance(search_res, list):
                    vehicles = search_res
                elif hasattr(search_res, "results"):
                    vehicles = list(search_res.results)
                elif hasattr(search_res, "vehicles"):
                    vehicles = list(search_res.vehicles)

                # Extraer provider_issues del engine o del resultado
                engine_issues = getattr(self.search_engine, "last_provider_issues", None)
                if engine_issues:
                    provider_issues.extend(engine_issues)
                elif hasattr(search_res, "provider_issues") and search_res.provider_issues:
                    provider_issues.extend(search_res.provider_issues)

            if vehicles and self.opportunity_finder is not None:
                opps = await self.opportunity_finder.find_opportunities(vehicles)
                if opps:
                    opportunities = list(opps)

            if vehicles and self.profit_analyzer is not None:
                for v in vehicles:
                    try:
                        await self.profit_analyzer.analyze(v)
                    except Exception:
                        pass

            search_order.status = "COMPLETED"

        except Exception as exc:
            search_order.status = "FAILED"
            provider_issues.append(
                ProviderIssue(
                    provider="autoscout24",
                    stage="search",
                    error_type=type(exc).__name__,
                    message=str(exc) or "Provider failure",
                )
            )

        await self._commit_order_session(search_order)

        return PipelineResult(
            vehicles=vehicles,
            opportunities=opportunities,
            provider_issues=provider_issues,
        )
