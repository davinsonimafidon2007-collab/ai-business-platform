"""Tests del wiring del perfil de costes de importación por defecto (Task B.2)."""

from __future__ import annotations

from app.config.import_costs import get_profile
from app.core.config import settings


def test_default_import_cost_profile_is_spain() -> None:
    name = getattr(settings, "default_import_cost_profile", "SPAIN")
    assert name == "SPAIN"


def test_default_profile_resolves_to_spain_costs() -> None:
    name = getattr(settings, "default_import_cost_profile", "SPAIN")
    p = get_profile(name)
    assert p.transport_cost == get_profile("SPAIN").transport_cost
    assert p.registration_cost == get_profile("SPAIN").registration_cost


def test_es_alias_equals_spain() -> None:
    es = get_profile("ES")
    spain = get_profile("SPAIN")
    assert es.transport_cost == spain.transport_cost
    assert es.registration_cost == spain.registration_cost
    assert es.tax_rate == spain.tax_rate