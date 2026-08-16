"""Constantes configurables para el ProfitAnalyzer.

Toda la configuración económica de importación de vehículos vive aquí.
Modificar estos valores cambia el comportamiento del analizador
sin necesidad de tocar el código del mismo.

Los perfiles se cargan desde ``import_costs_data.json`` (versionado) al importar
este módulo. Si el archivo falta o no existe, se usan los defaults embebidos
con un warning (fallback). Los valores fuera de rango lanzan ``ValueError``
(fail-fast) al cargar o al construir un perfil.

Perfiles disponibles (nombre canónico → uso):
    - DEFAULT: genérico.
    - GERMANY (alias DE): costes orientados a origen Alemania (legado).
    - FRANCE (alias FR): origen Francia (legado).
    - SPAIN (alias ES): importación Alemania → España (destino).
    - PORTUGAL (alias PT): importación Alemania → Portugal (destino).

Uso típico en el negocio DE→ES:
    analyzer.analyze(vehicle, profile_name="SPAIN")  # o "ES"

Para añadir un país, añade el perfil al archivo versionado
``import_costs_data.json`` y añade el alias correspondiente si procede.

Los valores son estimaciones de trabajo, no asesoramiento fiscal; deben
contrastarse con gestoría/ITV/DGT/ISV según el caso.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Final

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Rangos razonables para validación (fail-fast al cargar perfiles)
# -----------------------------------------------------------------------------

FIXED_COST_MIN: Final[float] = 0.0
FIXED_COST_MAX: Final[float] = 50000.0
RATE_MIN: Final[float] = 0.0
RATE_MAX: Final[float] = 0.5
ROI_THRESHOLD_MAX: Final[float] = 1.0
# Nota (desviación documentada de la tabla del task, que pedía `<= 1`): el perfil
# DEFAULT legado usa risk_high_cost_ratio_threshold=2.0 porque los costes de
# importación pueden superar el 100% del precio de compra en vehículos baratos.
# Para no cambiar números legados, el límite superior se fija en 3.0 (sigue
# rechazando valores absurdos).
COST_RATIO_THRESHOLD_MAX: Final[float] = 3.0

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

    # -------------------------------------------------------------------------
    # Validación de rangos (fail-fast al cargar perfiles)
    # -------------------------------------------------------------------------

    def __post_init__(self) -> None:
        """Valida los rangos razonables al construir el perfil (fail-fast)."""
        self.validate()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ImportCostProfile:
        """Construye un perfil desde un dict (p. ej. cargado de JSON).

        Raises:
            ValueError: si falta algún campo o algún valor sale de rango.
        """
        keys = (
            "transport_cost", "registration_cost", "inspection_cost",
            "paperwork_cost", "miscellaneous_cost", "tax_rate",
            "commission_rate", "repair_estimate_rate",
            "risk_high_roi_threshold", "risk_low_roi_threshold",
            "risk_high_profit_threshold", "risk_low_profit_threshold",
            "risk_high_cost_ratio_threshold", "risk_low_cost_ratio_threshold",
        )
        try:
            values = {key: float(data[key]) for key in keys}
        except KeyError as exc:
            raise ValueError(
                f"ImportCostProfile incompleto: falta el campo {exc.args[0]!r}."
            ) from exc
        return cls(**values)

    def validate(self) -> None:
        """Comprueba que todos los valores están dentro de rangos razonables.

        Raises:
            ValueError: si algún valor queda fuera de rango.
        """
        errors: list[str] = []

        for name in (
            "transport_cost", "registration_cost", "inspection_cost",
            "paperwork_cost", "miscellaneous_cost",
        ):
            value = getattr(self, name)
            if not (FIXED_COST_MIN <= value <= FIXED_COST_MAX):
                errors.append(
                    f"{name}={value} fuera de "
                    f"[{FIXED_COST_MIN}, {FIXED_COST_MAX}]"
                )

        for name in ("tax_rate", "commission_rate", "repair_estimate_rate"):
            value = getattr(self, name)
            if not (RATE_MIN <= value <= RATE_MAX):
                errors.append(
                    f"{name}={value} fuera de [{RATE_MIN}, {RATE_MAX}]"
                )

        low_roi = self.risk_low_roi_threshold
        high_roi = self.risk_high_roi_threshold
        if not (0.0 <= low_roi < high_roi <= ROI_THRESHOLD_MAX):
            errors.append(
                "ROI thresholds inválidos: se requiere "
                f"0.0 <= low ({low_roi}) < high ({high_roi}) "
                f"<= {ROI_THRESHOLD_MAX}"
            )

        low_profit = self.risk_low_profit_threshold
        high_profit = self.risk_high_profit_threshold
        if not (0.0 <= low_profit < high_profit):
            errors.append(
                "profit thresholds inválidos: se requiere "
                f"0.0 <= low ({low_profit}) < high ({high_profit})"
            )

        low_ratio = self.risk_low_cost_ratio_threshold
        high_ratio = self.risk_high_cost_ratio_threshold
        if not (0.0 <= low_ratio < high_ratio <= COST_RATIO_THRESHOLD_MAX):
            errors.append(
                "cost_ratio thresholds inválidos: se requiere "
                f"0.0 <= low ({low_ratio}) < high ({high_ratio}) "
                f"<= {COST_RATIO_THRESHOLD_MAX}"
            )

        if errors:
            raise ValueError("ImportCostProfile inválido: " + "; ".join(errors))


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

SPAIN_PROFILE: Final[ImportCostProfile] = ImportCostProfile(
    # Destino España, origen habitual Alemania (carretera ~1500–2500 km)
    transport_cost=1200.0,       # transporte puerta a puerta DE→ES
    registration_cost=450.0,     # matriculación + tasas DGT (aprox.)
    inspection_cost=90.0,        # ITV / inspección
    paperwork_cost=280.0,        # gestoría + transferencia
    miscellaneous_cost=200.0,    # seguro tránsito, imprevistos
    # IVA/impuestos simplificados (particular/VO): ~10 % efectivo sobre compra
    # (empresa + IVA 21 % pleno requerirá perfil distinto en B.2)
    tax_rate=0.10,
    commission_rate=0.04,        # intermediación / comprador profesional
    repair_estimate_rate=0.03,   # buffer cosmético/mecánico
    risk_high_roi_threshold=0.14,
    risk_low_roi_threshold=0.05,
    risk_high_profit_threshold=3500.0,
    risk_low_profit_threshold=700.0,
    risk_high_cost_ratio_threshold=0.30,
    risk_low_cost_ratio_threshold=0.12,
)

PORTUGAL_PROFILE: Final[ImportCostProfile] = ImportCostProfile(
    # Destino Portugal, origen habitual Alemania
    transport_cost=1400.0,       # algo más lejos / menos volumen de rutas
    registration_cost=550.0,     # ISV + tasas locales (orden magnitud)
    inspection_cost=100.0,
    paperwork_cost=300.0,
    miscellaneous_cost=220.0,
    tax_rate=0.12,               # carga fiscal efectiva algo mayor que ES en VO
    commission_rate=0.04,
    repair_estimate_rate=0.03,
    risk_high_roi_threshold=0.15,
    risk_low_roi_threshold=0.05,
    risk_high_profit_threshold=3800.0,
    risk_low_profit_threshold=800.0,
    risk_high_cost_ratio_threshold=0.32,
    risk_low_cost_ratio_threshold=0.13,
)

# =============================================================================
# Registro de perfiles (versión embebida = fallback)
# =============================================================================

_EMBEDDED_PROFILES: Final[dict[str, ImportCostProfile]] = {
    "DEFAULT": DEFAULT_PROFILE,
    "GERMANY": GERMANY_PROFILE,
    "FRANCE": FRANCE_PROFILE,
    "SPAIN": SPAIN_PROFILE,
    "PORTUGAL": PORTUGAL_PROFILE,
}

# Alias ISO / cortos → nombre canónico (se amplían con los del archivo de datos)
PROFILE_ALIASES: dict[str, str] = {
    "DE": "GERMANY",
    "FR": "FRANCE",
    "ES": "SPAIN",
    "PT": "PORTUGAL",
    "ESP": "SPAIN",
    "SPA": "SPAIN",
    "POR": "PORTUGAL",
}

# =============================================================================
# Carga desde archivo versionado (JSON) con fallback a defaults embebidos
# =============================================================================

_IMPORT_COSTS_DATA_FILE: Final[str] = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "import_costs_data.json"
)

FALLBACK_MESSAGE: Final[str] = (
    "Perfiles de costes no encontrados; usando defaults embebidos."
)


def _load_profiles_from_file() -> tuple[dict[str, ImportCostProfile], dict[str, str]] | None:
    """Carga los perfiles del archivo JSON versionado.

    Returns:
        (perfiles, aliases) si el archivo existe y es JSON válido; None si no existe.
    """
    if not os.path.isfile(_IMPORT_COSTS_DATA_FILE):
        return None
    with open(_IMPORT_COSTS_DATA_FILE, encoding="utf-8") as fh:
        data = json.load(fh)
    profiles: dict[str, ImportCostProfile] = {}
    for name, raw in (data.get("profiles") or {}).items():
        profiles[name.upper()] = ImportCostProfile.from_dict(raw)
    aliases: dict[str, str] = {}
    for alias, canonical in (data.get("aliases") or {}).items():
        aliases[alias.upper()] = canonical.upper()
    return profiles, aliases


_loaded_profiles = _load_profiles_from_file()
if _loaded_profiles is not None:
    PROFILES: dict[str, ImportCostProfile] = _loaded_profiles[0]
    PROFILE_ALIASES.update(_loaded_profiles[1])
else:
    logger.warning("%s no encontrado → %s", _IMPORT_COSTS_DATA_FILE, FALLBACK_MESSAGE)
    PROFILES = dict(_EMBEDDED_PROFILES)

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
    """Obtiene un perfil de costes por nombre o alias.

    Args:
        profile_name: Nombre canónico (SPAIN, GERMANY, ...) o alias (ES, DE, ...).
            Case-insensitive.

    Returns:
        ImportCostProfile correspondiente.

    Raises:
        KeyError: Si el perfil no existe (mensaje con perfiles válidos).
    """
    key = (profile_name or "DEFAULT").strip().upper()
    key = PROFILE_ALIASES.get(key, key)
    try:
        return PROFILES[key]
    except KeyError as exc:
        valid = ", ".join(sorted(PROFILES.keys()))
        aliases = ", ".join(f"{a}→{c}" for a, c in sorted(PROFILE_ALIASES.items()))
        raise KeyError(
            f"Perfil de costes desconocido: {profile_name!r}. "
            f"Válidos: {valid}. Alias: {aliases}."
        ) from exc

