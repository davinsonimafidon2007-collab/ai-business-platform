from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Business Platform API"
    app_description: str = "API for the AI Business Platform."
    app_version: str = "0.1.0"
    environment: Literal["development", "production", "test"] = "development"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_business_platform"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://localhost:8080"

    @property
    def database_url_for_environment(self) -> str:
        return self.database_url

    @property
    def cors_origins_list(self) -> list[str]:
        """Convierte la cadena de origins en una lista."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()