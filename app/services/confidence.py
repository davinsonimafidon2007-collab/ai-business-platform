"""Cálculo único de ``confidence`` (TASK 2 — motor económico).

Separa explícitamente tres conceptos que el resto del sistema (scoring,
ProfitAnalyzer, OpportunityFinder, EvaluationEngine) no debe mezclar:

- **profitability**: cuánto dinero se podría ganar (ProfitAnalysis, ROI, margen).
- **risk**: cuán probable es que la operación salga mal (RiskLevel).
- **confidence**: cuán fiables son los datos usados para estimar lo anterior.

Una oportunidad puede tener beneficio alto, riesgo alto y confianza baja al
mismo tiempo: eso es información legítima y debe conservarse, no colapsarse
en una única etiqueta "buena oportunidad". Este módulo es la única función
que calcula ``confidence`` en todo el proyecto — tanto ``OpportunityFinder``
(flujo de búsqueda) como ``EvaluationEngine`` (job de recálculo periódico)
delegan aquí en vez de reimplementar su propia heurística.
"""

from __future__ import annotations

from app.config.opportunity import (
    CONFIDENCE_EXTRA_WARNING_PENALTY,
    CONFIDENCE_MISSING_FIELD_PENALTY,
    CONFIDENCE_NO_MARKET_DATA_BASELINE,
)

# Fragmentos (en minúsculas) que, si aparecen en una debilidad/razón del
# VehicleScore u OpportunityFinder, indican un dato crítico ausente o una
# estimación no respaldada por datos reales.
_MISSING_DATA_MARKERS: tuple[str, ...] = (
    "sin precio",
    "no especificado",
    "sin comparativa de mercado",
    "no se pudo estimar",
)


def estimate_confidence(
    *,
    market_confidence: float | None,
    warnings: list[str] | None = None,
    weaknesses: list[str] | None = None,
    market_grounded: bool = True,
) -> float:
    """Calcula una confianza 0-100 a partir de señales disponibles.

    Args:
        market_confidence: Confianza del ``MarketEstimator`` (0-100) si hay
            una estimación de mercado disponible; ``None`` si no se consultó.
        warnings: Avisos del ``ProfitAnalysis`` (el primero suele ser el
            disclaimer estándar; solo los adicionales penalizan).
        weaknesses: Debilidades textuales del ``VehicleScore``/``OpportunityAnalysis``.
        market_grounded: ``False`` cuando el precio de venta estimado viene
            del multiplicador por defecto en vez de un comparable real.

    Returns:
        Confianza en el rango [0, 100]. Nunca inventa una confianza alta
        cuando faltan datos: el punto de partida ya refleja la ausencia de
        mercado, y solo se aplican penalizaciones adicionales, nunca bonos.
    """
    if market_confidence is not None:
        base = max(0.0, min(100.0, float(market_confidence)))
    else:
        base = CONFIDENCE_NO_MARKET_DATA_BASELINE

    if not market_grounded:
        base = min(base, CONFIDENCE_NO_MARKET_DATA_BASELINE)

    penalty = 0.0

    for weakness in weaknesses or []:
        text = str(weakness).lower()
        if any(marker in text for marker in _MISSING_DATA_MARKERS):
            penalty += CONFIDENCE_MISSING_FIELD_PENALTY

    real_warnings = [w for w in (warnings or []) if w]
    # ProfitAnalyzer siempre antepone un disclaimer estándar como primer
    # warning; solo los avisos adicionales (costes anómalos, etc.) penalizan.
    extra_warnings = max(0, len(real_warnings) - 1)
    penalty += extra_warnings * CONFIDENCE_EXTRA_WARNING_PENALTY

    return round(max(0.0, min(100.0, base - penalty)), 2)
