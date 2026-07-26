from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.models.vehicle import Vehicle
from app.providers.base import VehicleProvider
from app.providers.dto import VehicleSearchResult
from app.repositories.vehicle_repository import VehicleRepository


class VehicleService:
    def __init__(self, repository: VehicleRepository) -> None:
        self.repository = repository

    async def create_vehicle(self, data: dict) -> Vehicle:
        vehicle = Vehicle(**data)
        return await self.repository.create(vehicle)

    async def get_vehicle(self, vehicle_id: str | UUID) -> Vehicle | None:
        return await self.repository.get_by_id(vehicle_id)

    async def get_vehicle_by_external_id(self, source: str, external_id: str) -> Vehicle | None:
        return await self.repository.get_by_external_id(source, external_id)

    async def list_vehicles(self, skip: int = 0, limit: int = 100) -> list[Vehicle]:
        return await self.repository.list_all(skip=skip, limit=limit)

    async def update_vehicle(self, vehicle: Vehicle, data: dict) -> Vehicle:
        for key, value in data.items():
            if value is not None:
                setattr(vehicle, key, value)
        vehicle.updated_at = datetime.now(timezone.utc)
        return await self.repository.update(vehicle)

    async def delete_vehicle(self, vehicle: Vehicle) -> None:
        await self.repository.delete(vehicle)

    # ------------------------------------------------------------------
    # Provider integration
    # ------------------------------------------------------------------

    async def search_from_provider(self, provider: VehicleProvider, query: str, **kwargs: object) -> list[VehicleSearchResult]:
        """Busca vehículos usando un provider y devuelve los DTOs.

        El servicio no conoce la implementación concreta del provider,
        solo usa la interfaz VehicleProvider.

        Args:
            provider: Provider a utilizar (ej: MobileDeProvider).
            query: Término de búsqueda.
            **kwargs: Filtros adicionales.

        Returns:
            Lista de resultados normalizados como VehicleSearchResult.
        """
        return await provider.search(query, **kwargs)

    async def import_from_provider_result(self, result: VehicleSearchResult) -> Vehicle:
        """Convierte un DTO de provider en un modelo Vehicle y lo persiste.

        Si el vehículo ya existe (mismo source + external_id), lo actualiza.
        Si no existe, lo crea.

        Args:
            result: DTO con los datos del vehículo desde el provider.

        Returns:
            El modelo Vehicle creado o actualizado.
        """
        existing = await self.repository.get_by_external_id(result.source, result.external_id)
        if existing is not None:
            return await self._update_from_dto(existing, result)

        data = {
            "source": result.source,
            "external_id": result.external_id,
            "url": result.url,
            "brand": result.brand or "",
            "model": result.model or "",
            "category": result.category,
            "version": result.version,
            "year": result.year,
            "mileage": result.mileage,
            "fuel_type": result.fuel_type,
            "transmission": result.transmission,
            "power_hp": result.power_hp,
            "displacement_cc": result.displacement_cc,
            "doors": result.doors,
            "color": result.color,
            "emissions": result.emissions,
            "location": result.location,
            "seller_type": result.seller_type,
            "first_registration": result.first_registration,
            "price": result.price,
            "currency": result.currency,
            "vin": result.vin,
            "description": result.description,
            "images": ",".join(result.images) if result.images else None,
            "equipment": ",".join(result.equipment) if result.equipment else None,
        }
        vehicle = Vehicle(**data)
        return await self.repository.create(vehicle)

    async def _update_from_dto(self, vehicle: Vehicle, result: VehicleSearchResult) -> Vehicle:
        """Actualiza un vehículo existente con datos de un DTO de provider."""
        update_data: dict[str, object] = {}
        if result.url is not None:
            update_data["url"] = result.url
        if result.brand is not None:
            update_data["brand"] = result.brand
        if result.model is not None:
            update_data["model"] = result.model
        if result.category is not None:
            update_data["category"] = result.category
        if result.version is not None:
            update_data["version"] = result.version
        if result.year is not None:
            update_data["year"] = result.year
        if result.mileage is not None:
            update_data["mileage"] = result.mileage
        if result.fuel_type is not None:
            update_data["fuel_type"] = result.fuel_type
        if result.transmission is not None:
            update_data["transmission"] = result.transmission
        if result.power_hp is not None:
            update_data["power_hp"] = result.power_hp
        if result.displacement_cc is not None:
            update_data["displacement_cc"] = result.displacement_cc
        if result.doors is not None:
            update_data["doors"] = result.doors
        if result.color is not None:
            update_data["color"] = result.color
        if result.emissions is not None:
            update_data["emissions"] = result.emissions
        if result.location is not None:
            update_data["location"] = result.location
        if result.seller_type is not None:
            update_data["seller_type"] = result.seller_type
        if result.first_registration is not None:
            update_data["first_registration"] = result.first_registration
        if result.price is not None:
            update_data["price"] = result.price
        if result.currency is not None:
            update_data["currency"] = result.currency
        if result.vin is not None:
            update_data["vin"] = result.vin
        if result.description is not None:
            update_data["description"] = result.description
        if result.images:
            update_data["images"] = ",".join(result.images)
        if result.equipment:
            update_data["equipment"] = ",".join(result.equipment)

        for key, value in update_data.items():
            setattr(vehicle, key, value)
        vehicle.updated_at = datetime.now(timezone.utc)
        return await self.repository.update(vehicle)
