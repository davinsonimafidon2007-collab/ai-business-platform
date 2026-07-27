from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.api_key import ApiKey
from app.services.api_key_service import ApiKeyService


@pytest.fixture
def mock_repository() -> MagicMock:
    return AsyncMock()


@pytest.fixture
def api_key_service(mock_repository: MagicMock) -> ApiKeyService:
    return ApiKeyService(mock_repository)


class TestApiKeyService:
    async def test_generate_api_key_has_prefix(self, api_key_service: ApiKeyService) -> None:
        """Test that generated API keys have the correct prefix."""
        full_key, prefix = api_key_service.generate_api_key()
        assert full_key.startswith("abp_live_")
        assert prefix == "abp_live_"

    async def test_generate_api_key_unique(self, api_key_service: ApiKeyService) -> None:
        """Test that generated API keys are unique."""
        key1, _ = api_key_service.generate_api_key()
        key2, _ = api_key_service.generate_api_key()
        assert key1 != key2

    async def test_hash_api_key(self, api_key_service: ApiKeyService) -> None:
        """Test that API key hashing produces a hash."""
        api_key = "abp_live_test_key_12345"
        key_hash = api_key_service.hash_api_key(api_key)
        assert key_hash != api_key
        assert len(key_hash) > 0

    async def test_hash_api_key_deterministic(self, api_key_service: ApiKeyService) -> None:
        """Test that the same key produces different hashes (due to salt)."""
        api_key = "abp_live_test_key_12345"
        hash1 = api_key_service.hash_api_key(api_key)
        hash2 = api_key_service.hash_api_key(api_key)
        # PasswordHash uses random salt, so hashes should differ
        assert hash1 != hash2

    async def test_create_api_key_returns_key_and_record(
        self,
        api_key_service: ApiKeyService,
        mock_repository: MagicMock,
    ) -> None:
        """Test that creating an API key returns both record and full key."""
        mock_repository.create.return_value = ApiKey(
            id="test-id",
            user_id="user-1",
            name="Test Key",
            key_hash="hashed_value",
            prefix="abp_live_",
            is_active=True,
        )

        record, full_key = await api_key_service.create_api_key(
            user_id="user-1",
            name="Test Key",
            description="A test API key",
        )

        assert record.user_id == "user-1"
        assert record.name == "Test Key"
        assert record.prefix == "abp_live_"
        assert full_key.startswith("abp_live_")
        assert record.key_hash != full_key  # Hash should differ from raw key
        mock_repository.create.assert_called_once()

    async def test_validate_api_key_valid(
        self,
        api_key_service: ApiKeyService,
        mock_repository: MagicMock,
    ) -> None:
        """Test that a valid API key is accepted."""
        api_key = "abp_live_valid_key_12345"
        key_hash = api_key_service.hash_api_key(api_key)

        mock_record = ApiKey(
            id="test-id",
            user_id="user-1",
            name="Test Key",
            key_hash=key_hash,
            prefix="abp_live_",
            is_active=True,
        )
        mock_repository.get_active_by_key_hash.return_value = mock_record

        result = await api_key_service.validate_api_key(api_key)
        assert result.id == "test-id"
        assert result.user_id == "user-1"
        mock_repository.update_last_used.assert_called_once_with("test-id")

    async def test_validate_api_key_invalid(
        self,
        api_key_service: ApiKeyService,
        mock_repository: MagicMock,
    ) -> None:
        """Test that an invalid API key raises an error."""
        mock_repository.get_active_by_key_hash.return_value = None

        with pytest.raises(Exception) as exc_info:
            await api_key_service.validate_api_key("invalid_key")
        assert "Invalid API key" in str(exc_info.value)

    async def test_validate_api_key_expired(
        self,
        api_key_service: ApiKeyService,
        mock_repository: MagicMock,
    ) -> None:
        """Test that an expired API key raises an error."""
        api_key = "abp_live_expired_key"
        key_hash = api_key_service.hash_api_key(api_key)

        mock_record = ApiKey(
            id="test-id",
            user_id="user-1",
            name="Expired Key",
            key_hash=key_hash,
            prefix="abp_live_",
            is_active=True,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        mock_repository.get_active_by_key_hash.return_value = mock_record

        with pytest.raises(Exception) as exc_info:
            await api_key_service.validate_api_key(api_key)
        assert "expired" in str(exc_info.value).lower()

    async def test_deactivate_api_key(
        self,
        api_key_service: ApiKeyService,
        mock_repository: MagicMock,
    ) -> None:
        """Test that deactivating an API key calls the repository."""
        await api_key_service.deactivate_api_key("test-id")
        mock_repository.deactivate.assert_called_once_with("test-id")

    async def test_get_user_keys(
        self,
        api_key_service: ApiKeyService,
        mock_repository: MagicMock,
    ) -> None:
        """Test that getting user keys returns the list."""
        mock_repository.list_active_by_user_id.return_value = [
            ApiKey(id="key-1", user_id="user-1", name="Key 1", key_hash="hash1", prefix="abp_live_"),
            ApiKey(id="key-2", user_id="user-1", name="Key 2", key_hash="hash2", prefix="abp_live_"),
        ]

        keys = await api_key_service.get_user_keys("user-1")
        assert len(keys) == 2
        assert keys[0].name == "Key 1"
        assert keys[1].name == "Key 2"
