from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.search import ProviderIssue
from app.services.providers.autoscout24 import AutoScout24Provider
from app.services.providers.mobile_de import MobileDeProvider


@pytest.mark.integration_db
class TestProviderErrorHandling:
    """Tests de manejo de errores de proveedores externos."""

    @pytest.mark.asyncio
    async def test_autoscout24_handles_404_gracefully(self):
        """Test que AS24 maneja 404 (marca inexistente) correctamente."""
        provider = AutoScout24Provider()

        with patch.object(provider, "_fetch_listings") as mock_fetch:
            from httpx import HTTPStatusError

            mock_response = AsyncMock()
            mock_response.status_code = 404
            mock_fetch.side_effect = HTTPStatusError(
                "Not Found", request=AsyncMock(), response=mock_response
            )

            results, issues = await provider.search(
                brand="MarcaInexistenteXYZ",
                model="ModeloFake",
                min_price=10000,
                max_price=20000,
            )

            # Debe devolver 0 resultados pero con issue claro
            assert len(results) == 0
            assert len(issues) > 0
            assert any(
                "marca" in issue.message.lower() or "not found" in issue.message.lower()
                for issue in issues
            )

    @pytest.mark.asyncio
    async def test_autoscout24_handles_timeout_with_retry(self):
        """Test que AS24 reintenta ante timeouts."""
        provider = AutoScout24Provider()

        with patch.object(provider, "_fetch_listings") as mock_fetch:
            import httpx

            mock_fetch.side_effect = httpx.TimeoutException("Request timeout")

            results, issues = await provider.search(
                brand="BMW", model="Series 3", min_price=20000, max_price=30000
            )

            # Después de reintentos, debe devolver issue de timeout
            assert len(issues) > 0
            assert any("timeout" in issue.error_type.lower() for issue in issues)

    @pytest.mark.asyncio
    async def test_mobile_de_handles_403_anti_bot(self):
        """Test que mobile.de maneja 403 (anti-bot) correctamente."""
        provider = MobileDeProvider()

        with patch.object(provider, "_fetch_listings") as mock_fetch:
            from httpx import HTTPStatusError

            mock_response = AsyncMock()
            mock_response.status_code = 403
            mock_fetch.side_effect = HTTPStatusError(
                "Forbidden", request=AsyncMock(), response=mock_response
            )

            results, issues = await provider.search(
                brand="Audi", model="A4", min_price=15000, max_price=25000
            )

            # Debe devolver issue de anti-bot
            assert len(issues) > 0
            assert any(
                "anti-bot" in issue.message.lower() or "403" in issue.message for issue in issues
            )

    def test_provider_issues_are_actionable(self):
        """Test que los mensajes de provider_issues son accionables por el usuario."""
        from app.utils.provider_issue_labels import get_actionable_message

        issue = ProviderIssue(
            provider="autoscout24",
            stage="search",
            error_type="not_found",
            message="Brand 'MarcaFake' not found",
        )

        actionable_msg = get_actionable_message(issue)

        # El mensaje debe ser claro y accionable
        assert len(actionable_msg) > 0
        assert "revisa" in actionable_msg.lower() or "verifica" in actionable_msg.lower()
