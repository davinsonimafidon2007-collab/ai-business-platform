"""Negotiation Agent: preparar propuesta de negociación."""
from __future__ import annotations


class NegotiationAgent:
    """Agent para preparar argumentos y precios objetivo en negociación."""

    async def prepare_offer(self, deal: dict, defects: list[str], target_price: float) -> dict:
        return {"target_price": target_price, "arguments": defects}
