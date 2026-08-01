"""ComparableMarketEstimator — Estimador de mercado basado en comparables reales.

Arquitectura de componentes internos:
    - ComparableFilter: filtra vehículos según tolerancias configurables.
    - MarketStatistics: calcula estadísticas (media, mediana, Q1, Q3, IQR, CV, percentil).
    - ConfidenceCalculator: calcula la confianza (0-100) basada en múltiples factores.
    - ComparableMarketEstimator: orquesta el flujo completo con caché.

Mantiene compatibilidad completa con el protocolo ``MarketEstimator``
(``async def estimate(self, vehicle: object) -> MarketEstimation``).
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from app.config.comparable_market import (
    CACHE_TTL_SECONDS,
    CONFIDENCE_COUNT_WEIGHT,
    CONFIDENCE_DISCARDED_WEIGHT,
    CONFIDENCE_DISPERSION_WEIGHT,
    CONFIDENCE_DIVERSITY_WEIGHT,
    CONFIDENCE_FRESHNESS_WEIGHT,
    CONFIDENCE_MAX_COUNT,
    CONFIDENCE_SIMILARITY_WEIGHT,
    MARKET_HASH_MILEAGE_BUCKET,
    MARKET_HASH_YEAR_BUCKET,
    MILEAGE_TOLERANCE_PERCENT,
    OVERRICED_PERCENTILE,
    REQUIRE_SAME_BRAND,
    REQUIRE_SAME_FUEL,
    REQUIRE_SAME_MODEL,
    REQUIRE_SAME_TRANSMISSION,
    UNDERPRICED_PERCENTILE,
    WEIGHT_MILEAGE_SIMILARITY,
    WEIGHT_SAME_BRAND,
    WEIGHT_SAME_FUEL,
    WEIGHT_SAME_MODEL,
    WEIGHT_SAME_TRANSMISSION,
    WEIGHT_YEAR_SIMILARITY,
    YEAR_TOLERANCE,
)
from app.core.logging import get_logger
from app.models.cached_market import CachedMarketData
from app.models.market import MarketEstimation
from app.providers.dto import VehicleSearchResult
from app.providers.registry import ProviderRegistry
from app.repositories.cached_market_repository import CachedMarketRepository
from app.services.vehicle_service import VehicleService

logger = get_logger(__name__)


# =============================================================================
# Data classes internos
# =============================================================================


@dataclass(frozen=True)
class MarketStatistics:
    """Estadísticas calculadas sobre los comparables."""

    count: int
    mean: float
    median: float
    std_dev: float
    min_price: float
    max_price: float
    q1: float
    q3: float
    iqr: float
    coefficient_of_variation: float
    """CV = std_dev / mean (0 = sin dispersión)."""
    percentile_position: float
    """Percentil del precio del vehículo objetivo dentro de los comparables (0-100)."""
    weighted_mean: float
    """Media ponderada por similitud de cada comparable."""
    total_weight: float
    """Suma de pesos de similitud (útil para medir calidad de comparables)."""


@dataclass(frozen=True)
class ComparableVehicle:
    """Un vehículo comparable con su peso de similitud."""

    price: float
    year: int
    mileage: int
    fuel_type: str | None
    transmission: str | None
    source: str
    similarity_weight: float
    """Peso de similitud respecto al vehículo objetivo (0-1)."""


# =============================================================================
# ComparableFilter — Filtra vehículos según tolerancias
# =============================================================================


class ComparableFilter:
    """Filtra vehículos candidatos para determinar si son comparables.

    Aplica las tolerancias configurables: misma marca, mismo modelo,
    ±2 años, ±20% kilometraje, mismo combustible, misma transmisión.
    """

    def __init__(self) -> None:
        self._config = {
            "require_same_brand": REQUIRE_SAME_BRAND,
            "require_same_model": REQUIRE_SAME_MODEL,
            "require_same_fuel": REQUIRE_SAME_FUEL,
            "require_same_transmission": REQUIRE_SAME_TRANSMISSION,
            "year_tolerance": YEAR_TOLERANCE,
            "mileage_tolerance_pct": MILEAGE_TOLERANCE_PERCENT,
        }

    def is_comparable(self, target: Any, candidate: Any) -> bool:
        """Determina si un vehículo candidato es comparable al objetivo."""
        if self._config["require_same_brand"]:
            if self._get_attr(target, "brand") != self._get_attr(candidate, "brand"):
                return False
        if self._config["require_same_model"]:
            if self._get_attr(target, "model") != self._get_attr(candidate, "model"):
                return False
        target_year = self._get_attr(target, "year")
        candidate_year = self._get_attr(candidate, "year")
        if target_year is not None and candidate_year is not None:
            if abs(target_year - candidate_year) > self._config["year_tolerance"]:
                return False
        elif target_year is not None and candidate_year is None:
            return False
        target_mileage = self._get_attr(target, "mileage")
        candidate_mileage = self._get_attr(candidate, "mileage")
        if target_mileage is not None and candidate_mileage is not None and target_mileage > 0:
            tolerance = target_mileage * (self._config["mileage_tolerance_pct"] / 100.0)
            if abs(target_mileage - candidate_mileage) > tolerance:
                return False
        elif target_mileage is not None and candidate_mileage is None:
            return False
        if self._config["require_same_fuel"]:
            target_fuel = self._get_attr(target, "fuel_type")
            candidate_fuel = self._get_attr(candidate, "fuel_type")
            if target_fuel and candidate_fuel:
                if target_fuel.lower() != candidate_fuel.lower():
                    return False
            elif target_fuel and not candidate_fuel:
                return False
        if self._config["require_same_transmission"]:
            target_trans = self._get_attr(target, "transmission")
            candidate_trans = self._get_attr(candidate, "transmission")
            if target_trans and candidate_trans:
                if target_trans.lower() != candidate_trans.lower():
                    return False
            elif target_trans and not candidate_trans:
                return False
        return True

    def compute_similarity_weight(self, target: Any, candidate: Any) -> float:
        """Calcula el peso de similitud entre objetivo y candidato (0-1)."""
        weight = 0.0
        total_possible = (
            WEIGHT_SAME_BRAND + WEIGHT_SAME_MODEL + WEIGHT_YEAR_SIMILARITY
            + WEIGHT_MILEAGE_SIMILARITY + WEIGHT_SAME_FUEL + WEIGHT_SAME_TRANSMISSION
        )
        if self._get_attr(target, "brand") == self._get_attr(candidate, "brand"):
            weight += WEIGHT_SAME_BRAND
        if self._get_attr(target, "model") == self._get_attr(candidate, "model"):
            weight += WEIGHT_SAME_MODEL
        target_year = self._get_attr(target, "year")
        candidate_year = self._get_attr(candidate, "year")
        if target_year is not None and candidate_year is not None:
            year_diff = abs(target_year - candidate_year)
            year_sim = max(0.0, 1.0 - year_diff / (YEAR_TOLERANCE + 1))
            weight += WEIGHT_YEAR_SIMILARITY * year_sim
        target_mileage = self._get_attr(target, "mileage")
        candidate_mileage = self._get_attr(candidate, "mileage")
        if target_mileage is not None and candidate_mileage is not None and target_mileage > 0:
            mileage_ratio = min(target_mileage, candidate_mileage) / max(target_mileage, candidate_mileage)
            weight += WEIGHT_MILEAGE_SIMILARITY * mileage_ratio
        target_fuel = self._get_attr(target, "fuel_type")
        candidate_fuel = self._get_attr(candidate, "fuel_type")
        if target_fuel and candidate_fuel and target_fuel.lower() == candidate_fuel.lower():
            weight += WEIGHT_SAME_FUEL
        target_trans = self._get_attr(target, "transmission")
        candidate_trans = self._get_attr(candidate, "transmission")
        if target_trans and candidate_trans and target_trans.lower() == candidate_trans.lower():
            weight += WEIGHT_SAME_TRANSMISSION
        return weight / total_possible if total_possible > 0 else 0.0

    @staticmethod
    def _get_attr(obj: Any, name: str) -> Any:
        if isinstance(obj, dict):
            return obj.get(name)
        return getattr(obj, name, None)

    def filter_comparables(self, target: Any, candidates: list[Any]) -> list[ComparableVehicle]:
        """Filtra candidatos y devuelve solo los comparables con su peso."""
        comparables: list[ComparableVehicle] = []
        for cand in candidates:
            if not self.is_comparable(target, cand):
                continue
            price = self._get_price(cand)
            if price is None or price <= 0:
                continue
            weight = self.compute_similarity_weight(target, cand)
            comparables.append(
                ComparableVehicle(
                    price=price,
                    year=self._get_attr(cand, "year") or 0,
                    mileage=self._get_attr(cand, "mileage") or 0,
                    fuel_type=self._get_attr(cand, "fuel_type"),
                    transmission=self._get_attr(cand, "transmission"),
                    source=self._get_attr(cand, "source") or "unknown",
                    similarity_weight=weight,
                )
            )
        return comparables

    @staticmethod
    def _get_price(vehicle: Any) -> float | None:
        price = ComparableFilter._get_attr(vehicle, "price")
        return float(price) if price is not None else None


# =============================================================================
# MarketStatistics — Cálculo de estadísticas sobre comparables
# =============================================================================


class MarketStatisticsCalculator:
    """Calcula estadísticas descriptivas y ponderadas sobre una lista de comparables."""

    @staticmethod
    def compute(comparables: list[ComparableVehicle], target_price: float | None) -> MarketStatistics:
        if not comparables:
            return MarketStatistics(
                count=0, mean=0.0, median=0.0, std_dev=0.0,
                min_price=0.0, max_price=0.0, q1=0.0, q3=0.0, iqr=0.0,
                coefficient_of_variation=0.0, percentile_position=50.0,
                weighted_mean=0.0, total_weight=0.0,
            )
        prices = [c.price for c in comparables]
        weights = [c.similarity_weight for c in comparables]
        total_weight = sum(weights)
        mean = statistics.mean(prices)
        median = statistics.median(prices)
        std_dev = statistics.pstdev(prices) if len(prices) > 1 else 0.0
        min_price = min(prices)
        max_price = max(prices)
        sorted_prices = sorted(prices)
        q1 = MarketStatisticsCalculator._percentile(sorted_prices, 25)
        q3 = MarketStatisticsCalculator._percentile(sorted_prices, 75)
        iqr = q3 - q1
        cv = std_dev / mean if mean > 0 else 0.0
        percentile_pos = 50.0
        if target_price is not None and prices:
            count_below = sum(1 for p in prices if p < target_price)
            percentile_pos = (count_below / len(prices)) * 100.0
        weighted_mean = 0.0
        if total_weight > 0:
            weighted_mean = sum(p * w for p, w in zip(prices, weights)) / total_weight
        return MarketStatistics(
            count=len(prices), mean=mean, median=median, std_dev=std_dev,
            min_price=min_price, max_price=max_price, q1=q1, q3=q3, iqr=iqr,
            coefficient_of_variation=cv, percentile_position=percentile_pos,
            weighted_mean=weighted_mean, total_weight=total_weight,
        )

    @staticmethod
    def _percentile(sorted_data: list[float], percentile: float) -> float:
        """Calcula un percentil sobre datos ordenados (interpolación lineal)."""
        n = len(sorted_data)
        if n == 0:
            return 0.0
        if n == 1:
            return sorted_data[0]
        k = (percentile / 100.0) * (n - 1)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_data[int(k)]
        d0 = sorted_data[int(f)] * (c - k)
        d1 = sorted_data[int(c)] * (k - f)
        return d0 + d1


# =============================================================================
# ConfidenceCalculator — Cálculo de confianza (0-100)
# =============================================================================


class ConfidenceCalculator:
    """Calcula el nivel de confianza de una estimación de mercado (0-100)."""

    def __init__(self) -> None:
        self._config = {
            "max_count": CONFIDENCE_MAX_COUNT,
            "count_weight": CONFIDENCE_COUNT_WEIGHT,
            "dispersion_weight": CONFIDENCE_DISPERSION_WEIGHT,
            "diversity_weight": CONFIDENCE_DIVERSITY_WEIGHT,
            "freshness_weight": CONFIDENCE_FRESHNESS_WEIGHT,
            "similarity_weight": CONFIDENCE_SIMILARITY_WEIGHT,
            "discarded_weight": CONFIDENCE_DISCARDED_WEIGHT,
        }
        self._total_weight = (
            CONFIDENCE_COUNT_WEIGHT + CONFIDENCE_DISPERSION_WEIGHT
            + CONFIDENCE_DIVERSITY_WEIGHT + CONFIDENCE_FRESHNESS_WEIGHT
            + CONFIDENCE_SIMILARITY_WEIGHT + CONFIDENCE_DISCARDED_WEIGHT
        )

    def compute(
        self,
        stats: MarketStatistics,
        provider_sources: set[str],
        freshness_hours: float | None = None,
        discarded_ratio: float = 0.0,
    ) -> float:
        if stats.count == 0:
            return 0.0
        count_score = min(1.0, stats.count / self._config["max_count"])
        cv = stats.coefficient_of_variation
        dispersion_score = max(0.0, min(1.0, 1.0 - (cv / 0.5)))
        num_providers = len(provider_sources)
        diversity_score = min(1.0, num_providers / 3.0)
        freshness_score = 1.0
        if freshness_hours is not None:
            freshness_score = max(0.0, 1.0 - freshness_hours / 168.0)
        if stats.total_weight > 0 and stats.count > 0:
            avg_similarity = stats.total_weight / stats.count
        else:
            avg_similarity = 0.0
        similarity_score = min(1.0, avg_similarity * 2.0)
        discarded_score = max(0.0, 1.0 - discarded_ratio)
        confidence = (
            count_score * self._config["count_weight"]
            + dispersion_score * self._config["dispersion_weight"]
            + diversity_score * self._config["diversity_weight"]
            + freshness_score * self._config["freshness_weight"]
            + similarity_score * self._config["similarity_weight"]
            + discarded_score * self._config["discarded_weight"]
        )
        normalized = (confidence / self._total_weight) * 100.0 if self._total_weight > 0 else 0.0
        return round(max(0.0, min(100.0, normalized)), 1)


# =============================================================================
# ComparableMarketEstimator — Orquestador principal
# =============================================================================


class ComparableMarketEstimator:
    """Estimador de mercado basado en comparables reales.

    Flujo:
        1. Computa un market_hash a partir de los atributos del vehículo.
        2. Busca en caché (CachedMarketRepository) si ya hay datos válidos.
        3. Si no hay caché, busca vehículos comparables usando todos los providers.
        4. Filtra los resultados con ``ComparableFilter``.
        5. Calcula estadísticas con ``MarketStatisticsCalculator``.
        6. Calcula confianza con ``ConfidenceCalculator``.
        7. Determina si está sobre/precio justo/infravalorado.
        8. Almacena en caché y devuelve ``MarketEstimation``.

    Compatible con el protocolo ``MarketEstimator``.
    """

    def __init__(
        self,
        vehicle_service: VehicleService,
        cached_market_repository: CachedMarketRepository,
        provider_registry: type[ProviderRegistry] = ProviderRegistry,
        comparable_filter: ComparableFilter | None = None,
        stats_calculator: MarketStatisticsCalculator | None = None,
        confidence_calculator: ConfidenceCalculator | None = None,
        cache_ttl_seconds: int = CACHE_TTL_SECONDS,
    ) -> None:
        self._vehicle_service = vehicle_service
        self._cached_market_repo = cached_market_repository
        self._provider_registry = provider_registry
        self._filter = comparable_filter or ComparableFilter()
        self._stats = stats_calculator or MarketStatisticsCalculator()
        self._confidence = confidence_calculator or ConfidenceCalculator()
        self._cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self._local_cache: dict[str, MarketEstimation] = {}

    async def estimate(self, vehicle: object) -> MarketEstimation:
        """Estima las condiciones de mercado para un vehículo (corutina).

        Args:
            vehicle: Objeto con atributos VehicleData (brand, model, year, etc.).

        Returns:
            ``MarketEstimation`` con la estimación de mercado.
        """
        market_hash = self._compute_market_hash(vehicle)
        if market_hash in self._local_cache:
            return self._local_cache[market_hash]
        vehicle_id = self._get_external_id(vehicle)
        vehicle_source = self._get_source(vehicle)
        if vehicle_id and vehicle_source:
            cached = await self._cached_market_repo.get_valid(
                external_id=vehicle_id, provider=vehicle_source, market_hash=market_hash,
            )
            if cached is not None:
                estimation = self._from_cached(cached)
                self._local_cache[market_hash] = estimation
                return estimation
        comparables, candidates_count, provider_sources = await self._search_comparables(vehicle)
        return await self._compute_and_cache(
            vehicle=vehicle, market_hash=market_hash,
            comparables=comparables, candidates_count=candidates_count,
            provider_sources=provider_sources, vehicle_id=vehicle_id, vehicle_source=vehicle_source,
        )

    # ------------------------------------------------------------------
    # Búsqueda de comparables
    # ------------------------------------------------------------------

    async def _search_comparables(self, vehicle: Any) -> tuple[list[ComparableVehicle], int, set[str]]:
        all_candidates: list[VehicleSearchResult] = []
        provider_sources: set[str] = set()
        provider_names = self._provider_registry.list_providers()
        for provider_name in provider_names:
            try:
                provider = self._provider_registry.get(provider_name)
            except KeyError:
                continue
            query = self._build_search_query(vehicle, provider_name)
            if not query:
                continue
            try:
                results = await self._vehicle_service.search_from_provider(provider, query)
                all_candidates.extend(results)
                if results:
                    provider_sources.add(provider_name)
            except Exception:
                logger.exception("Error al buscar comparables en provider %s", provider_name)
                continue
        total_candidates = len(all_candidates)
        comparables = self._filter.filter_comparables(vehicle, all_candidates)
        return comparables, total_candidates, provider_sources

    def _build_search_query(self, vehicle: Any, provider_name: str) -> str | None:
        brand = self._get_attr(vehicle, "brand")
        model = self._get_attr(vehicle, "model")
        if not brand:
            return None
        if model:
            return f"{brand} {model}"
        return brand

    # ------------------------------------------------------------------
    # Cómputo y caché
    # ------------------------------------------------------------------

    async def _compute_and_cache(
        self, vehicle: Any, market_hash: str,
        comparables: list[ComparableVehicle], candidates_count: int,
        provider_sources: set[str], vehicle_id: str | None, vehicle_source: str | None,
    ) -> MarketEstimation:
        target_price = self._get_price(vehicle)
        stats = self._stats.compute(comparables, target_price)
        discarded_ratio = 0.0
        if candidates_count > 0:
            discarded_ratio = 1.0 - (stats.count / candidates_count)
        confidence = self._confidence.compute(
            stats=stats, provider_sources=provider_sources,
            freshness_hours=None, discarded_ratio=discarded_ratio,
        )
        price_detection = self._detect_pricing(stats, target_price)
        market_price = stats.weighted_mean if stats.count > 0 else (target_price or 0.0)
        estimation = MarketEstimation(
            market_price=round(market_price, 2), confidence=confidence,
            supply_level=50.0, demand_level=50.0, market_trend="stable",
            comparable_count=stats.count,
            notes=[
                f"mean={stats.mean:.0f}", f"median={stats.median:.0f}",
                f"std_dev={stats.std_dev:.0f}", f"q1={stats.q1:.0f}",
                f"q3={stats.q3:.0f}", f"cv={stats.coefficient_of_variation:.3f}",
                f"percentile={stats.percentile_position:.1f}%",
                f"weighted_mean={stats.weighted_mean:.0f}",
                f"discarded_ratio={discarded_ratio:.2f}",
                f"providers={','.join(sorted(provider_sources))}",
                f"pricing={price_detection}",
            ],
        )
        self._local_cache[market_hash] = estimation
        if vehicle_id and vehicle_source:
            # Guardado asíncrono directo en el mismo event loop,
            # sin bridges sync->async.
            await self._save_to_cache(
                vehicle_id=vehicle_id, vehicle_source=vehicle_source,
                market_hash=market_hash, estimation=estimation,
            )
        return estimation

    async def _save_to_cache(
        self, vehicle_id: str, vehicle_source: str, market_hash: str, estimation: MarketEstimation,
    ) -> None:
        now = datetime.now(timezone.utc)
        cached = CachedMarketData(
            external_id=vehicle_id, provider=vehicle_source, market_hash=market_hash,
            market_price=estimation.market_price, confidence=estimation.confidence,
            supply_level=estimation.supply_level, demand_level=estimation.demand_level,
            market_trend=estimation.market_trend, comparable_count=estimation.comparable_count,
            notes=json.dumps(estimation.notes), expires_at=now + self._cache_ttl,
        )
        try:
            await self._cached_market_repo.save(cached)
        except Exception:
            logger.warning(
                "No se pudo guardar la estimación de mercado en caché "
                "(external_id=%s, provider=%s)",
                vehicle_id, vehicle_source, exc_info=True,
            )

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_market_hash(vehicle: Any) -> str:
        brand = (ComparableMarketEstimator._get_attr(vehicle, "brand") or "").lower().strip()
        model = (ComparableMarketEstimator._get_attr(vehicle, "model") or "").lower().strip()
        fuel = (ComparableMarketEstimator._get_attr(vehicle, "fuel_type") or "").lower().strip()
        transmission = (ComparableMarketEstimator._get_attr(vehicle, "transmission") or "").lower().strip()
        year = ComparableMarketEstimator._get_attr(vehicle, "year")
        year_bucket = (year // MARKET_HASH_YEAR_BUCKET) * MARKET_HASH_YEAR_BUCKET if year is not None else 0
        mileage = ComparableMarketEstimator._get_attr(vehicle, "mileage")
        mileage_bucket = (mileage // MARKET_HASH_MILEAGE_BUCKET) * MARKET_HASH_MILEAGE_BUCKET if mileage is not None else 0
        raw = f"{brand}|{model}|{year_bucket}|{mileage_bucket}|{fuel}|{transmission}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @staticmethod
    def _detect_pricing(stats: MarketStatistics, target_price: float | None) -> str:
        if target_price is None or stats.count == 0:
            return "fair"
        percentile = stats.percentile_position
        if percentile >= OVERRICED_PERCENTILE:
            return "overpriced"
        elif percentile <= UNDERPRICED_PERCENTILE:
            return "underpriced"
        else:
            return "fair"

    @staticmethod
    def _from_cached(cached: CachedMarketData) -> MarketEstimation:
        notes: list[str] = []
        if cached.notes:
            try:
                notes = json.loads(cached.notes)
            except (json.JSONDecodeError, TypeError):
                notes = [cached.notes] if cached.notes else []
        return MarketEstimation(
            market_price=cached.market_price or 0.0, confidence=cached.confidence or 0.0,
            supply_level=cached.supply_level or 50.0, demand_level=cached.demand_level or 50.0,
            market_trend=cached.market_trend or "stable", comparable_count=cached.comparable_count or 0,
            notes=notes,
        )

    @staticmethod
    def _get_attr(obj: Any, name: str) -> Any:
        if isinstance(obj, dict):
            return obj.get(name)
        return getattr(obj, name, None)

    @staticmethod
    def _get_external_id(vehicle: Any) -> str | None:
        return ComparableMarketEstimator._get_attr(vehicle, "external_id")

    @staticmethod
    def _get_source(vehicle: Any) -> str | None:
        return ComparableMarketEstimator._get_attr(vehicle, "source")

    @staticmethod
    def _get_price(vehicle: Any) -> float | None:
        price = ComparableMarketEstimator._get_attr(vehicle, "price")
        return float(price) if price is not None else None

