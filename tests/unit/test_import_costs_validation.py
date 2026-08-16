"""Tests de validación y carga versionada de perfiles de costes (Task ECON-001).

Cubre:
    - Carga desde `import_costs_data.json` con valores que coinciden con los
      defaults embebidos (no se inventan números).
    - Fallback a defaults embebidos cuando el archivo no existe.
    - Validación de rangos (fail-fast): valores fuera de rango → ValueError.
    - Aliases (`ES` ≡ `SPAIN`, etc.).
    - Perfil desconocido → KeyError.
"""

from __future__ import annotations

import json
import os

import pytest

import app.config.import_costs as ic
from app.config.import_costs import ImportCostProfile, get_profile
from app.services.profit_analyzer import ProfitAnalyzer

# =============================================================================
# Helpers
# =============================================================================


def _data_file() -> str:
    """Ruta absoluta del archivo de datos versionado."""
    config_dir = os.path.dirname(os.path.abspath(ic.__file__))
    return os.path.join(config_dir, "import_costs_data.json")


BASE = {
    "transport_cost": 1200.0,
    "registration_cost": 450.0,
    "inspection_cost": 90.0,
    "paperwork_cost": 280.0,
    "miscellaneous_cost": 200.0,
    "tax_rate": 0.10,
    "commission_rate": 0.04,
    "repair_estimate_rate": 0.03,
    "risk_high_roi_threshold": 0.14,
    "risk_low_roi_threshold": 0.05,
    "risk_high_profit_threshold": 3500.0,
    "risk_low_profit_threshold": 700.0,
    "risk_high_cost_ratio_threshold": 0.30,
    "risk_low_cost_ratio_threshold": 0.12,
}


def _valid(mutations: dict[str, float] | None = None) -> dict[str, float]:
    d = dict(BASE)
    if mutations:
        d.update(mutations)
    return d


def _all_fields(**overrides) -> dict[str, float]:
    """Dict con TODOS los campos de ImportCostProfile (construcción directa)."""
    d = dict(BASE)
    d.update(overrides)
    return d


# =============================================================================
# Carga versionada (JSON) + fallback
# =============================================================================


def test_json_data_file_exists_and_versioned() -> None:
    assert os.path.isfile(_data_file()), "Falta app/config/import_costs_data.json"
    with open(_data_file(), encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["version"]  # ej. "2026.08"
    assert data["currency"] == "EUR"
    for canonical in ("DEFAULT", "GERMANY", "FRANCE", "SPAIN", "PORTUGAL"):
        assert canonical in data["profiles"]


def test_json_values_match_embedded_defaults() -> None:
    """Los valores del JSON deben coincidir con los defaults embebidos.

    Objetivo del task: externalizar + validar, no recalibrar.
    """
    with open(_data_file(), encoding="utf-8") as fh:
        data = json.load(fh)
    for name, raw in data["profiles"].items():
        embedded = getattr(ic, f"{name}_PROFILE")
        for key, value in raw.items():
            assert getattr(embedded, key) == value, f"{name}.{key} no coincide"


def test_profiles_loaded_from_file() -> None:
    p = get_profile("SPAIN")
    assert p.transport_cost == 1200.0
    assert p.registration_cost == 450.0


def test_missing_data_file_falls_back(monkeypatch) -> None:
    """Si el archivo no existe, _load_profiles_from_file devuelve None (fallback)."""
    monkeypatch.setattr(
        ic, "_IMPORT_COSTS_DATA_FILE", "/nonexistent/import_costs_data.json"
    )
    assert ic._load_profiles_from_file() is None


def test_aliases_es_pt_de_fr() -> None:
    assert get_profile("ES") is get_profile("SPAIN")
    assert get_profile("PT") is get_profile("PORTUGAL")
    assert get_profile("DE") is get_profile("GERMANY")
    assert get_profile("FR") is get_profile("FRANCE")


def test_unknown_profile_raises_keyerror() -> None:
    with pytest.raises(KeyError, match="desconocido"):
        get_profile("NARNIA")


# =============================================================================
# from_dict con JSON válido
# =============================================================================


def test_from_dict_valid() -> None:
    p = ImportCostProfile.from_dict(BASE)
    assert p.transport_cost == 1200.0
    assert p.tax_rate == 0.10



# =============================================================================
# Validación de rangos (fail-fast)
# =============================================================================


def test_negative_fixed_cost_raises() -> None:
    with pytest.raises(ValueError, match="transport_cost"):
        ImportCostProfile.from_dict(_valid({"transport_cost": -1.0}))


def test_fixed_cost_over_limit_raises() -> None:
    with pytest.raises(ValueError, match="transport_cost"):
        ImportCostProfile.from_dict(_valid({"transport_cost": 60000.0}))


def test_tax_rate_absurd_raises() -> None:
    # Ejemplo del task: JSON/YAML con tax_rate 0.9 → ValueError
    with pytest.raises(ValueError, match="tax_rate"):
        ImportCostProfile.from_dict(_valid({"tax_rate": 0.9}))


def test_rate_over_half_raises() -> None:
    with pytest.raises(ValueError, match="commission_rate"):
        ImportCostProfile.from_dict(_valid({"commission_rate": 0.6}))


def test_roi_low_not_below_high_raises() -> None:
    with pytest.raises(ValueError, match="ROI thresholds"):
        ImportCostProfile.from_dict(
            _valid({"risk_low_roi_threshold": 0.20, "risk_high_roi_threshold": 0.10})
        )


def test_roi_high_over_one_raises() -> None:
    with pytest.raises(ValueError, match="ROI thresholds"):
        ImportCostProfile.from_dict(
            _valid({"risk_low_roi_threshold": 0.05, "risk_high_roi_threshold": 1.5})
        )


def test_profit_low_not_below_high_raises() -> None:
    with pytest.raises(ValueError, match="profit thresholds"):
        ImportCostProfile.from_dict(
            _valid(
                {"risk_low_profit_threshold": 5000.0, "risk_high_profit_threshold": 4000.0}
            )
        )


def test_cost_ratio_high_over_limit_raises() -> None:
    with pytest.raises(ValueError, match="cost_ratio thresholds"):
        ImportCostProfile.from_dict(_valid({"risk_high_cost_ratio_threshold": 4.0}))


def test_constructor_validates_via_post_init() -> None:
    with pytest.raises(ValueError, match="transport_cost"):
        ImportCostProfile(**_all_fields(transport_cost=-5.0))


def test_validate_noop_for_valid_profile() -> None:
    p = ImportCostProfile.from_dict(BASE)
    assert p.validate() is None


# =============================================================================
# Regresión numérica (fixtures fijas calculadas a mano)
# =============================================================================


class _Vehicle:
    """Fixture mínima que cumple VehicleData (solo price importa al analyzer)."""

    def __init__(self, price: float) -> None:
        self.price = price
        self.brand = "BMW"
        self.model = "320d"
        self.year = 2019
        self.mileage = 80000


def test_regression_spain_net_profit_and_total_costs() -> None:
    """Perfil SPAIN, compra 10.000, venta 14.000.

    Cifras a mano desde las constantes actuales:
        fijos  = 1200 + 450 + 90 + 280 + 200 = 2220
        vars   = 1000 (IVA 10%) + 400 (comisión 4%) + 300 (reparación 3%) = 1700
        total  = 10000 + 2220 + 1700 = 13920
        net    = 14000 - 13920 = 80
    """
    a = ProfitAnalyzer().analyze(
        _Vehicle(10000.0), profile_name="SPAIN", estimated_sale_price=14000.0
    )
    assert a.total_cost == pytest.approx(13920.0)
    assert a.net_profit == pytest.approx(80.0, abs=0.01)
    assert a.cost_breakdown.total_fixed_costs == pytest.approx(2220.0)
    assert a.cost_breakdown.total_variable_costs == pytest.approx(1700.0)


def test_regression_portugal_net_profit_and_total_costs() -> None:
    """Perfil PORTUGAL, compra 10.000, venta 15.000.

    Cifras a mano desde las constantes actuales:
        fijos  = 1400 + 550 + 100 + 300 + 220 = 2570
        vars   = 1200 (12%) + 400 (comisión) + 300 (reparación) = 1900
        total  = 10000 + 2570 + 1900 = 14470
        net    = 15000 - 14470 = 530
    """
    a = ProfitAnalyzer().analyze(
        _Vehicle(10000.0), profile_name="PORTUGAL", estimated_sale_price=15000.0
    )
    assert a.total_cost == pytest.approx(14470.0)
    assert a.net_profit == pytest.approx(530.0, abs=0.01)


def test_regression_spain_components_labels_present() -> None:
    """El breakdown expone cada componente con label legible en español."""
    a = ProfitAnalyzer().analyze(
        _Vehicle(10000.0), profile_name="SPAIN", estimated_sale_price=14000.0
    )
    comps = {c["key"]: c for c in a.cost_breakdown.components()}
    assert comps["transport_cost"]["label"] == "Transporte"
    assert comps["registration_cost"]["label"] == "Matriculación"
    assert comps["inspection_cost"]["amount"] == pytest.approx(90.0)
    assert comps["taxes"]["label"] == "Impuestos (sobre compra)"
    assert comps["repair_estimate"]["amount"] == pytest.approx(300.0)
    # as_dict incluye todos los campos del breakdown
    flat = a.cost_breakdown.as_dict()
    assert flat["total_cost"] == pytest.approx(13920.0)
    assert "transport_cost" in flat
