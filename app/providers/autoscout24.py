from __future__ import annotations

from app.providers.base import VehicleProvider
from app.providers.dto import VehicleDetail, VehicleSearchResult


class AutoScout24Provider(VehicleProvider):
    """Provider para AutoScout24.

    NOTA: El scraping NO está implementado. Esta clase es solo la
    estructura preparada para la futura integración con AutoScout24.
    """

    def __init__(
        self,
        http_client: VehicleProvider | None = None,
        base_url: str = "https://www.autoscout24.de",
    ) -> None:
        """Inicializa el provider de AutoScout24.

        Args:
            http_client: Cliente HTTP reutilizable.
            base_url: URL base de AutoScout24.
        """
        super().__init__(http_client=http_client, base_url=base_url)

    @property
    def source_name(self) -> str:
        return "autoscout24"

    async def search(self, query: str, **kwargs: object) -> list[VehicleSearchResult]:
        """Busca vehículos en AutoScout24.

        Ejemplo de uso:
            async with AutoScout24Provider() as provider:
                results = await provider.search("BMW X5 2020")

        Raises:
            NotImplementedError: El scraping aún no está implementado.
        """
        # Ejemplo de cómo se usaría el cliente HTTP:
        # client = await self._get_client()
        # response = await client.get("/search", params={"q": query})
        # html = response.text
        # ... parsear HTML y normalizar datos ...
        raise NotImplementedError("AutoScout24 scraping is not implemented yet")

    async def get_vehicle(self, external_id: str) -> VehicleDetail:
        """Obtiene un vehículo detallado de AutoScout24.

        Ejemplo de uso:
            async with AutoScout24Provider() as provider:
                detail = await provider.get_vehicle("123456")

        Raises:
            NotImplementedError: El scraping aún no está implementado.
        """
        # Ejemplo de cómo se usaría el cliente HTTP:
        # client = await self._get_client()
        # response = await client.get(f"/vehicle/{external_id}")
        # html = response.text
        # ... parsear HTML y normalizar datos ...
        raise NotImplementedError("AutoScout24 scraping is not implemented yet")

    def normalize_vehicle(self, raw_data: dict) -> VehicleSearchResult | VehicleDetail:
        """Normaliza los datos crudos de AutoScout24 a un DTO.

        Raises:
            NotImplementedError: El scraping aún no está implementado.
        """
        raise NotImplementedError("AutoScout24 scraping is not implemented yet")
