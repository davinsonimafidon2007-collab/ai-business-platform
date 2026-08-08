"""Integration tests for admin API key management (Task F.4).

Cubre: listar keys de cualquier usuario y revocar cualquier key (ADMIN),
con 403 para USER, 401 sin token, 404 para id inexistente y 422 sin user_id.
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.models.role import Role
from tests.integration.conftest import user_repository


def _promote_to_admin(user_id: str) -> None:
    """Promueve el rol del usuario a ADMIN en el repo fake (sync)."""
    for user in user_repository._users.values():
        if str(user.id) == str(user_id):
            user.role = Role.ADMIN
            return
    raise AssertionError(f"User {user_id} not found in fake repo")


def _email() -> str:
    return f"adminkey_{uuid.uuid4().hex[:12]}@example.com"


def _register(client: TestClient, *, role: Role = Role.USER) -> dict:
    """Registra un usuario y devuelve (user_id, token)."""
    email, password = _email(), "password123"
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert r.status_code in (200, 201), r.text
    user_id = str(r.json()["id"])

    # Promover rol a ADMIN si se pide (el override de auth resuelve por user_id)
    if role == Role.ADMIN:
        _promote_to_admin(user_id)

    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return {"user_id": user_id, "token": login.json()["access_token"]}


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_key(client: TestClient, token: str, name: str = "Target Key") -> str:
    r = client.post(
        "/api/v1/auth/api-keys",
        headers=_auth(token),
        json={"name": name},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


class TestAdminListApiKeys:
    def test_admin_lists_other_users_keys(self, client: TestClient) -> None:
        admin = _register(client, role=Role.ADMIN)
        target = _register(client)
        key_id = _create_key(client, target["token"])

        r = client.get(
            f"/api/v1/admin/api-keys?user_id={target['user_id']}",
            headers=_auth(admin["token"]),
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["total"] == 1
        assert [i["id"] for i in data["items"]] == [key_id]
        # metadata only
        assert "api_key" not in data["items"][0]
        assert "key_hash" not in data["items"][0]

    def test_admin_active_only_filter(self, client: TestClient) -> None:
        admin = _register(client, role=Role.ADMIN)
        target = _register(client)
        key_id = _create_key(client, target["token"])
        # revocar la key para que quede inactiva
        client.delete(f"/api/v1/auth/api-keys/{key_id}", headers=_auth(target["token"]))

        active = client.get(
            f"/api/v1/admin/api-keys?user_id={target['user_id']}&active_only=true",
            headers=_auth(admin["token"]),
        )
        assert active.status_code == 200
        assert active.json()["total"] == 0

        all_keys = client.get(
            f"/api/v1/admin/api-keys?user_id={target['user_id']}&active_only=false",
            headers=_auth(admin["token"]),
        )
        assert all_keys.status_code == 200
        assert all_keys.json()["total"] == 1
        assert all_keys.json()["items"][0]["id"] == key_id

    def test_user_is_forbidden(self, client: TestClient) -> None:
        user = _register(client)
        target = _register(client)
        r = client.get(
            f"/api/v1/admin/api-keys?user_id={target['user_id']}",
            headers=_auth(user["token"]),
        )
        assert r.status_code == 403

    def test_unauthenticated_401(self, client: TestClient) -> None:
        r = client.get("/api/v1/admin/api-keys?user_id=some-user")
        assert r.status_code == 401

    def test_missing_user_id_422(self, client: TestClient) -> None:
        admin = _register(client, role=Role.ADMIN)
        r = client.get("/api/v1/admin/api-keys", headers=_auth(admin["token"]))
        assert r.status_code == 422


class TestAdminRevokeApiKey:
    def test_admin_revokes_foreign_key(self, client: TestClient) -> None:
        admin = _register(client, role=Role.ADMIN)
        target = _register(client)
        key_id = _create_key(client, target["token"])

        r = client.delete(
            f"/api/v1/admin/api-keys/{key_id}",
            headers=_auth(admin["token"]),
        )
        assert r.status_code == 204

        # El dueño ya no la ve en su GET own
        own = client.get("/api/v1/auth/api-keys", headers=_auth(target["token"]))
        assert own.status_code == 200
        assert key_id not in {i["id"] for i in own.json()["items"]}

    def test_admin_revoke_nonexistent_404(self, client: TestClient) -> None:
        admin = _register(client, role=Role.ADMIN)
        r = client.delete(
            f"/api/v1/admin/api-keys/{uuid.uuid4()}",
            headers=_auth(admin["token"]),
        )
        assert r.status_code == 404

    def test_user_cannot_revoke_via_admin(self, client: TestClient) -> None:
        user = _register(client)
        target = _register(client)
        key_id = _create_key(client, target["token"])
        r = client.delete(
            f"/api/v1/admin/api-keys/{key_id}",
            headers=_auth(user["token"]),
        )
        assert r.status_code == 403

    def test_unauthenticated_delete_401(self, client: TestClient) -> None:
        r = client.delete(f"/api/v1/admin/api-keys/{uuid.uuid4()}")
        assert r.status_code == 401
