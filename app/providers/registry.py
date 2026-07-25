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