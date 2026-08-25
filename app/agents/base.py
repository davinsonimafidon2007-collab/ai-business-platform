"""Base contract for all domain agents (AUDIT.AGENTS.1).

Todo agent del dominio hereda de ``BaseAgent`` y gana de forma uniforme:

- Interfaz única: ``run(input) -> output`` con esquemas Pydantic tipados.
- Validación del input contra el schema declarado (``input_type``).
- Timeout por agente (``asyncio.wait_for``).
- Manejo de errores con taxonomía propia (``AgentError`` y subclases).
- Logging estructurado de inicio/fin/duración y errores.

Los agents son la capa fina de orquestación de dominio: delegan el trabajo
pesado en los services reales (SearchEngineService, VehicleScorer,
OpportunityFinder, NegotiationEngine). No duplican lógica de negocio.
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Generic, TypeVar

from pydantic import BaseModel, ValidationError

from app.core.logging import get_logger

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class AgentError(Exception):
    """Base de todos los errores de agents."""


class AgentValidationError(AgentError):
    """El input no cumple el schema de entrada del agent."""

    def __init__(self, agent_name: str, detail: str) -> None:
        self.agent_name = agent_name
        self.detail = detail
        super().__init__(f"Invalid input for agent '{agent_name}': {detail}")


class AgentTimeoutError(AgentError):
    """El agent excedió su timeout."""

    def __init__(self, agent_name: str, timeout_seconds: float) -> None:
        self.agent_name = agent_name
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Agent '{agent_name}' timed out after {timeout_seconds:.1f}s"
        )


class AgentExecutionError(AgentError):
    """Fallo inesperado durante la ejecución del agent."""

    def __init__(self, agent_name: str, detail: str) -> None:
        self.agent_name = agent_name
        self.detail = detail
        super().__init__(f"Agent '{agent_name}' failed: {detail}")


class BaseAgent(ABC, Generic[InputT, OutputT]):
    """Plantilla base para todos los agents del dominio.

    Subclases declaran:

    - ``name`` / ``role`` / ``description``: metadatos para el registry.
    - ``input_type`` / ``output_type``: schemas Pydantic de entrada/salida.
    - ``default_timeout_seconds``: timeout por defecto (sobreescrible por
      instancia vía constructor).

    e implementan ``_execute(input_data) -> output``.
    """

    name: ClassVar[str] = "base_agent"
    role: ClassVar[str] = "agent"
    description: ClassVar[str] = ""
    input_type: ClassVar[type[BaseModel]]
    output_type: ClassVar[type[BaseModel]]
    default_timeout_seconds: ClassVar[float] = 30.0

    def __init__(self, timeout_seconds: float | None = None) -> None:
        if timeout_seconds is not None and timeout_seconds <= 0:
            raise ValueError("timeout_seconds debe ser > 0")
        self._timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else self.default_timeout_seconds
        )
        self._logger = get_logger(f"app.agents.{self.name}")

    @property
    def timeout_seconds(self) -> float:
        return self._timeout_seconds

    async def run(self, input_data: InputT | dict[str, Any]) -> OutputT:
        """Ejecuta el agent: valida input, aplica timeout, loggea y envuelve errores.

        Args:
            input_data: Modelo Pydantic del schema ``input_type`` o un dict
                validable contra él.

        Returns:
            Output del schema ``output_type``.

        Raises:
            AgentValidationError: Input inválido según el schema.
            AgentTimeoutError: Ejecución excedió el timeout.
            AgentExecutionError: Fallo interno del agent o del service subyacente.
        """
        try:
            validated_input = self.input_type.model_validate(input_data)
        except ValidationError as exc:
            self._logger.warning(
                "Agent '%s' rejected invalid input: %s", self.name, exc.error_count()
            )
            raise AgentValidationError(self.name, str(exc)) from exc

        started = time.perf_counter()
        self._logger.info(
            "Agent '%s' started (timeout=%.1fs)", self.name, self._timeout_seconds
        )
        try:
            output = await asyncio.wait_for(
                self._execute(validated_input), timeout=self._timeout_seconds
            )
        except TimeoutError as exc:
            duration = time.perf_counter() - started
            self._logger.warning(
                "Agent '%s' timed out after %.1fs", self.name, duration
            )
            raise AgentTimeoutError(self.name, self._timeout_seconds) from exc
        except AgentError:
            raise
        except Exception as exc:
            duration = time.perf_counter() - started
            self._logger.exception(
                "Agent '%s' failed after %.1fs: %s", self.name, duration, exc
            )
            raise AgentExecutionError(self.name, str(exc)) from exc

        duration = time.perf_counter() - started
        self._logger.info(
            "Agent '%s' completed in %.1fms", self.name, duration * 1000
        )
        return output

    @abstractmethod
    async def _execute(self, input_data: InputT) -> OutputT:
        """Implementación concreta del agent (sin logging/timeout/validation)."""
