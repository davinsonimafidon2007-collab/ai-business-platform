"""Alert Agent: notificar cuando aparece una oportunidad relevante."""
from __future__ import annotations


class AlertAgent:
    """Agent para generar alertas según reglas configuradas."""

    async def check_and_alert(self, opportunity: dict, rules: dict) -> list[str]:
        return []
