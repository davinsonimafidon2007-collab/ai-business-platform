"""Alert Agent: notificar cuando aparece una oportunidad relevante."""
from __future__ import annotations

from typing import Any

# Niveles de oportunidad ordenados de más a menos relevante.
_LEVEL_RANK: dict[str, int] = {
    "EXCELLENT": 4,
    "GOOD": 3,
    "AVERAGE": 2,
    "POOR": 1,
    "REJECT": 0,
}


class AlertAgent:
    """Agent para generar alertas según reglas configuradas.

    Evalúa una oportunidad contra reglas umbral y devuelve los mensajes de
    alerta que dispara. No envía notificaciones: eso es responsabilidad de
    ``OpportunityAlertService``.
    """

    async def check_and_alert(self, opportunity: dict[str, Any], rules: dict[str, Any]) -> list[str]:
        """Genera alertas de texto si la oportunidad supera los umbrales.

        Args:
            opportunity: Dict con ``opportunity_level``, ``recommendation``,
                ``estimated_profit`` y ``roi`` (formato API de oportunidad).
            rules: Dict con umbrales opcionales:
                ``min_level`` (EXCELLENT/GOOD/AVERAGE/...),
                ``min_profit`` (EUR), ``min_roi`` (%).

        Returns:
            Lista de mensajes de alerta (vacía si no supera ningún umbral).
        """
        alerts: list[str] = []
        if not isinstance(opportunity, dict):
            return alerts

        level = str(opportunity.get("opportunity_level", "") or "").upper()
        recommendation = str(opportunity.get("recommendation", "") or "").upper()
        estimated_profit = opportunity.get("estimated_profit")
        roi = opportunity.get("roi")

        min_level = str(rules.get("min_level", "") or "").upper()
        if min_level and level and _LEVEL_RANK.get(level, -1) >= _LEVEL_RANK.get(min_level, -1):
            alerts.append(f"Oportunidad de nivel {level} detectada")

        min_profit = rules.get("min_profit")
        if min_profit is not None and estimated_profit is not None and float(estimated_profit) >= float(min_profit):
            alerts.append(f"Beneficio estimado >= {float(min_profit):.0f} EUR")

        min_roi = rules.get("min_roi")
        if min_roi is not None and roi is not None and float(roi) >= float(min_roi):
            alerts.append(f"ROI >= {float(min_roi):.1f}%")

        if recommendation in ("BUY_NOW", "NEGOTIATE"):
            alerts.append(f"Recomendación de acción: {recommendation}")

        return alerts
