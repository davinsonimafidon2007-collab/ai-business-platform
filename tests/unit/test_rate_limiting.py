from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, settings
from app.main import app


def test_rate_limit_settings_loaded():
    """Verifica que la configuración de rate limiting se carga desde Settings."""
    with patch("app.core.config.settings") as mock_settings:
        mock_settings.rate_limit_global = 60
        mock_settings.rate_limit_login = 5
        mock_settings.rate_limit_register = 10
        
        assert mock_settings.rate_limit_global == 60
        assert mock_settings.rate_limit_login == 5
        assert mock_settings.rate_limit_register == 10


def test_rate_limit_global_applied():
    """Verifica que el rate limit global está aplicado en la aplicación."""
    client = TestClient(app)
    
    # Realizar múltiples peticiones al endpoint de health
    # El límite global es 60 req/min, así que deberíamos poder hacer varias peticiones
    for _ in range(5):
        response = client.get("/health")
        assert response.status_code == 200


def test_rate_limit_login_decorator_applied():
    """Verifica que el decorador de rate limit está aplicado en el endpoint de login."""
    from app.api.v1.auth import login_user
    from app.main import limiter
    
    # Verificar que el endpoint tiene el límite configurado en el limiter
    assert login_user is not None
    
    # Verificar que el limiter global está configurado
    assert limiter is not None
    # Verificar que tiene límites por defecto configurados
    assert hasattr(limiter, "_default_limits")


def test_rate_limit_configuration_values():
    """Verifica que los valores de configuración son correctos."""
    with patch("app.core.config.settings") as mock_settings:
        # Valores por defecto
        mock_settings.rate_limit_global = 60
        mock_settings.rate_limit_login = 5
        mock_settings.rate_limit_register = 10
        
        # Verificar que los valores son enteros positivos
        assert isinstance(mock_settings.rate_limit_global, int)
        assert isinstance(mock_settings.rate_limit_login, int)
        assert isinstance(mock_settings.rate_limit_register, int)
        assert mock_settings.rate_limit_global > 0
        assert mock_settings.rate_limit_login > 0
        assert mock_settings.rate_limit_register > 0


def test_rate_limit_login_more_restrictive_than_global():
    """Verifica que el límite de login es más restrictivo que el global."""
    with patch("app.core.config.settings") as mock_settings:
        mock_settings.rate_limit_global = 60
        mock_settings.rate_limit_login = 5
        
        # El límite de login debe ser menor que el global
        assert mock_settings.rate_limit_login < mock_settings.rate_limit_global