from __future__ import annotations

import logging

import pytest

from app.providers.registry import ProviderRegistry


@pytest.fixture(autouse=True)
def clear_registry() -> None:
    ProviderRegistry.clear()


def test_default_providers_registered() -> None:
    """ensure_default_providers registra las fuentes principales por defecto."""
    ProviderRegistry.ensure_default_providers()

    providers = ProviderRegistry.list_providers()
    assert "autoscout24" in providers
    assert "es_market_fixture" in providers
    assert "coches_net_fixture" in providers
