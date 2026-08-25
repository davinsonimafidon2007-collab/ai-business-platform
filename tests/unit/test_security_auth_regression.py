"""Tests de regresión de seguridad — auth, vision SSRF/LFI y schemas (SEC.*)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.core.auth import create_access_token, revoke_token, verify_token
from app.models.inspection import InspectionPhoto
from app.services.vision_service import VisionService

# ---------------------------------------------------------------------------
# SEC.JWT.1 — blacklist en proceso funciona tras el cleanup
# ---------------------------------------------------------------------------


class TestJwtBlacklist:
    def test_token_con_jti_revocado_rechazado(self) -> None:
        token = create_access_token({"sub": "user-1", "jti": "jti-123"})
        payload = verify_token(token)
        assert payload["sub"] == "user-1"

        revoke_token("jti-123")
        from jose import JWTError

        with pytest.raises(JWTError, match="revoked"):
            verify_token(token)

    def test_verify_token_sin_redis_funciona(self) -> None:
        # Tras SEC.JWT.1 verify_token no depende del event loop ni de Redis
        token = create_access_token({"sub": "u2"})
        assert verify_token(token)["sub"] == "u2"


# ---------------------------------------------------------------------------
# SEC.LFI.1 — VisionService descarta fotos con file_path inseguro
# ---------------------------------------------------------------------------


def _photo(path: str) -> InspectionPhoto:
    return InspectionPhoto(
        session_id="s1",
        observation_id="o1",
        file_path=path,
    )


class TestVisionServiceFiltersUnsafePaths:
    @pytest.mark.asyncio
    async def test_ruta_externa_no_llega_al_provider(self) -> None:
        provider = AsyncMock()
        provider.analyze_images.return_value.summary = ""
        provider.analyze_images.return_value.observations = []
        service = VisionService(provider)

        await service.analyze_photos(
            [_photo("/etc/passwd"), _photo("C:\\Windows\\win.ini")],
            {},
        )

        _, kwargs = provider.analyze_images.call_args
        assert len(provider.analyze_images.call_args.args[0]) == 0

    @pytest.mark.asyncio
    async def test_url_data_bloqueada_y_valida_ok(self) -> None:
        provider = AsyncMock()
        provider.analyze_images.return_value.summary = ""
        provider.analyze_images.return_value.observations = []
        service = VisionService(provider)

        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            settings_dir = Path(tmp) / "sess"
            settings_dir.mkdir()
            f = settings_dir / "foto.jpg"
            f.write_bytes(b"\xff\xd8\xff" + b"x" * 10)

            from app.core.config import settings as cfg

            original = cfg.upload_dir
            object.__setattr__(cfg, "upload_dir", tmp)
            try:
                await service.analyze_photos(
                    [_photo("data:image/png;base64,AAAA"), _photo(str(f))],
                    {},
                )
            finally:
                object.__setattr__(cfg, "upload_dir", original)

        images = provider.analyze_images.call_args.args[0]
        assert [i.file_path for i in images] == [str(f)]


# ---------------------------------------------------------------------------
# SEC.INPUT.1 — caps de longitud en schemas de entrada
# ---------------------------------------------------------------------------


class TestSchemaCaps:
    def test_search_query_cap(self) -> None:
        from app.api.v1.schemas.search import SearchAPIRequest

        with pytest.raises(ValidationError):
            SearchAPIRequest(query="x" * 201)

        req = SearchAPIRequest(query="golf")
        assert req.max_results <= 100

    def test_password_max_length(self) -> None:
        from app.schemas.auth import RegisterRequest

        with pytest.raises(ValidationError):
            RegisterRequest(email="a@b.com", password="x" * 129)

    def test_google_id_token_max_length(self) -> None:
        from app.schemas.auth import GoogleAuthRequest

        with pytest.raises(ValidationError):
            GoogleAuthRequest(id_token="x" * 5000)

    def test_observation_notes_cap(self) -> None:
        from app.api.v1.schemas.inspection import ObservationUpdate

        with pytest.raises(ValidationError):
            ObservationUpdate(
                category_id="exterior",
                item_id="pintura",
                status="GOOD",
                notes="n" * 5001,
            )

    def test_photo_upload_request_caps(self) -> None:
        from app.api.v1.schemas.inspection import PhotoUploadRequest

        with pytest.raises(ValidationError):
            PhotoUploadRequest(observation_id="o", file_path="p" * 2049)

    def test_vision_analyze_photo_ids_cap(self) -> None:
        from app.api.v1.schemas.inspection import VisionAnalyzeRequest

        with pytest.raises(ValidationError):
            VisionAnalyzeRequest(photo_ids=[f"id{i}" for i in range(51)])


# ---------------------------------------------------------------------------
# SEC.ENUM.1 — registro no revela emails existentes
# ---------------------------------------------------------------------------


class TestRegisterEnumeration:
    @pytest.mark.asyncio
    async def test_mensaje_generico(self) -> None:
        from unittest.mock import MagicMock

        from app.exceptions import UserAlreadyExistsError
        from app.services.auth_service import AuthService

        repo = AsyncMock()
        repo.get_by_email.return_value = MagicMock()
        service = AuthService(repo)

        with pytest.raises(UserAlreadyExistsError) as exc_info:
            await service.register_user(email="exists@test.com", password="password123")

        assert "exists@test.com" not in str(exc_info.value)
