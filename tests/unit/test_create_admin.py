from __future__ import annotations

from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.role import Role
from app.models.user import User
from app.scripts.create_admin import _get_credentials_from_env, create_admin_user
from app.services.auth_service import password_hasher


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_repository(
    *,
    get_by_email_return: User | None = None,
    create_return: User | None = None,
    update_return: User | None = None,
) -> MagicMock:
    """Construye un mock de UserRepository con métodos async."""
    repo = MagicMock()
    repo.get_by_email = AsyncMock(return_value=get_by_email_return)
    repo.create = AsyncMock(return_value=create_return)
    repo.update = AsyncMock(return_value=update_return)
    return repo


def _make_mock_user_service(*, create_user_return: User | None = None) -> MagicMock:
    """Construye un mock de UserService con métodos async."""
    svc = MagicMock()
    svc.create_user = AsyncMock(return_value=create_user_return)
    return svc


def _patch_deps(repo: MagicMock, svc: MagicMock) -> ExitStack:
    """Aplica los parches de UserRepository y UserService en create_admin."""
    stack = ExitStack()
    stack.enter_context(patch("app.scripts.create_admin.UserRepository", return_value=repo))
    stack.enter_context(patch("app.scripts.create_admin.UserService", return_value=svc))
    return stack


# ---------------------------------------------------------------------------
# Tests – creación exitosa
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_admin_user_successfully():
    """Verifica que se crea un usuario administrador correctamente."""
    mock_session = AsyncMock()

    email = "admin@example.com"
    password = "SecurePass123!"

    admin_user = User(
        email=email,
        hashed_password=password_hasher.hash(password),
        full_name="Administrator",
    )
    updated_admin = User(
        email=email,
        hashed_password=password_hasher.hash(password),
        full_name="Administrator",
        role=Role.ADMIN,
    )

    repo = _make_mock_repository(
        get_by_email_return=None,
        create_return=admin_user,
        update_return=updated_admin,
    )
    svc = _make_mock_user_service(create_user_return=admin_user)

    with _patch_deps(repo, svc):
        await create_admin_user(email, password, session=mock_session)

    # Se llamó a create_user con los datos correctos
    svc.create_user.assert_called_once()
    call_kwargs = svc.create_user.call_args[1]
    assert call_kwargs["email"] == email
    assert call_kwargs["full_name"] == "Administrator"
    assert call_kwargs["hashed_password"] != password
    assert call_kwargs["hashed_password"].startswith("$")

    # Se actualizó el rol a ADMIN
    repo.update.assert_called_once()
    updated_user = repo.update.call_args[0][0]
    assert updated_user.role == Role.ADMIN


@pytest.mark.asyncio
async def test_create_admin_user_hashes_password():
    """Verifica que la contraseña se hashea correctamente."""
    mock_session = AsyncMock()

    email = "admin@example.com"
    password = "SecurePass123!"

    admin_user = User(
        email=email, hashed_password="hashed", full_name="Administrator"
    )
    updated_admin = User(
        email=email,
        hashed_password="hashed",
        full_name="Administrator",
        role=Role.ADMIN,
    )

    repo = _make_mock_repository(
        get_by_email_return=None,
        create_return=admin_user,
        update_return=updated_admin,
    )
    svc = _make_mock_user_service(create_user_return=admin_user)

    with _patch_deps(repo, svc):
        await create_admin_user(email, password, session=mock_session)

    svc.create_user.assert_called_once()
    call_kwargs = svc.create_user.call_args[1]
    assert call_kwargs["hashed_password"] != password
    assert call_kwargs["hashed_password"].startswith("$")  # Formato Argon2


@pytest.mark.asyncio
async def test_create_admin_user_sets_correct_role():
    """Verifica que el usuario se crea con rol ADMIN."""
    mock_session = AsyncMock()

    email = "admin@example.com"
    password = "SecurePass123!"

    admin_user = User(
        email=email,
        hashed_password=password_hasher.hash(password),
        full_name="Administrator",
    )
    updated_admin = User(
        email=email,
        hashed_password=password_hasher.hash(password),
        full_name="Administrator",
        role=Role.ADMIN,
    )

    repo = _make_mock_repository(
        get_by_email_return=None,
        create_return=admin_user,
        update_return=updated_admin,
    )
    svc = _make_mock_user_service(create_user_return=admin_user)

    with _patch_deps(repo, svc):
        await create_admin_user(email, password, session=mock_session)

    repo.update.assert_called_once()
    updated_user = repo.update.call_args[0][0]
    assert updated_user.role == Role.ADMIN


# ---------------------------------------------------------------------------
# Tests – idempotencia
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_admin_user_when_admin_already_exists():
    """Verifica que no se crea ni modifica nada si el admin ya existe."""
    mock_session = AsyncMock()

    email = "admin@example.com"
    existing_admin = User(
        email=email,
        hashed_password="hashed",
        role=Role.ADMIN,
    )

    repo = _make_mock_repository(get_by_email_return=existing_admin)
    svc = _make_mock_user_service()

    with _patch_deps(repo, svc):
        # No debe lanzar excepción
        await create_admin_user(email, "SecurePass123!", session=mock_session)

    # No se debe haber creado ni actualizado nada
    svc.create_user.assert_not_called()
    repo.update.assert_not_called()


@pytest.mark.asyncio
async def test_create_admin_user_upgrades_existing_user_to_admin():
    """Verifica que un usuario existente sin rol ADMIN se actualiza a ADMIN."""
    mock_session = AsyncMock()

    email = "existing@example.com"
    existing_user = User(
        email=email, hashed_password="hashed", role=Role.USER
    )
    updated_user = User(
        email=email, hashed_password="hashed", role=Role.ADMIN
    )

    repo = _make_mock_repository(
        get_by_email_return=existing_user,
        update_return=updated_user,
    )
    svc = _make_mock_user_service()

    with _patch_deps(repo, svc):
        await create_admin_user(email, "SecurePass123!", session=mock_session)

    # No se debe crear un usuario nuevo
    svc.create_user.assert_not_called()
    # Se debe actualizar el rol
    repo.update.assert_called_once()
    updated = repo.update.call_args[0][0]
    assert updated.role == Role.ADMIN
    assert updated.email == email


# ---------------------------------------------------------------------------
# Tests – validaciones de contraseña
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_admin_user_validates_password_length():
    """Verifica que se valida la longitud mínima de la contraseña."""
    with pytest.raises(SystemExit):
        await create_admin_user("admin@example.com", "short")


@pytest.mark.asyncio
async def test_create_admin_user_rejects_common_passwords():
    """Verifica que se rechazan contraseñas comunes."""
    common_passwords = ["password", "12345678", "admin123", "changeme"]

    for common_password in common_passwords:
        with pytest.raises(SystemExit):
            await create_admin_user("admin@example.com", common_password)


# ---------------------------------------------------------------------------
# Tests – variables de entorno
# ---------------------------------------------------------------------------


def test_get_credentials_from_env_returns_values_when_set():
    """Verifica que _get_credentials_from_env lee ADMIN_EMAIL y ADMIN_PASSWORD."""
    with patch.dict(
        "os.environ",
        {"ADMIN_EMAIL": "admin@example.com", "ADMIN_PASSWORD": "SuperSecret42!"},
    ):
        email, password = _get_credentials_from_env()
        assert email == "admin@example.com"
        assert password == "SuperSecret42!"


def test_get_credentials_from_env_returns_none_when_not_set():
    """Verifica que _get_credentials_from_env retorna (None, None) sin vars."""
    with patch.dict("os.environ", {}, clear=True):
        email, password = _get_credentials_from_env()
        assert email is None
        assert password is None


def test_get_credentials_from_env_returns_none_when_partially_set():
    """Verifica que si falta una variable devuelve None en la parte faltante."""
    with patch.dict("os.environ", {"ADMIN_EMAIL": "admin@example.com"}, clear=True):
        email, password = _get_credentials_from_env()
        assert email == "admin@example.com"
        assert password is None
