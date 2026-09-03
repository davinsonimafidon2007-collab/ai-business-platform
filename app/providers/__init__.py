from app.providers.autoscout24 import AutoScout24Provider
from app.providers.base import VehicleProvider
from app.providers.coches_net import CochesNetProvider
from app.providers.coches_net_html import CochesNetHtmlFixtureProvider
from app.providers.dto import VehicleDetail, VehicleSearchResult
from app.providers.exceptions import (
    ProviderAuthenticationError,
    ProviderConnectionError,
    ProviderError,
    ProviderMaxRetriesExceededError,
    ProviderNotFoundError,
    ProviderParsingError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from app.providers.gemini_vision import GeminiVisionProvider
from app.providers.http_client import ProviderHttpClient
from app.providers.mobile_de import MobileDeProvider
from app.providers.mobile_de_playwright import MobileDePlaywrightProvider
from app.providers.openai_vision import OpenAIVisionProvider, VisionProviderError
from app.providers.registry import ProviderRegistry
from app.providers.vision_provider import MockVisionProvider, VisionProvider

__all__ = [
    "VehicleProvider",
    "VehicleSearchResult",
    "VehicleDetail",
    "ProviderRegistry",
    "MobileDeProvider",
    "MobileDePlaywrightProvider",
    "AutoScout24Provider",
    "CochesNetProvider",
    "ProviderHttpClient",
    "ProviderError",
    "ProviderConnectionError",
    "ProviderTimeoutError",
    "ProviderRateLimitError",
    "ProviderAuthenticationError",
    "ProviderNotFoundError",
    "ProviderParsingError",
    "ProviderMaxRetriesExceededError",
    "MockVisionProvider",
    "VisionProvider",
    "GeminiVisionProvider",
    "OpenAIVisionProvider",
    "VisionProviderError",
    "CochesNetHtmlFixtureProvider",
]

