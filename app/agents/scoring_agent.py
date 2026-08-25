"""Scoring Agent: calcular score de vehículo y re-scoring por cambio de precio.

Absorbe al antiguo ``ReScoringAgent`` (AUDIT.AGENTS.1): ambos usaban el mismo
service (VehicleScorer) con la misma llamada; el re-scoring es ahora el método
``rescore`` de este agent, que además calcula el delta frente al precio previo.
"""

from __future__ import annotations

from app.agents.base import BaseAgent
from app.agents.schemas import (
    RescoreAgentInput,
    RescoreAgentOutput,
    ScoringAgentInput,
    ScoringAgentOutput,
)
from app.services.vehicle_scorer import VehicleScorer


class ScoringAgent(BaseAgent[ScoringAgentInput, ScoringAgentOutput]):
    """Agent del pipeline SCORE.

    Delega en VehicleScorer, el motor real de puntuación por reglas.
    """

    name = "scoring_agent"
    role = "scoring"
    description = (
        "Calcula el score objetivo 0-100 de un vehículo a partir de sus campos "
        "(precio, km, año, combustible, transmisión, potencia, anuncio)."
    )
    input_type = ScoringAgentInput
    output_type = ScoringAgentOutput
    default_timeout_seconds = 10.0

    def __init__(
        self,
        scorer: VehicleScorer | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        super().__init__(timeout_seconds=timeout_seconds)
        self._scorer = scorer or VehicleScorer()

    async def _execute(self, input_data: ScoringAgentInput) -> ScoringAgentOutput:
        return self._score_output(input_data.vehicle.model_dump())

    def _score_output(self, vehicle_fields: dict[str, object]) -> ScoringAgentOutput:
        result = self._scorer.score_from_dto(**vehicle_fields)
        return ScoringAgentOutput(
            score=result.score,
            category_key=result.category_key,
            category_label_es=result.category_label_es or result.category,
            strengths=result.strengths,
            weaknesses=result.weaknesses,
        )

    # ------------------------------------------------------------------
    # Re-scoring (antiguo ReScoringAgent)
    # ------------------------------------------------------------------

    async def rescore(self, input_data: RescoreAgentInput | dict[str, object]) -> RescoreAgentOutput:
        """Recalcula el score con un precio nuevo y lo compara con el anterior."""
        validated = RescoreAgentInput.model_validate(input_data)
        previous_fields = dict(validated.vehicle.model_dump())
        previous_score = self._scorer.score_from_dto(**previous_fields)

        new_fields = dict(previous_fields)
        new_fields["price"] = validated.new_price
        new_score = self._scorer.score_from_dto(**new_fields)

        return RescoreAgentOutput(
            vehicle_id=validated.vehicle_id,
            previous_price=validated.vehicle.price,
            new_price=validated.new_price,
            previous_score=previous_score.score,
            score=new_score.score,
            delta=float(new_score.score - previous_score.score),
            category_key=new_score.category_key,
            category_label_es=new_score.category_label_es or new_score.category,
        )
