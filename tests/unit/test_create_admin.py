from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.role import Role
from app.models.user import User
from app.scripts.create_admin import create_admin_user
from app.services.auth_service import password_hasher


@pytest.mark.asyncio
async def test_create_admin_user_successfully():
    """Verifica que se crea un usuario administrador correctamente."""
    mock_session = AsyncMock()
    
    email = "admin@example.com"
    password = "SecurePass123!"

    # Crear usuario inicial (sin rol ADMIN)
    admin_user = User(email=email, hashed_password=password_hasher.hash(password), full_name="Administrator")
    # Crear usuario actualizado (con rol ADMIN)
    updated_admin = User(email=email, hashed_password=password_hasher.hash(password), full_name="Administrator", role=Role.ADMIN)

    # Mock del repositorio
    mock_repository = MagicMock()
    mock_repository.get_by_email = AsyncMock(return_value=None)
    mock_repository.create = AsyncMock(return_value=admin_user)
    mock_repository.update = AsyncMock(return_value=updated_admin)

    # Mock de UserService
    mock_user_service = MagicMock()
    mock_user_service.create_user = AsyncMock(return_value=admin_user)

    with patch("app.scripts.create_admin.UserRepository", return_value=mock_repository), \
         patch("app.scripts.create_admin.UserService", return_value=mock_user_service):
        await create_admin_user(email, password, session=mock_session)

    # Verificar que se llamó a create_user del servicio con la contraseña hasheada
    mock_user_service.create_user.assert_called_once()
    call_kwargs = mock_user_service.create_user.call_args[1]
    assert call_kwargs["email"] == email
    assert call_kwargs["full_name"] == "Administrator"
    assert call_kwargs["hashed_password"] != password
    assert call_kwargs["hashed_password"].startswith("$")
    
    # Verificar que se actualizó a ADMIN
    mock_repository.update.assert_called_once()
    updated_user = mock_repository.update.call_args[0][0]
    assert updated_user.role == Role.ADMIN


@pytest.mark.asyncio
async def test_create_admin_user_raises_when_user_exists():
    """Verifica que no se crea el admin si el usuario ya existe."""
    mock_session = AsyncMock()
    
    email = "existing@example.com"
    existing_user = User(email=email, hashed_password="hashed", role=Role.USER)

    # Mock del repositorio
    mock_repository = MagicMock()
    mock_repository.get_by_email = AsyncMock(return_value=existing_user)

    with patch("app.scripts.create_admin.UserRepository", return_value=mock_repository):
        with pytest.raises(SystemExit):
            await create_admin_user(email, "password123", session=mock_session)


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


@pytest.mark.asyncio
async def test_create_admin_user_hashes_password():
    """Verifica que la contraseña se hashea correctamente."""
    mock_session = AsyncMock()
    
    email = "admin@example.com"
    password = "SecurePass123!"

    admin_user = User(email=email, hashed_password="hashed", full_name="Administrator")
    updated_admin = User(email=email, hashed_password="hashed", full_name="Administrator", role=Role.ADMIN)

    # Mock del repositorio
    mock_repository = MagicMock()
    mock_repository.get_by_email = AsyncMock(return_value=None)
    mock_repository.create = AsyncMock(return_value=admin_user)
    mock_repository.update = AsyncMock(return_value=updated_admin)

    # Mock de UserService
    mock_user_service = MagicMock()
    mock_user_service.create_user = AsyncMock(return_value=admin_user)

    with patch("app.scripts.create_admin.UserRepository", return_value=mock_repository), \
         patch("app.scripts.create_admin.UserService", return_value=mock_user_service):
        await create_admin_user(email, password, session=mock_session)

    # Verificar que se llamó a create_user con la contraseña hasheada
    mock_user_service.create_user.assert_called_once()
    call_kwargs = mock_user_service.create_user.call_args[1]
    assert call_kwargs["hashed_password"] != password
    assert call_kwargs["hashed_password"].startswith("$")  # Formato Argon2


@pytest.mark.asyncio
async def test_create_admin_user_sets_correct_role():
    """Verifica que el usuario se crea con rol ADMIN."""
    mock_session = AsyncMock()
    
    email = "admin@example.com"
    password = "SecurePass123!"

    admin_user = User(email=email, hashed_password=password_hasher.hash(password), full_name="Administrator")
    updated_admin = User(email=email, hashed_password=password_hasher.hash(password), full_name="Administrator", role=Role.ADMIN)

    # Mock del repositorio
    mock_repository = MagicMock()
    mock_repository.get_by_email = AsyncMock(return_value=None)
    mock_repository.create = AsyncMock(return_value=admin_user)
    mock_repository.update = AsyncMock(return_value=updated_admin)

    # Mock de UserService
    mock_user_service = MagicMock()
    mock_user_service.create_user = AsyncMock(return_value=admin_user)

    with patch("app.scripts.create_admin.UserRepository", return_value=mock_repository), \
         patch("app.scripts.create_admin.UserService", return_value=mock_user_service):
        await create_admin_user(email, password, session=mock_session)

    # Verificar que se actualizó el rol a ADMIN
    mock_repository.update.assert_called_once()
    updated_user = mock_repository.update.call_args[0][0]
    assert updated_user.role == Role.ADMIN
