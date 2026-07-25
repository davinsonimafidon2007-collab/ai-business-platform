from __future__ import annotations

from abc import ABC, abstractmethod

from app.providers.dto import VehicleDetail, VehicleSearchResult
from app.providers.http_client import ProviderHttpClient


class VehicleProvider(ABC):
    """Interfaz abstracta que deben implementar todos los providers de vehículos.

    Cualquier nuevo proveedor (mobile.de, AutoScout24, eBay, etc.) debe
    heredar de esta clase e implementar sus métodos abstractos.
    """

    def __init__(
        self,
        http_client: ProviderHttpClient | None = None,
        base_url: str | None = None,
    ) -> None:
        """Inicializa el provider con un cliente HTTP opcional.

        Args:
            http_client: Cliente HTTP reutilizable. Si no se proporciona, se crea uno nuevo.
            base_url: URL base del proveedor (solo usado si no se proporciona http_client).
        """
        self._http_client = http_client
        self._base_url = base_url

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Nombre único del provider (ej: 'mobile_de', 'autoscout24')."""
        ...

    @abstractmethod
    async def search(self, query: str, **kwargs: object) -> list[VehicleSearchResult]:
        """Busca vehículos en el provider según un criterio de búsqueda.

        Args:
            query: Término de búsqueda (ej: 'BMW X5 2020').
            **kwargs: Filtros adicionales específicos del provider.

        Returns:
            Lista de resultados normalizados como VehicleSearchResult.
        """
        ...

    @abstractmethod
    async def get_vehicle(self, external_id: str) -> VehicleDetail:
        """Obtiene la información detallada de un vehículo por su ID externo.

        Args:
            external_id: Identificador del vehículo en el provider.

        Returns:
            VehicleDetail con la información completa del vehículo.
        """
        ...

    @abstractmethod
    def normalize_vehicle(self, raw_data: dict) -> VehicleSearchResult | VehicleDetail:
        """Convierte los datos crudos del provider a un DTO normalizado.

        Args:
            raw_data: Datos en bruto obtenidos del provider.

        Returns:
            DTO normalizado (VehicleSearchResult o VehicleDetail).
        """
        ...

    async def _get_client(self) -> ProviderHttpClient:
        """Obtiene el cliente HTTP, creándolo si es necesario."""
        if self._http_client is None:
            self._http_client = ProviderHttpClient(
                provider_name=self.source_name,
                base_url=self._base_url,
            )
        return self._http_client

    async def close(self) -> None:
        """Cierra el cliente HTTP si fue creado por el provider."""
        if self._http_client is not None:
            await self._http_client.close()

    async def __aenter__(self) -> VehicleProvider:
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        await self.close()
