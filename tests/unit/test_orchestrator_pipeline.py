"""Tests de PipelineOrchestrator (app/orchestrator/pipeline.py) — TEST.ORCH.1.

Comportamiento real bajo test: composición SEARCH → ALERT. El único doble es
el SearchEngineService (borde externo: scraping/providers), inyectado vía el
SearchAgent. AlertAgent y sus reglas son código de producción real.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.agents.schemas import (
    AlertRulesInput,
    SearchAgentOutput,
)
from app.agents.search_agent import SearchAgent
from app.orchestrator.pipeline import PipelineInput, PipelineOrchestrator, ResultAlert


class _FakeSearchEngine:
    """Doble mínimo del borde externo (scraping)."""

    def __init__(self, results: list) -> None:
        self._results = results
        self.calls: list[SimpleNamespace] = []

    async def search(self, request, **kwargs):
        self.calls.append(request)
        return SimpleNamespace(
            summary=SimpleNamespace(total_found=len(self._results)),
            results=self._results,
            provider_issues=[],
        )


def _result(
    external_id: str = "as24-1",
    level: str = "BUY",
    recommendation: str = "BUY_NOW",
    profit: float = 5000.0,
    roi: float = 22.0,
):
    return SimpleNamespace(
        vehicle=SimpleNamespace(external_id=external_id),
        opportunity=SimpleNamespace(
            opportunity_level=level,
            recommendation=recommendation,
            estimated_profit=profit,
            roi=roi,
        ),
    )


@pytest.mark.asyncio
async def test_pipeline_returns_search_and_no_alerts_without_rules() -> None:
    engine = _FakeSearchEngine([_result()])
    orchestrator = PipelineOrchestrator(search_engine=engine)

    output = await orchestrator.run(PipelineInput(query="golf", max_results=10))

    assert output.total_results == 1
    assert output.alerts == []
    assert len(engine.calls) == 1


@pytest.mark.asyncio
async def test_pipeline_triggers_alert_for_matching_result() -> None:
    engine = _FakeSearchEngine(
        [
            _result("hot-1", profit=9000.0, roi=30.0),
            # WATCH no dispara la regla de recomendación; solo el umbral decide
            _result("cold-2", profit=100.0, roi=1.0, recommendation="WATCH"),
        ]
    )
    orchestrator = PipelineOrchestrator(search_engine=engine)

    output = await orchestrator.run(
        PipelineInput(
            query="bmw",
            alert_rules=AlertRulesInput(min_profit=5000.0),
        )
    )

    assert [a.external_id for a in output.alerts] == ["hot-1"]
    alert = output.alerts[0]
    assert isinstance(alert, ResultAlert)
    assert alert.recommendation == "BUY_NOW"
    assert alert.alerts  # el AlertAgent explica por qué se disparó


@pytest.mark.asyncio
async def test_pipeline_skips_results_without_opportunity() -> None:
    bare = SimpleNamespace(vehicle=SimpleNamespace(external_id="no-opportunity"))
    engine = _FakeSearchEngine([bare, _result("with-opp")])
    orchestrator = PipelineOrchestrator(search_engine=engine)

    output = await orchestrator.run(
        PipelineInput(query="audi", alert_rules=AlertRulesInput(min_roi=0.0))
    )
    assert [a.external_id for a in output.alerts] == ["with-opp"]


@pytest.mark.asyncio
async def test_pipeline_input_validation_rejects_empty_query() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        PipelineInput(query="")


@pytest.mark.asyncio
async def test_orchestrator_metadata_and_timeout() -> None:
    orchestrator = PipelineOrchestrator(search_engine=_FakeSearchEngine([]))
    assert orchestrator.name == "pipeline_orchestrator"
    assert orchestrator.role == "orchestrator"
    assert orchestrator.timeout_seconds == orchestrator.default_timeout_seconds


@pytest.mark.asyncio
async def test_search_agent_receives_query_and_budget() -> None:
    captured: list = []

    class CapturingAgent(SearchAgent):
        async def run(self, input_data):  # type: ignore[override]
            captured.append(input_data)
            return SearchAgentOutput(summary=SimpleNamespace(), results=[])

    class BoomEngine:
        async def search(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("no debe llamarse")

    orchestrator = PipelineOrchestrator(search_engine=BoomEngine())
    orchestrator.search_agent = CapturingAgent(search_engine=None)

    await orchestrator.run(
        PipelineInput(query="tesla model 3", max_results=5, budget_max=25000.0)
    )
    assert captured[0].query == "tesla model 3"
    assert captured[0].max_results == 5
    assert captured[0].budget_max == 25000.0


@pytest.mark.asyncio
async def test_alert_rules_min_roi_threshold_filters() -> None:
    engine = _FakeSearchEngine(
        [
            _result("roi-ok", roi=18.0, recommendation="WATCH"),
            _result("roi-low", roi=3.0, recommendation="WATCH"),
        ]
    )
    orchestrator = PipelineOrchestrator(search_engine=engine)
    output = await orchestrator.run(
        PipelineInput(query="seat", alert_rules=AlertRulesInput(min_roi=15.0))
    )
    assert [a.external_id for a in output.alerts] == ["roi-ok"]


@pytest.mark.asyncio
async def test_buy_now_recommendation_alerts_independently_of_thresholds() -> None:
    """BUY_NOW dispara alerta aunque no se superen los umbrales (regla explícita)."""
    engine = _FakeSearchEngine([_result("auto-buy", profit=10.0, roi=0.5)])
    orchestrator = PipelineOrchestrator(search_engine=engine)
    output = await orchestrator.run(
        PipelineInput(query="fiat", alert_rules=AlertRulesInput(min_profit=99999.0))
    )
    assert [a.external_id for a in output.alerts] == ["auto-buy"]
    assert any("BUY_NOW" in msg for msg in output.alerts[0].alerts)
