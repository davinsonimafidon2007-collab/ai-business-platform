"""Constantes configurables para el ProfitAnalyzer.

Toda la configuración económica de importación de vehículos vive aquí.
Modificar estos valores cambia el comportamiento del analizador
sin necesidad de tocar el código del mismo.

Perfiles disponibles:
    - DEFAULT: Perfil genérico (valor por defecto).
    - GERMANY: Perfil específico para importación desde Alemania.
    - FRANCE: Perfil específico para importación desde Francia.

Para añadir un nuevo país, basta con crear un nuevo perfil en este archivo.
ProfitAnalyzer lo cargará automáticamente por nombre.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

# =============================================================================
# Perfil de costes por país
# =============================================================================


@dataclass(frozen=True)
class ImportCostProfile:
    """Perfil de costes asociados a la importación desde un país de origen.

    Todos los valores están en EUR, salvo que se indique lo contrario.
    Los valores porcentuales se expresan como fracción (0..1).
    """

    # --- Costes fijos ---
    transport_cost: float
    """Coste de transporte desde el país de origen hasta destino (EUR)."""

    registration_cost: float
    """Coste de matriculación en destino (EUR)."""

    inspection_cost: float
    """Coste de ITV / inspección técnica (EUR)."""

    paperwork_cost: float
    """Coste de gestoría / trámites administrativos (EUR)."""

    miscellaneous_cost: float
    """Otros costes fijos no categorizados (EUR)."""

    # --- Costes variables (porcentaje sobre el precio de compra) ---
    tax_rate: float
    """Tasa impositiva aplicable como fracción del precio de compra (0..1)."""

    commission_rate: float
    """Comisión del intermediario como fracción del precio de compra (0..1)."""

    repair_estimate_rate: float
    """Estimación de reparaciones como fracción del precio de compra (0..1)."""

    # --- Umbrales para clasificación de riesgo ---
    risk_high_roi_threshold: float
    """ROI por encima de este valor se considera alto (fracción, ej: 0.15 = 15%)."""

    risk_low_roi_threshold: float
    """ROI por debajo de este valor se considera bajo (fracción, ej: 0.05 = 5%)."""

    risk_high_profit_threshold: float
    """Beneficio neto por encima de este valor (EUR) contribuye a riesgo bajo."""

    risk_low_profit_threshold: float
    """Beneficio neto por debajo de este valor (EUR) contribuye a riesgo alto."""

    risk_high_cost_ratio_threshold: float
    """Ratio coste total / precio de compra por encima del cual los costes son altos."""

    risk_low_cost_ratio_threshold: float
    """Ratio coste total / precio de compra por debajo del cual los costes son bajos."""


# =============================================================================
# Perfiles predefinidos
# =============================================================================

DEFAULT_PROFILE: Final[ImportCostProfile] = ImportCostProfile(
    # Costes fijos
    transport_cost=1500.0,
    registration_cost=800.0,
    inspection_cost=120.0,
    paperwork_cost=300.0,
    miscellaneous_cost=200.0,
    # Costes variables
    tax_rate=0.10,           # 10% IVA / impuestos
    commission_rate=0.05,    # 5% comisión
    repair_estimate_rate=0.03,  # 3% reparación estimada
    # Umbrales de riesgo
    risk_high_roi_threshold=0.15,
    risk_low_roi_threshold=0.05,
    risk_high_profit_threshold=3000.0,
    risk_low_profit_threshold=500.0,
    risk_high_cost_ratio_threshold=2.00,
    risk_low_cost_ratio_threshold=0.80,
)

GERMANY_PROFILE: Final[ImportCostProfile] = ImportCostProfile(
    # Alemania: transporte más barato (cercanía), matriculación similar
    transport_cost=800.0,
    registration_cost=750.0,
    inspection_cost=150.0,
    paperwork_cost=350.0,
    miscellaneous_cost=250.0,
    # IVA alemán 19% (se recupera en parte al exportar, estimamos 7% neto)
    tax_rate=0.07,
    commission_rate=0.04,
    repair_estimate_rate=0.02,
    # Umbrales ajustados para mercado alemán
    risk_high_roi_threshold=0.12,
    risk_low_roi_threshold=0.04,
    risk_high_profit_threshold=4000.0,
    risk_low_profit_threshold=800.0,
    risk_high_cost_ratio_threshold=0.25,
    risk_low_cost_ratio_threshold=0.12,
)

FRANCE_PROFILE: Final[ImportCostProfile] = ImportCostProfile(
    # Francia: transporte moderado, matriculación más cara
    transport_cost=1100.0,
    registration_cost=950.0,
    inspection_cost=130.0,
    paperwork_cost=320.0,
    miscellaneous_cost=220.0,
    # IVA francés 20% (estimación neta 8%)
    tax_rate=0.08,
    commission_rate=0.045,
    repair_estimate_rate=0.025,
    # Umbrales ajustados para mercado francés
    risk_high_roi_threshold=0.13,
    risk_low_roi_threshold=0.045,
    risk_high_profit_threshold=4500.0,
    risk_low_profit_threshold=900.0,
    risk_high_cost_ratio_threshold=0.28,
    risk_low_cost_ratio_threshold=0.13,
)

# =============================================================================
# Registro de perfiles
# =============================================================================

PROFILES: Final[dict[str, ImportCostProfile]] = {
    "DEFAULT": DEFAULT_PROFILE,
    "GERMANY": GERMANY_PROFILE,
    "FRANCE": FRANCE_PROFILE,
}

# =============================================================================
# Costes adicionales opcionales (extensibles)
# =============================================================================

ADDITIONAL_COSTS_CATEGORIES: Final[list[str]] = [
    "insurance",
    "customs",
    "financing",
    "storage",
    "detailing",
]


def get_profile(profile_name: str = "DEFAULT") -> ImportCostProfile:
    """Obtiene un perfil de costes por nombre.

    Args:
        profile_name: Nombre del perfil (case-insensitive).

    Returns:
        ImportCostProfile correspondiente.

    Raises:
        KeyError: Si el perfil no existe.
    """
    return PROFILES[profile_name.upper()]

