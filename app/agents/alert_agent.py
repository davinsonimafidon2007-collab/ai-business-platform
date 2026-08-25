"""Alert Agent: notificar cuando aparece una oportunidad relevante."""

from __future__ import annotations

from app.agents.base import BaseAgent
from app.agents.schemas import AlertAgentInput, AlertAgentOutput

# Niveles de oportunidad ordenados de más a menos relevante.
_LEVEL_RANK: dict[str, int] = {
    "EXCELLENT": 4,
    "GOOD": 3,
    "AVERAGE": 2,
    "POOR": 1,
    "REJECT": 0,
}


class AlertAgent(BaseAgent[AlertAgentInput, AlertAgentOutput]):
    """Agent del pipeline ALERT.

    Evalúa una oportunidad contra reglas umbral y devuelve los mensajes de
    alerta que dispara. No envía notificaciones: eso es responsabilidad de
    ``OpportunityAlertService``.
    """

    name = "alert_agent"
    role = "alert"
    description = (
        "Evalúa una oportunidad contra reglas umbral (nivel mínimo, beneficio "
        "mínimo, ROI mínimo) y devuelve las alertas disparadas."
    )
    input_type = AlertAgentInput
    output_type = AlertAgentOutput
    default_timeout_seconds = 5.0

    async def _execute(self, input_data: AlertAgentInput) -> AlertAgentOutput:
        opportunity = input_data.opportunity
        rules = input_data.rules
        alerts: list[str] = []

        level = (opportunity.opportunity_level or "").upper()
        recommendation = (opportunity.recommendation or "").upper()

        min_level = (rules.min_level or "").upper()
        if min_level and level and _LEVEL_RANK.get(level, -1) >= _LEVEL_RANK.get(min_level, -1):
            alerts.append(f"Oportunidad de nivel {level} detectada")

        if (
            rules.min_profit is not None
            and opportunity.estimated_profit is not None
            and float(opportunity.estimated_profit) >= float(rules.min_profit)
        ):
            alerts.append(f"Beneficio estimado >= {float(rules.min_profit):.0f} EUR")

        if (
            rules.min_roi is not None
            and opportunity.roi is not None
            and float(opportunity.roi) >= float(rules.min_roi)
        ):
            alerts.append(f"ROI >= {float(rules.min_roi):.1f}%")

        if recommendation in ("BUY_NOW", "NEGOTIATE"):
            alerts.append(f"Recomendación de acción: {recommendation}")

        return AlertAgentOutput(triggered=bool(alerts), alerts=alerts)
