from __future__ import annotations

import secrets
from datetime import UTC, datetime

from pwdlib import PasswordHash

from app.core.config import settings
from app.exceptions import AuthenticationError
from app.models.api_key import ApiKey
from app.repositories.api_key_repository import ApiKeyRepository

password_hasher = PasswordHash.recommended()


class ApiKeyService:
    def __init__(self, repository: ApiKeyRepository) -> None:
        self.repository = repository

    def generate_api_key(self) -> tuple[str, str]:
        """Generate a new API key with prefix.

        Returns:
            Tuple of (full_api_key, prefix).
            The full API key is shown once to the user and never stored.
            Only the hash and prefix are stored in the database.
        """
        raw_key = secrets.token_urlsafe(settings.api_key_length)
        prefix = f"{settings.api_key_prefix}_"
        full_key = f"{prefix}{raw_key}"
        return full_key, prefix

    def hash_api_key(self, api_key: str) -> str:
        """Hash an API key for storage."""
        return password_hasher.hash(api_key)

    async def create_api_key(
        self,
        *,
        user_id: str,
        name: str,
        scopes: str | None = None,
        description: str | None = None,
        expires_at: datetime | None = None,
    ) -> tuple[ApiKey, str]:
        """Create a new API key for a user.

        Returns:
            Tuple of (ApiKey record, full_api_key).
            The full API key is shown once and cannot be retrieved again.
        """
        full_key, prefix = self.generate_api_key()
        key_hash = self.hash_api_key(full_key)

        api_key = ApiKey(
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            prefix=prefix,
            scopes=scopes,
            description=description,
            expires_at=expires_at,
            is_active=True,
        )
        created = await self.repository.create(api_key)
        return created, full_key

    async def validate_api_key(self, api_key: str) -> ApiKey:
        """Validate an API key and return the associated record.

        Como el hash es Argon2 (con sal aleatoria), no se puede buscar por
        igualdad de hash. Todas las keys comparten el mismo prefijo fijo
        (settings.api_key_prefix), así que se listan las activas con ese
        prefijo y se verifica cada una con password_hasher.verify().
        """
        prefix = f"{settings.api_key_prefix}_"
        candidates = await self.repository.list_active_by_prefix(prefix)

        record = None
        for candidate in candidates:
            try:
                if password_hasher.verify(api_key, candidate.key_hash):
                    record = candidate
                    break
            except Exception:
                continue

        if record is None:
            raise AuthenticationError("Invalid API key")

        if record.expires_at and record.expires_at < datetime.now(UTC):
            raise AuthenticationError("API key has expired")

        await self.repository.update_last_used(record.id)
        return record

    async def get_user_keys(self, user_id: str) -> list[ApiKey]:
        """Get all API keys for a user."""
        return await self.repository.list_active_by_user_id(user_id)

    async def list_keys_for_user(
        self, user_id: str, *, active_only: bool = True
    ) -> list[ApiKey]:
        """List API keys for a user (admin helper).

        No cambia create_api_key / validate_api_key.
        """
        if active_only:
            return await self.repository.list_active_by_user_id(user_id)
        return await self.repository.get_by_user_id(user_id)

    async def deactivate_api_key(self, api_key_id: str) -> None:
        """Deactivate (revoke) an API key without deleting it."""
        await self.repository.deactivate(api_key_id)

    async def get_api_key_by_id(self, api_key_id: str) -> ApiKey | None:
        """Get an API key by its ID."""
        return await self.repository.get_by_id(api_key_id)
