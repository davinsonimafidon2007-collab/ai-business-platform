from __future__ import annotations

import pytest

from app.providers.registry import ProviderRegistry


@pytest.fixture(autouse=True)
def clear_registry() -> None:
    ProviderRegistry.clear()


def test_default_providers_registered() -> None:
    """ensure_default_providers registra las fuentes principales por defecto.

    TASK 4 (AUD-005): con la config por defecto (perfil SPAIN y
    enable_coches_net=True) la fuente española es el scraper REAL de
    coches.net, no su fixture.
    """
    ProviderRegistry.ensure_default_providers()

    providers = ProviderRegistry.list_providers()
    assert "autoscout24" in providers
    assert "es_market_fixture" in providers
    assert "coches_net" in providers
    assert "coches_net_fixture" not in providers


def test_offline_mode_falls_back_to_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    """Desactivando el provider real se recupera el modo offline con fixture."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "enable_coches_net", False)
    ProviderRegistry.ensure_default_providers()

    providers = ProviderRegistry.list_providers()
    assert "coches_net" not in providers
    assert "coches_net_fixture" in providers
