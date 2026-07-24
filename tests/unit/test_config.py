from app.core.config import Settings


def test_settings_use_default_values() -> None:
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