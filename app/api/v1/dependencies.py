"""Dependency Injection for the API v1 layer.

Services are never created inside endpoints. All dependencies are
resolved through this module, making them easily testable and swappable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Import diferido: estos módulos se importan dentro de las factories para
    # evitar ciclos, pero las anotaciones de retorno necesitan el símbolo
    # (ruff F821). Con `from __future__ import annotations` no hay coste en
    # runtime.
    from app.providers.autoscout24_es import AutoScout24EsProvider
    from app.repositories.vehicle_evaluation_repository import (
        VehicleEvaluationRepository,
    )

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database import get_db_session
from app.providers.autoscout24 import AutoScout24Provider
from app.providers.base import VehicleProvider
from app.providers.http_client import ProviderHttpClient
from app.providers.mobile_de import MobileDeProvider
from app.providers.openai_vision import OpenAIVisionProvider
from app.providers.registry import ProviderRegistry
from app.providers.vision_provider import MockVisionProvider
from app.repositories.cached_market_repository import CachedMarketRepository
from app.repositories.inspection_repository import (
    InspectionObservationRepository,
    InspectionPhotoRepository,
    InspectionSessionRepository,
)
from app.repositories.vehicle_repository import VehicleRepository
from app.services.comparable_market_estimator import ComparableMarketEstimator
from app.services.evaluation_engine import EvaluationEngine
from app.services.inspection_service import InspectionService
from app.services.market_estimator import MarketEstimator
from app.services.negotiation_engine import NegotiationEngine
from app.services.opportunity_alert_service import OpportunityAlertService
from app.services.opportunity_finder import OpportunityFinder
from app.services.profit_analyzer import ProfitAnalyzer
from app.services.search_engine import SearchEngineService
from app.services.vehicle_scorer import VehicleScorer
from app.services.vehicle_service import VehicleService
from app.services.vision_service import VisionService

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


def get_evaluation_engine() -> EvaluationEngine:
    """Obtiene el motor de evaluación de vehículos.

    El bloque económico se delega en ProfitAnalyzer con el perfil de
    costes por defecto (settings.default_import_cost_profile).
    """
    return EvaluationEngine(
        profit_analyzer=get_profit_analyzer(),
        import_cost_profile=settings.default_import_cost_profile,
    )


def get_opportunity_finder() -> OpportunityFinder:
    """Obtiene el detector de oportunidades."""
    return OpportunityFinder()


def get_opportunity_alert_service() -> OpportunityAlertService:
    """Obtiene el servicio de alertas de oportunidades (Task C.2)."""
    return OpportunityAlertService()


def get_market_estimator(
    vehicle_service: VehicleService = Depends(get_vehicle_service),
    cached_market_repo: CachedMarketRepository = Depends(get_cached_market_repository),
) -> MarketEstimator:
    """Obtiene el estimador de mercado.

    Actualmente devuelve ComparableMarketEstimator, pero puede cambiarse
    por cualquier implementación del protocolo MarketEstimator sin
    modificar los endpoints.
    """
    from app.providers.registry import ProviderRegistry

    # Registra los providers de comparables DE (mobile_de + autoscout24)
    # siempre, y el fixture ES si enable_es_market_fixture está activo
    # (Task P.1a-bis). Idempotente.
    ProviderRegistry.ensure_default_providers()
    return ComparableMarketEstimator(
        vehicle_service=vehicle_service,
        cached_market_repository=cached_market_repo,
    )


# =============================================================================
# Providers
# =============================================================================


def get_mobile_de_provider() -> MobileDeProvider:
    """Provider mobile.de con cliente HTTP anti-bot unificado (settings-driven).

    El ``ProviderHttpClient`` aplica proxy/cookies/delay desde ``settings``
    (``PROVIDER_HTTP_PROXY`` / ``PROVIDER_HTTP_COOKIES`` /
    ``PROVIDER_HTTP_MIN_DELAY_MS``) de forma centralizada — un solo camino
    de red para todos los providers.
    """
    client = ProviderHttpClient(
        provider_name="mobile_de",
        base_url="https://suchen.mobile.de",
        timeout=settings.provider_http_timeout,
        max_retries=settings.provider_http_max_retries,
    )
    return MobileDeProvider(http_client=client, base_url="https://suchen.mobile.de")


def get_autoscout24_provider() -> AutoScout24Provider:
    """Provider AutoScout24 con cliente HTTP anti-bot unificado (settings-driven).

    El ``ProviderHttpClient`` aplica proxy/cookies/delay desde ``settings``
    (``PROVIDER_HTTP_PROXY`` / ``PROVIDER_HTTP_COOKIES`` /
    ``PROVIDER_HTTP_MIN_DELAY_MS``) de forma centralizada — un solo camino
    de red para todos los providers.
    """
    client = ProviderHttpClient(
        provider_name="autoscout24",
        base_url="https://www.autoscout24.de",
        timeout=settings.provider_http_timeout,
        max_retries=settings.provider_http_max_retries,
    )
    return AutoScout24Provider(http_client=client, base_url="https://www.autoscout24.de")


def get_autoscout24_es_provider() -> AutoScout24EsProvider:
    """Provider AutoScout24 ES con el mismo HTTP client anti-bot (settings)."""
    from app.providers.autoscout24_es import AutoScout24EsProvider

    client = ProviderHttpClient(
        provider_name="autoscout24_es",
        base_url="https://www.autoscout24.es",
        timeout=settings.provider_http_timeout,
        max_retries=settings.provider_http_max_retries,
    )
    return AutoScout24EsProvider(
        http_client=client,
        base_url="https://www.autoscout24.es",
    )


def get_coches_net_provider():
    """Provider Coches.net live (HTTP scraping real)."""
    from app.providers.coches_net import CochesNetProvider

    client = ProviderHttpClient(
        provider_name="coches_net",
        base_url="https://www.coches.net",
        timeout=settings.provider_http_timeout,
        max_retries=settings.provider_http_max_retries,
    )
    return CochesNetProvider(http_client=client, base_url="https://www.coches.net")


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


def get_openai_vision_provider() -> OpenAIVisionProvider:
    """Creates an OpenAIVisionProvider configured from application settings.

    The API key, model, max_tokens, and temperature are read from
    Settings (environment variables or .env file).

    Returns:
        Configured OpenAIVisionProvider instance.
    """
    return OpenAIVisionProvider(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        max_tokens=settings.openai_max_tokens,
        temperature=settings.openai_temperature,
    )


def get_vision_provider():
    """Returns Gemini, OpenAI, or Mock provider depending on configuration.

    Priority: Gemini (GEMINI_API_KEY) > OpenAI (OPENAI_API_KEY) > Mock.
    """
    if settings.gemini_api_key:
        from app.providers.gemini_vision import GeminiVisionProvider
        return GeminiVisionProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            max_tokens=settings.gemini_max_tokens,
            temperature=settings.gemini_temperature,
        )
    if settings.openai_api_key:
        return OpenAIVisionProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            max_tokens=settings.openai_max_tokens,
            temperature=settings.openai_temperature,
        )
    return MockVisionProvider()


def get_vision_service(
    provider=Depends(get_vision_provider),
) -> VisionService:
    """Obtiene el servicio adaptador de vision."""
    return VisionService(provider=provider)


def get_vehicle_evaluation_repository(
    session: AsyncSession = Depends(get_db_session),
) -> VehicleEvaluationRepository:
    """Obtiene el repositorio de evaluaciones de vehículos."""
    from app.repositories.vehicle_evaluation_repository import VehicleEvaluationRepository
    return VehicleEvaluationRepository(session)


def get_inspection_service(
    session_repo: InspectionSessionRepository = Depends(get_inspection_session_repository),
    observation_repo: InspectionObservationRepository = Depends(get_inspection_observation_repository),
    photo_repo: InspectionPhotoRepository = Depends(get_inspection_photo_repository),
    vision_service: VisionService = Depends(get_vision_service),
    evaluation_repo: VehicleEvaluationRepository = Depends(get_vehicle_evaluation_repository),
) -> InspectionService:
    """Obtiene el servicio de orquestación de inspecciones."""
    return InspectionService(
        session_repo=session_repo,
        observation_repo=observation_repo,
        photo_repo=photo_repo,
        vision_service=vision_service,
        evaluation_repo=evaluation_repo,
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
        import_cost_profile=settings.default_import_cost_profile,
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
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider_name}' not found. "
            f"Available: {ProviderRegistry.list_providers()}",
        ) from exc

