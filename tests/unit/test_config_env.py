from __future__ import annotations

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_loads_from_env():
    """Verifica que Settings carga variables de entorno correctamente."""
    with patch.dict(
        "os.environ",
        {
            "ENVIRONMENT": "production",
            "DATABASE_URL": "postgresql+asyncpg://user:pass@host:5432/db",
            # production exige JWT_SECRET_KEY con >= 32 caracteres (ver Settings.validate_jwt_secret_for_env)
            "JWT_SECRET_KEY": "super-secret-key-that-is-at-least-32-characters-long",
            "JWT_ALGORITHM": "HS512",
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "60",
            "CORS_ORIGINS": "https://example.com,https://admin.example.com",
        },
    ):
        settings = Settings()
        
        assert settings.environment == "production"
        assert settings.database_url == "postgresql+asyncpg://user:pass@host:5432/db"
        assert settings.jwt_secret_key == "super-secret-key-that-is-at-least-32-characters-long"
        assert settings.jwt_algorithm == "HS512"
        assert settings.jwt_access_token_expire_minutes == 60
        assert settings.cors_origins == "https://example.com,https://admin.example.com"


def test_settings_default_values():
    """Verifica que Settings tiene valores por defecto correctos."""
    with patch.dict(
        "os.environ",
        {
            # development exige JWT_SECRET_KEY con >= 32 caracteres (ver Settings.validate_jwt_secret_for_env)
            "JWT_SECRET_KEY": "defaults-test-secret-that-is-at-least-32-characters-long",
        },
        clear=True,
    ):
        settings = Settings()
        
        assert settings.environment == "development"
        assert settings.app_name == "AI Business Platform API"
        assert settings.app_version == "0.1.0"
        assert settings.jwt_algorithm == "HS256"
        assert settings.jwt_access_token_expire_minutes == 30
        assert "localhost" in settings.cors_origins


def test_settings_cors_origins_list_property():
    """Verifica que la propiedad cors_origins_list parsea correctamente."""
    with patch.dict("os.environ", {"CORS_ORIGINS": "http://localhost:3000,http://localhost:5173"}):
        settings = Settings()
        
        assert settings.cors_origins_list == ["http://localhost:3000", "http://localhost:5173"]


def test_settings_cors_origins_list_with_spaces():
    """Verifica que la propiedad cors_origins_list maneja espacios correctamente."""
    with patch.dict("os.environ", {"CORS_ORIGINS": "http://localhost:3000 , http://localhost:5173 ,http://localhost:8080"}):
        settings = Settings()
        
        assert settings.cors_origins_list == [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8080",
        ]


def test_settings_environment_validation():
    """Verifica que la validación de environment funciona correctamente."""
    with patch.dict("os.environ", {"ENVIRONMENT": "invalid"}):
        with pytest.raises(ValidationError):
            Settings()


def test_settings_jwt_secret_key_default():
    """Verifica que el JWT secret key tiene un valor seguro en cualquier entorno."""
    settings = Settings()

    # En 'test' el validator auto-rellena un secret largo; en dev/prod exige uno >= 32 chars.
    # En cualquier entorno el secret resultante debe ser no vacío y suficientemente largo.
    assert settings.jwt_secret_key
    assert len(settings.jwt_secret_key) >= 32


def test_settings_database_url_default():
    """Verifica que la database URL tiene un valor por defecto."""
    settings = Settings()
    
    assert "postgresql+asyncpg://" in settings.database_url
    assert "ai_business_platform" in settings.database_url


def test_settings_case_insensitive():
    """Verifica que las variables de entorno son case-insensitive."""
    with patch.dict(
        "os.environ",
        {
            "environment": "production",
            "database_url": "postgresql+asyncpg://test:test@localhost:5432/test",
            "jwt_secret_key": "test-secret-that-is-at-least-32-characters-long",
            # production exige CORS_ORIGINS explícito y real (SEC-001)
            "cors_origins": "https://app.example.com",
        },
    ):
        settings = Settings()
        
        assert settings.environment == "production"
        assert settings.database_url == "postgresql+asyncpg://test:test@localhost:5432/test"
        assert settings.jwt_secret_key == "test-secret-that-is-at-least-32-characters-long"


def test_settings_ignores_extra_env_vars():
    """Verifica que Settings ignora variables de entorno extra."""
    with patch.dict(
        "os.environ",
        {
            "ENVIRONMENT": "development",
            "JWT_SECRET_KEY": "test-secret-for-ignore-extra-vars-at-least-32-chars-long",
            "UNKNOWN_VAR": "should-be-ignored",
            "ANOTHER_VAR": "also-ignored",
        },
    ):
        # No debe lanzar excepción
        settings = Settings()
        assert settings.environment == "development"


def test_settings_jwt_access_token_expire_minutes_validation():
    """Verifica que la validación de JWT_ACCESS_TOKEN_EXPIRE_MINUTES funciona."""
    with patch.dict("os.environ", {"JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "invalid"}):
        with pytest.raises(ValidationError):
            Settings()


def test_settings_log_level_env_var():
    """Verifica que LOG_LEVEL se puede cargar (si está implementado)."""
    # Este test verifica que al menos el archivo .env.example lo menciona
    # En el futuro, si se implementa log_level en Settings, este test lo validará
    with patch.dict("os.environ", {"LOG_LEVEL": "DEBUG"}):
        settings = Settings()
        # Por ahora solo verificamos que no causa error
        assert settings is not None