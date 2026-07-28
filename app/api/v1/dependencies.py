"""Dependency Injection for the API v1 layer.

Services are never created inside endpoints. All dependencies are
resolved through this module, making them easily testable and swappable.
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db_session
from app.providers.autoscout24 import AutoScout24Provider
from app.providers.base import VehicleProvider
from app.providers.http_client import ProviderHttpClient
from app.providers.mobile_de import MobileDeProvider
from app.providers.registry import ProviderRegistry
from app.repositories.cached_market_repository import CachedMarketRepository
from app.repositories.inspection_repository import (
    InspectionObservationRepository,
    InspectionPhotoRepository,
    InspectionSessionRepository,
)
from app.repositories.vehicle_repository import VehicleRepository
from app.services.comparable_market_estimator import ComparableMarketEstimator
from app.services.market_estimator import MarketEstimator
from app.services.negotiation_engine import NegotiationEngine
from app.services.opportunity_finder import OpportunityFinder
from app.services.profit_analyzer import ProfitAnalyzer
from app.services.search_engine import SearchEngineService
from app.services.inspection_service import InspectionService
from app.services.vehicle_scorer import VehicleScorer
from app.services.vehicle_service import VehicleService


# =============================================================================
# Repositories
# =============================================================================


def get_vehicle_repository(
    session: AsyncSession = Depends(get_db_session),
) -> VehicleRepository:
    """Obtiene el repositorio de vehículos."""
    return VehicleRepository(session)


def get_cached_market_repository(
    session: AsyncSession = Depends(get_db_session),
) -> CachedMarketRepository:
    """Obtiene el repositorio de datos de mercado cacheados."""
    return CachedMarketRepository(session)


# =============================================================================
# Services de dominio
# =============================================================================


def get_vehicle_service(
    repository: VehicleRepository = Depends(get_vehicle_repository),
) -> VehicleService:
    """Obtiene el servicio de vehículos."""
    return VehicleService(repository)


def get_vehicle_scorer() -> VehicleScorer:
    """Obtiene el motor de puntuación de vehículos."""
    return VehicleScorer()


def get_profit_analyzer() -> ProfitAnalyzer:
    """Obtiene el analizador de rentabilidad."""
    return ProfitAnalyzer()


def get_opportunity_finder() -> OpportunityFinder:
    """Obtiene el detector de oportunidades."""
    return OpportunityFinder()


def get_market_estimator(
    vehicle_service: VehicleService = Depends(get_vehicle_service),
    cached_market_repo: CachedMarketRepository = Depends(get_cached_market_repository),
) -> MarketEstimator:
    """Obtiene el estimador de mercado.

    Actualmente devuelve ComparableMarketEstimator, pero puede cambiarse
    por cualquier implementación del protocolo MarketEstimator sin
    modificar los endpoints.
    """
    return ComparableMarketEstimator(
        vehicle_service=vehicle_service,
        cached_market_repository=cached_market_repo,
    )


# =============================================================================
# Providers
# =============================================================================


def get_http_client() -> ProviderHttpClient:
    """Crea un cliente HTTP compartido para providers.

    Nota: Actualmente ProviderHttpClient requiere provider_name y base_url
    en el constructor. Esta función existe como placeholder para cuando
    se refactorice a un cliente compartido.
    """
    raise NotImplementedError(
        "Use get_mobile_de_provider() or get_autoscout24_provider() directly"
    )


def get_mobile_de_provider() -> MobileDeProvider:
    """Obtiene el provider de mobile.de."""
    return MobileDeProvider(base_url="https://suchen.mobile.de")


def get_autoscout24_provider() -> AutoScout24Provider:
    """Obtiene el provider de AutoScout24."""
    return AutoScout24Provider(base_url="https://www.autoscout24.de")


# =============================================================================
# Inspection dependencies
# =============================================================================


def get_inspection_session_repository(
    session: AsyncSession = Depends(get_db_session),
) -> InspectionSessionRepository:
    """Obtiene el repositorio de sesiones de inspección."""
    return InspectionSessionRepository(session)


def get_inspection_observation_repository(
    session: AsyncSession = Depends(get_db_session),
) -> InspectionObservationRepository:
    """Obtiene el repositorio de observaciones de inspección."""
    return InspectionObservationRepository(session)


def get_inspection_photo_repository(
    session: AsyncSession = Depends(get_db_session),
) -> InspectionPhotoRepository:
    """Obtiene el repositorio de fotos de inspección."""
    return InspectionPhotoRepository(session)


def get_inspection_service(
    session_repo: InspectionSessionRepository = Depends(get_inspection_session_repository),
    observation_repo: InspectionObservationRepository = Depends(get_inspection_observation_repository),
    photo_repo: InspectionPhotoRepository = Depends(get_inspection_photo_repository),
) -> InspectionService:
    """Obtiene el servicio de orquestación de inspecciones."""
    return InspectionService(
        session_repo=session_repo,
        observation_repo=observation_repo,
        photo_repo=photo_repo,
    )


# =============================================================================
# SearchEngineService (facade principal)
# =============================================================================


def get_negotiation_engine() -> NegotiationEngine:
    """Obtiene el motor de estrategia de negociación."""
    return NegotiationEngine()


def get_search_engine_service(
    vehicle_service: VehicleService = Depends(get_vehicle_service),
    mobile_de_provider: MobileDeProvider = Depends(get_mobile_de_provider),
    autoscout24_provider: AutoScout24Provider = Depends(get_autoscout24_provider),
    vehicle_scorer: VehicleScorer = Depends(get_vehicle_scorer),
    market_estimator: MarketEstimator = Depends(get_market_estimator),
    profit_analyzer: ProfitAnalyzer = Depends(get_profit_analyzer),
    opportunity_finder: OpportunityFinder = Depends(get_opportunity_finder),
    negotiation_engine: NegotiationEngine = Depends(get_negotiation_engine),
) -> SearchEngineService:
    """Obtiene el servicio principal de búsqueda con todas las dependencias.

    Este es el punto de entrada único para las búsquedas end-to-end.
    """
    return SearchEngineService(
        vehicle_service=vehicle_service,
        mobile_de_provider=mobile_de_provider,
        autoscout24_provider=autoscout24_provider,
        vehicle_scorer=vehicle_scorer,
        market_estimator=market_estimator,
        profit_analyzer=profit_analyzer,
        opportunity_finder=opportunity_finder,
        negotiation_engine=negotiation_engine,
    )


# =============================================================================
# Provider lookup for vehicle detail endpoint
# =============================================================================


def get_provider(provider_name: str) -> VehicleProvider:
    """Obtiene un provider del registro por nombre.

    Args:
        provider_name: Nombre del provider (ej: 'mobile_de', 'autoscout24').

    Returns:
        Instancia del provider.

    Raises:
        HTTPException 404: Si el provider no existe.
    """
    try:
        return ProviderRegistry.get(provider_name)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider_name}' not found. "
            f"Available: {ProviderRegistry.list_providers()}",
        )

