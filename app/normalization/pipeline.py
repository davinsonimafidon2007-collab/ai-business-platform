"""Normalization pipeline: Provider DTO → NormalizedVehicle → SQLAlchemy Vehicle."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.models.vehicle import Vehicle
from app.providers.dto import VehicleDetail, VehicleSearchResult
from app.repositories.vehicle_repository import VehicleRepository
from app.normalization.schema import (
    NormalizedVehicle,
    NormalizedEquipment,
    compute_quality_score,
    detect_corrupt_listing,
    deduplicate_vehicles,
    convert_to_eur,
    validate_vin,
)

logger = logging.getLogger(__name__)


class NormalizationPipeline:
    """Pipeline to normalize, validate, deduplicate, and persist vehicles."""

    def __init__(
        self,
        repository: VehicleRepository,
        exchange_rates: dict[str, Decimal] | None = None,
        enable_deduplication: bool = True,
        enable_corrupt_detection: bool = True,
        min_quality_score: float = 0.3,
    ) -> None:
        self.repository = repository
        self.exchange_rates = exchange_rates
        self.enable_deduplication = enable_deduplication
        self.enable_corrupt_detection = enable_corrupt_detection
        self.min_quality_score = min_quality_score

    async def process_provider_results(
        self,
        results: list[VehicleSearchResult | VehicleDetail],
        user_id: str,
    ) -> list[Vehicle]:
        """Process a batch of provider results through the full pipeline."""
        normalized = [self._normalize_dto(r) for r in results]

        if self.enable_deduplication:
            normalized = deduplicate_vehicles(normalized)

        valid_normalized = [v for v in normalized if v.quality_score >= self.min_quality_score]
        rejected = [v for v in normalized if v.quality_score < self.min_quality_score]

        if rejected:
            logger.warning(
                "Rejected %d vehicles below quality threshold %.2f",
                len(rejected),
                self.min_quality_score,
            )
            for v in rejected:
                logger.debug("Rejected: %s %s (score=%.2f, flags=%s)",
                           v.brand, v.model, v.quality_score, v.quality_flags)

        if self.enable_corrupt_detection:
            for v in valid_normalized:
                corrupt_flags = detect_corrupt_listing(v)
                if corrupt_flags:
                    v.quality_flags.extend(corrupt_flags)
                    v.quality_score = max(0.0, v.quality_score - 0.15 * len(corrupt_flags))
                    logger.warning(
                        "Corrupt listing detected: %s %s (flags=%s)",
                        v.brand, v.model, corrupt_flags,
                    )

        saved_vehicles: list[Vehicle] = []
        for norm in valid_normalized:
            vehicle = await self._upsert_vehicle(norm, user_id)
            saved_vehicles.append(vehicle)

        return saved_vehicles

    async def process_single(
        self,
        dto: VehicleSearchResult | VehicleDetail,
        user_id: str,
    ) -> Vehicle | None:
        """Process a single provider result."""
        norm = self._normalize_dto(dto)

        if norm.quality_score < self.min_quality_score:
            logger.warning(
                "Vehicle rejected (quality=%.2f): %s %s",
                norm.quality_score, norm.brand, norm.model,
            )
            return None

        if self.enable_corrupt_detection:
            corrupt_flags = detect_corrupt_listing(norm)
            if corrupt_flags:
                norm.quality_flags.extend(corrupt_flags)
                norm.quality_score = max(0.0, norm.quality_score - 0.15 * len(corrupt_flags))
                if norm.quality_score < self.min_quality_score:
                    logger.warning(
                        "Vehicle rejected after corrupt detection: %s %s",
                        norm.brand, norm.model,
                    )
                    return None

        return await self._upsert_vehicle(norm, user_id)

    def _normalize_dto(
        self,
        dto: VehicleSearchResult | VehicleDetail,
    ) -> NormalizedVehicle:
        """Convert provider DTO to NormalizedVehicle with full normalization."""
        return NormalizedVehicle.from_provider_dto(dto, self.exchange_rates)

    async def _upsert_vehicle(
        self,
        normalized: NormalizedVehicle,
        user_id: str,
    ) -> Vehicle:
        """Upsert normalized vehicle to database."""
        existing = await self.repository.get_by_external_id(
            normalized.source,
            normalized.external_id,
            user_id,
        )

        data = normalized.to_sqlalchemy_dict()
        data["user_id"] = user_id

        if existing is not None:
            for key, value in data.items():
                if value is not None:
                    setattr(existing, key, value)
            return await self.repository.update(existing)

        vehicle = Vehicle(**data)
        return await self.repository.create(vehicle)

    async def normalize_and_validate(
        self,
        dto: VehicleSearchResult | VehicleDetail,
    ) -> NormalizedVehicle:
        """Normalize and validate without persisting (for testing/analysis)."""
        return self._normalize_dto(dto)


class VehicleNormalizer:
    """Stateless normalizer for use in services without repository dependency."""

    def __init__(
        self,
        exchange_rates: dict[str, Decimal] | None = None,
        enable_corrupt_detection: bool = True,
    ) -> None:
        self.exchange_rates = exchange_rates
        self.enable_corrupt_detection = enable_corrupt_detection

    def normalize(
        self,
        dto: VehicleSearchResult | VehicleDetail,
    ) -> NormalizedVehicle:
        """Normalize a single provider DTO."""
        norm = NormalizedVehicle.from_provider_dto(dto, self.exchange_rates)

        if self.enable_corrupt_detection:
            corrupt_flags = detect_corrupt_listing(norm)
            if corrupt_flags:
                norm.quality_flags.extend(corrupt_flags)
                norm.quality_score = max(0.0, norm.quality_score - 0.15 * len(corrupt_flags))

        return norm

    def normalize_batch(
        self,
        dtos: list[VehicleSearchResult | VehicleDetail],
        deduplicate: bool = True,
    ) -> list[NormalizedVehicle]:
        """Normalize a batch of provider DTOs."""
        normalized = [self.normalize(dto) for dto in dtos]

        if deduplicate:
            normalized = deduplicate_vehicles(normalized)

        return normalized

    def to_sqlalchemy_model(
        self,
        normalized: NormalizedVehicle,
        user_id: str,
    ) -> Vehicle:
        """Convert NormalizedVehicle to SQLAlchemy Vehicle model."""
        data = normalized.to_sqlalchemy_dict()
        data["user_id"] = user_id
        return Vehicle(**data)


def normalize_search_results(
    results: list[VehicleSearchResult],
    user_id: str,
    repository: VehicleRepository | None = None,
    exchange_rates: dict[str, Decimal] | None = None,
) -> list[Vehicle]:
    """Convenience function to normalize and persist search results."""
    normalizer = VehicleNormalizer(exchange_rates=exchange_rates)
    normalized = normalizer.normalize_batch(results)

    if repository is None:
        raise ValueError("Repository required for persistence")

    pipeline = NormalizationPipeline(repository, exchange_rates)
    return pipeline.process_provider_results(results, user_id)


__all__ = [
    "NormalizationPipeline",
    "VehicleNormalizer",
    "normalize_search_results",
]