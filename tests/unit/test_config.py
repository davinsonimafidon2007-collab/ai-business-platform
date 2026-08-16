from app.core.config import Settings


def test_settings_use_default_values(monkeypatch) -> None:
    # Aislar del entorno del runner (release_check inyecta ENVIRONMENT=test + JWT_SECRET_KEY largo).
    # Este test valida los defaults de "development" con un secret válido (>= 32 chars).
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("JWT_SECRET_KEY", "defaults-test-secret-that-is-at-least-32-characters-long")

    settings = Settings()

    assert settings.app_name == "AI Business Platform API"
    assert settings.app_version == "0.1.0"
    assert settings.environment == "development"


def test_settings_read_environment_variables(monkeypatch) -> None:
    monkeypatch.setenv("APP_NAME", "Test API")
    monkeypatch.setenv("APP_VERSION", "1.2.3")
    monkeypatch.setenv("ENVIRONMENT", "test")

    settings = Settings()

    assert settings.app_name == "Test API"
    assert settings.app_version == "1.2.3"
    assert settings.environment == "test"


def test_firebase_required_defaults_to_false(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    settings = Settings()
    assert settings.firebase_required is False


def test_firebase_required_reads_from_env(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("FIREBASE_REQUIRED", "true")
    settings = Settings()
    assert settings.firebase_required is True