"""Etiquetas ES para partidas de CostBreakdown (PROFIT.1)."""

from __future__ import annotations

from typing import Any

# Claves = nombres de campos del breakdown / schema (alineado a
# app/services/profit_analyzer.py::CostBreakdown)
COST_LABELS_ES: dict[str, str] = {
    "purchase_price": "Precio de compra",
    "transport_cost": "Transporte",
    "registration_cost": "Matriculación",
    "taxes": "Impuestos (IVA / transferencias)",
    "inspection_cost": "ITV / inspección",
    "repair_estimate": "Reparaciones estimadas",
    "commission_cost": "Comisión",
    "miscellaneous_cost": "Otros / gestoría",
}


def build_cost_lines(breakdown: Any) -> list[dict[str, Any]]:
    """Lista ordenada {key, label_es, amount} solo con importes no None.

    El orden sigue ``CostBreakdown._COMPONENTS`` del dominio para mantener
    coherencia con la lógica de negocio.
    """
    if breakdown is None:
        return []

    lines: list[dict[str, Any]] = []
    components: tuple[tuple[str, str, str], ...] = getattr(
        breakdown, "_COMPONENTS", None
    ) or getattr(
        type(breakdown), "_COMPONENTS", tuple(COST_LABELS_ES.items())
    )

    # ``components`` usa (key, label_dominio, kind); aquí solo nos interesa key.
    ordered_keys = [item[0] for item in components]

    # Fallback por si el dominio no expone _COMPONENTS.
    if not ordered_keys:
        ordered_keys = list(COST_LABELS_ES.keys())

    seen: set[str] = set()
    for key in ordered_keys:
        if key in seen:
            continue
        seen.add(key)

        label = COST_LABELS_ES.get(key, key)
        val = (
            getattr(breakdown, key, None)
            if hasattr(breakdown, key)
            else (
                breakdown.get(key)
                if isinstance(breakdown, dict)
                else None
            )
        )
        if val is None:
            continue
        try:
            amount = float(val)
        except (TypeError, ValueError):
            continue
        lines.append({"key": key, "label_es": label, "amount": round(amount, 2)})

    return lines
