import pytest

from app.providers.base import VehicleProvider
from app.providers.dto import VehicleDetail, VehicleSearchResult
from app.providers.registry import ProviderRegistry


class FakeProvider(VehicleProvider):
    """Provider ficticio para los tests."""

    @property
    def source_name(self) -> str:
        return "fake_provider"

    def _find_listing_nodes(self, soup: object) -> list[object]:
        return []

    async def search(self, query: str, **kwargs: object) -> list[VehicleSearchResult]:
        return []

    async def get_vehicle(self, external_id: str) -> VehicleDetail:
        return VehicleDetail(source="fake_provider", external_id=external_id)

    def normalize_vehicle(self, raw_data: dict) -> VehicleSearchResult | VehicleDetail:
        return VehicleSearchResult(source="fake_provider", external_id="fake-001")


class AnotherFakeProvider(VehicleProvider):
    """Otro provider ficticio para los tests."""

    @property
    def source_name(self) -> str:
        return "another_provider"

    def _find_listing_nodes(self, soup: object) -> list[object]:
        return []

    async def search(self, query: str, **kwargs: object) -> list[VehicleSearchResult]:
        return []

    async def get_vehicle(self, external_id: str) -> VehicleDetail:
        return VehicleDetail(source="another_provider", external_id=external_id)

    def normalize_vehicle(self, raw_data: dict) -> VehicleSearchResult | VehicleDetail:
        return VehicleSearchResult(source="another_provider", external_id="another-001")


@pytest.fixture(autouse=True)
def clear_registry() -> None:
    """Limpia el registro antes de cada test."""
    ProviderRegistry.clear()


def test_register_and_get_provider() -> None:
    provider = FakeProvider()
    ProviderRegistry.register(provider)

    retrieved = ProviderRegistry.get("fake_provider")
    assert retrieved is provider
    assert retrieved.source_name == "fake_provider"


def test_register_duplicate_raises_error() -> None:
    ProviderRegistry.register(FakeProvider())

    with pytest.raises(ValueError, match="already registered"):
        ProviderRegistry.register(FakeProvider())


def test_get_unregistered_provider_raises_error() -> None:
    with pytest.raises(KeyError, match="not registered"):
        ProviderRegistry.get("non_existent")


def test_list_providers() -> None:
    ProviderRegistry.register(FakeProvider())
    ProviderRegistry.register(AnotherFakeProvider())

    providers = ProviderRegistry.list_providers()
    assert "fake_provider" in providers
    assert "another_provider" in providers
    assert len(providers) == 2


def test_unregister_provider() -> None:
    ProviderRegistry.register(FakeProvider())
    assert len(ProviderRegistry.list_providers()) == 1

    ProviderRegistry.unregister("fake_provider")
    assert len(ProviderRegistry.list_providers()) == 0


def test_clear_registry() -> None:
    ProviderRegistry.register(FakeProvider())
    ProviderRegistry.register(AnotherFakeProvider())
    assert len(ProviderRegistry.list_providers()) == 2

    ProviderRegistry.clear()
    assert len(ProviderRegistry.list_providers()) == 0