"""Tests del contrato BaseAgent (AUDIT.AGENTS.1): validación, timeout, errores y logging."""

from __future__ import annotations

import asyncio
import logging

import pytest
from pydantic import BaseModel

from app.agents.base import (
    AgentExecutionError,
    AgentTimeoutError,
    AgentValidationError,
    BaseAgent,
)


class _In(BaseModel):
    value: int = 0


class _Out(BaseModel):
    doubled: int = 0


class _OkAgent(BaseAgent[_In, _Out]):
    name = "ok_agent"
    input_type = _In
    output_type = _Out

    async def _execute(self, input_data: _In) -> _Out:
        return _Out(doubled=input_data.value * 2)


class _BoomAgent(_OkAgent):
    name = "boom_agent"

    async def _execute(self, input_data: _In) -> _Out:
        raise RuntimeError("fallo interno")


class _SlowAgent(_OkAgent):
    name = "slow_agent"

    async def _execute(self, input_data: _In) -> _Out:
        await asyncio.sleep(5)
        return _Out(doubled=input_data.value)


@pytest.mark.asyncio
async def test_run_accepts_model_and_dict_and_validates():
    agent = _OkAgent()

    from_model = await agent.run(_In(value=2))
    from_dict = await agent.run({"value": 3})

    assert from_model.doubled == 4
    assert from_dict.doubled == 6


@pytest.mark.asyncio
async def test_run_rejects_invalid_input_with_agent_validation_error():
    agent = _OkAgent()

    with pytest.raises(AgentValidationError) as excinfo:
        await agent.run({"value": "not-an-int"})

    assert excinfo.value.agent_name == "ok_agent"


@pytest.mark.asyncio
async def test_run_wraps_unexpected_errors_in_agent_execution_error():
    agent = _BoomAgent()

    with pytest.raises(AgentExecutionError) as excinfo:
        await agent.run({"value": 1})

    assert excinfo.value.agent_name == "boom_agent"
    assert "fallo interno" in str(excinfo.value)
    assert isinstance(excinfo.value.__cause__, RuntimeError)


@pytest.mark.asyncio
async def test_run_enforces_timeout():
    agent = _SlowAgent(timeout_seconds=0.05)

    with pytest.raises(AgentTimeoutError) as excinfo:
        await agent.run({"value": 1})

    assert excinfo.value.timeout_seconds == 0.05


@pytest.mark.asyncio
async def test_timeout_is_not_swallowed_by_execution_error_wrapper():
    """AgentTimeoutError NO debe reenvolverse como AgentExecutionError."""
    agent = _SlowAgent(timeout_seconds=0.01)

    with pytest.raises(AgentTimeoutError):
        await agent.run({})


def test_invalid_timeout_is_rejected_at_construction():
    with pytest.raises(ValueError):
        _OkAgent(timeout_seconds=0)


def test_default_timeout_comes_from_classvar():
    agent = _OkAgent()
    custom = _OkAgent(timeout_seconds=7.5)

    assert agent.timeout_seconds == _OkAgent.default_timeout_seconds
    assert custom.timeout_seconds == 7.5


@pytest.mark.asyncio
async def test_run_logs_start_and_completion(caplog):
    agent = _OkAgent(timeout_seconds=5)

    with caplog.at_level(logging.INFO, logger="app.agents.ok_agent"):
        await agent.run({"value": 21})

    messages = [r.getMessage() for r in caplog.records]
    assert any("started" in m for m in messages)
    assert any("completed" in m for m in messages)
