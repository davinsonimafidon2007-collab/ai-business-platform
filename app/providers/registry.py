from __future__ import annotations

from app.providers.base import VehicleProvider


class ProviderRegistry:
    """Registro central de proveedores de vehículos.

    Permite registrar, obtener y listar providers de forma desacoplada.
    Los providers se identifican por su source_name.
    """

    _providers: dict[str, VehicleProvider] = {}

    @classmethod
    def register(cls, provider: VehicleProvider) -> None:
        """Registra un provider en el registro.

        Args:
            provider: Instancia del provider a registrar.

        Raises:
            ValueError: Si ya existe un provider con el mismo source_name.
        """
        name = provider.source_name
        if name in cls._providers:
            raise ValueError(f"Provider '{name}' is already registered")
        cls._providers[name] = provider

    @classmethod
    def get(cls, name: str) -> VehicleProvider:
        """Obtiene un provider por su nombre.

        Args:
            name: Nombre del provider (ej: 'mobile_de', 'autoscout24').

        Returns:
            Instancia del provider solicitado.

        Raises:
            KeyError: Si no existe un provider con ese nombre.
        """
        if name not in cls._providers:
            raise KeyError(f"Provider '{name}' is not registered. Available: {list(cls._providers.keys())}")
        return cls._providers[name]

    @classmethod
    def list_providers(cls) -> list[str]:
        """Devuelve la lista de nombres de providers registrados."""
        return list(cls._providers.keys())

    @classmethod
    def unregister(cls, name: str) -> None:
        """Elimina un provider del registro.

        Args:
            name: Nombre del provider a eliminar.
        """
        cls._providers.pop(name, None)

    @classmethod
    def clear(cls) -> None:
        """Limpia todos los providers registrados (útil en tests)."""
        cls._providers.clear()

    @classmethod
    def ensure_es_market_fixture(cls, enabled: bool | None = None) -> None:
        """Registra es_market_fixture si enabled y aún no está.

        Idempotente. ``enabled=None`` → lee settings.enable_es_market_fixture.
        """
        if enabled is None:
            from app.core.config import settings

            enabled = bool(getattr(settings, "enable_es_market_fixture", False))
        if not enabled:
            return
        if "es_market_fixture" in cls._providers:
            return
        from app.providers.es_market_fixture import EsMarketFixtureProvider

        cls.register(EsMarketFixtureProvider())

    @classmethod
    def ensure_default_providers(cls) -> None:
        """Registra los providers de búsqueda/comparables usados en runtime.

        Idempotente. No hace HTTP al construir las instancias (el cliente
        HTTP se crea lazy y solo abre conexión en el primer ``search`` real).
        - mobile_de, autoscout24: siempre
        - es_market_fixture: solo si settings.enable_es_market_fixture

        Reutiliza settings-provider_http_* para el cliente anti-bot, igual
        que las dependencias de API (get_mobile_de_provider /
        get_autoscout24_provider).
        """
        if "mobile_de" not in cls._providers:
            from app.core.config import settings
            from app.providers.http_client import ProviderHttpClient
            from app.providers.mobile_de import MobileDeProvider

            client = ProviderHttpClient(
                provider_name="mobile_de",
                base_url="https://suchen.mobile.de",
                timeout=settings.provider_http_timeout,
                max_retries=settings.provider_http_max_retries,
            )
            cls.register(
                MobileDeProvider(
                    http_client=client, base_url="https://suchen.mobile.de"
                )
            )

        if "autoscout24" not in cls._providers:
            from app.core.config import settings
            from app.providers.autoscout24 import AutoScout24Provider
            from app.providers.http_client import ProviderHttpClient

            client = ProviderHttpClient(
                provider_name="autoscout24",
                base_url="https://www.autoscout24.de",
                timeout=settings.provider_http_timeout,
                max_retries=settings.provider_http_max_retries,
            )
            cls.register(
                AutoScout24Provider(
                    http_client=client, base_url="https://www.autoscout24.de"
                )
            )

        # Reutiliza la lógica ya existente (flag + idempotente) para el
        # fixture ES cuando está activo.
        cls.ensure_es_market_fixture()
