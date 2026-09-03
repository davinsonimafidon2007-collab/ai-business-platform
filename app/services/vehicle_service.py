from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from app.models.vehicle import Vehicle
from app.normalization.pipeline import NormalizationPipeline, VehicleNormalizer
from app.normalization.schema import NormalizedVehicle
from app.providers.base import VehicleProvider
from app.providers.dto import VehicleDetail, VehicleSearchResult
from app.repositories.vehicle_repository import VehicleRepository


class VehicleService:
    def __init__(
        self,
        repository: VehicleRepository,
        exchange_rates: dict[str, Decimal] | None = None,
        enable_normalization: bool = True,
        min_quality_score: float = 0.3,
    ) -> None:
        self.repository = repository
        self.exchange_rates = exchange_rates
        self.enable_normalization = enable_normalization
        self.min_quality_score = min_quality_score

        self._pipeline = NormalizationPipeline(
            repository=repository,
            exchange_rates=exchange_rates,
            enable_deduplication=True,
            enable_corrupt_detection=True,
            min_quality_score=min_quality_score,
        )
        self._normalizer = VehicleNormalizer(
            exchange_rates=exchange_rates,
            enable_corrupt_detection=True,
        )

    async def create_vehicle(self, data: dict) -> Vehicle:
        vehicle = Vehicle(**data)
        return await self.repository.create(vehicle)

    async def get_vehicle(self, vehicle_id: str | UUID) -> Vehicle | None:
        return await self.repository.get_by_id(vehicle_id)

    async def get_vehicle_by_external_id(
        self,
        source: str,
        external_id: str,
        user_id: str | None = None,
    ) -> Vehicle | None:
        return await self.repository.get_by_external_id(source, external_id, user_id)

    async def list_vehicles_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Vehicle]:
        return await self.repository.list_by_user(user_id, skip=skip, limit=limit)

    async def update_vehicle(self, vehicle: Vehicle, data: dict) -> Vehicle:
        for key, value in data.items():
            if value is not None:
                setattr(vehicle, key, value)
        vehicle.updated_at = datetime.now(UTC)
        return await self.repository.update(vehicle)

    async def delete_vehicle(self, vehicle: Vehicle) -> None:
        await self.repository.delete(vehicle)

    # ------------------------------------------------------------------
    # Provider integration with normalization
    # ------------------------------------------------------------------

    async def search_from_provider(
        self,
        provider: VehicleProvider,
        query: str,
        **kwargs: object,
    ) -> list[VehicleSearchResult]:
        """Busca vehículos usando un provider y devuelve los DTOs."""
        return await provider.search(query, **kwargs)

    async def search_and_import(
        self,
        provider: VehicleProvider,
        query: str,
        user_id: str,
        **kwargs: object,
    ) -> list[Vehicle]:
        """Busca en un provider y importa resultados con normalización completa."""
        results = await self.search_from_provider(provider, query, **kwargs)
        return await self.import_from_provider_results(results, user_id)

    async def import_from_provider_result(
        self,
        result: VehicleSearchResult | VehicleDetail,
        user_id: str,
    ) -> Vehicle | None:
        """Importa un resultado de provider con normalización completa.

        Returns None if vehicle is rejected due to low quality or corruption.
        """
        if self.enable_normalization:
            return await self._pipeline.process_single(result, user_id)

        # Legacy path (backwards compatible)
        return await self._legacy_import(result, user_id)

    async def import_from_provider_results(
        self,
        results: list[VehicleSearchResult | VehicleDetail],
        user_id: str,
    ) -> list[Vehicle]:
        """Importa múltiples resultados con normalización y deduplicación."""
        if self.enable_normalization:
            return await self._pipeline.process_provider_results(results, user_id)

        # Legacy path
        saved: list[Vehicle] = []
        for result in results:
            vehicle = await self._legacy_import(result, user_id)
            if vehicle:
                saved.append(vehicle)
        return saved

    async def _legacy_import(
        self,
        result: VehicleSearchResult | VehicleDetail,
        user_id: str,
    ) -> Vehicle:
        """Legacy import without normalization (for backwards compatibility)."""
        existing = await self.repository.get_by_external_id(
            result.source, result.external_id, user_id
        )
        if existing is not None:
            return await self._update_from_dto(existing, result)

        data = {
            "user_id": user_id,
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
            "doors": getattr(result, "doors", None),
            "color": getattr(result, "color", None),
            "emissions": getattr(result, "emissions", None),
            "location": result.location,
            "seller_type": result.seller_type,
            "first_registration": result.first_registration,
            "price": result.price,
            "currency": result.currency,
            "vin": result.vin,
            "description": result.description,
            "images": list(result.images) if result.images else None,
            "equipment": ",".join(result.equipment) if result.equipment else None,
        }
        vehicle = Vehicle(**data)
        return await self.repository.create(vehicle)

    async def _update_from_dto(
        self,
        vehicle: Vehicle,
        result: VehicleSearchResult | VehicleDetail,
    ) -> Vehicle:
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
        if getattr(result, "doors", None) is not None:
            update_data["doors"] = result.doors
        if getattr(result, "color", None) is not None:
            update_data["color"] = result.color
        if getattr(result, "emissions", None) is not None:
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
            update_data["images"] = list(result.images)
        if result.equipment:
            update_data["equipment"] = ",".join(result.equipment)

        for key, value in update_data.items():
            setattr(vehicle, key, value)
        vehicle.updated_at = datetime.now(UTC)
        return await self.repository.update(vehicle)

    # ------------------------------------------------------------------
    # Normalization utilities (for external use)
    # ------------------------------------------------------------------

    def normalize_dto(
        self,
        dto: VehicleSearchResult | VehicleDetail,
    ) -> NormalizedVehicle:
        """Normalize a DTO without persisting (for analysis/testing)."""
        return self._normalizer.normalize(dto)

    def normalize_batch(
        self,
        dtos: list[VehicleSearchResult | VehicleDetail],
        deduplicate: bool = True,
    ) -> list[NormalizedVehicle]:
        """Normalize a batch of DTOs without persisting."""
        return self._normalizer.normalize_batch(dtos, deduplicate=deduplicate)

    def to_sqlalchemy_model(
        self,
        normalized: NormalizedVehicle,
        user_id: str,
    ) -> Vehicle:
        """Convert NormalizedVehicle to SQLAlchemy Vehicle model."""
        return self._normalizer.to_sqlalchemy_model(normalized, user_id)


__all__ = ["VehicleService"]