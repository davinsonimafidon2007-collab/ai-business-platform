"""Avisos de coherencia del análisis de rentabilidad (ROI.1).

Devuelve mensajes en español que advierten de valores de ROI / beneficio
incoherentes o extremos. Es una capa de AVISO (no bloqueante): no modifica
ninguna fórmula de cálculo de profit/ROI, solo genera señales legibles
para exponerlas en la API y en el front.
"""

from __future__ import annotations


def build_coherence_warnings(
    *,
    purchase_price: float | None,
    total_cost: float | None,
    estimated_profit: float | None,
    roi: float | None,
    market_price: float | None = None,
) -> list[str]:
    """Devuelve mensajes ES de coherencia; lista vacía si todo es razonable.

    Args:
        purchase_price: Precio de compra (EUR).
        total_cost: Coste total de importación (EUR).
        estimated_profit: Beneficio neto estimado (EUR).
        roi: Retorno sobre la inversión (%).
        market_price: Precio de mercado estimado (EUR), opcional.

    Returns:
        ``list[str]`` con avisos en español. Nunca lanza; si faltan datos
        se omiten las comprobaciones que los requieren.
    """
    warnings: list[str] = []

    if purchase_price is not None and purchase_price <= 0:
        warnings.append("El precio de compra no es positivo.")

    if total_cost is not None and purchase_price is not None and total_cost < purchase_price:
        warnings.append("El coste total es menor que el precio de compra (revisar desglose).")

    if roi is not None and roi > 150:
        warnings.append("ROI muy alto (>150 %); conviene validar precios y costes.")

    if roi is not None and roi < -50:
        warnings.append("ROI muy negativo (<-50 %); la operación parece inviable con estos datos.")

    if estimated_profit is not None and total_cost is not None and market_price is not None:
        # beneficio implícito vs mercado (orientativo)
        implied = market_price - total_cost
        if abs(implied - estimated_profit) > max(500.0, 0.15 * abs(estimated_profit or 1.0)):
            warnings.append(
                "El beneficio estimado no cuadra del todo con precio de mercado y coste total."
            )

    if estimated_profit is not None and estimated_profit > 0 and roi is not None and roi < 0:
        warnings.append("Beneficio positivo con ROI negativo; posible inconsistencia de cálculo.")

    if estimated_profit is not None and estimated_profit < 0 and roi is not None and roi > 0:
        warnings.append("Beneficio negativo con ROI positivo; posible inconsistencia de cálculo.")

    return warnings

