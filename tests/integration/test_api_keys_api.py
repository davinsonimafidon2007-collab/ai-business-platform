"""Integration tests for API key HTTP CRUD (Task F.2)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient


def _email() -> str:
    return f"apikey_{uuid.uuid4().hex[:12]}@example.com"


def _register_and_login(client: TestClient) -> str:
    email, password = _email(), "password123"
    r = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert r.status_code in (200, 201), r.text
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def token(client: TestClient) -> str:
    return _register_and_login(client)


class TestApiKeysCRUD:
    def test_list_empty(self, client: TestClient, token: str) -> None:
        r = client.get("/api/v1/auth/api-keys", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["total"] == 0
        assert r.json()["items"] == []

    def test_create_list_get_revoke(self, client: TestClient, token: str) -> None:
        r = client.post(
            "/api/v1/auth/api-keys",
            headers=_auth(token),
            json={"name": "CI Key", "description": "for tests"},
        )
        assert r.status_code == 201, r.text
        data = r.json()
        assert "api_key" in data
        assert data["name"] == "CI Key"
        assert data["is_active"] is True
        assert "key_hash" not in data
        key_id = data["id"]
        full_key = data["api_key"]

        listed = client.get("/api/v1/auth/api-keys", headers=_auth(token))
        assert listed.status_code == 200
        item = next(i for i in listed.json()["items"] if i["id"] == key_id)
        assert "api_key" not in item

        one = client.get(f"/api/v1/auth/api-keys/{key_id}", headers=_auth(token))
        assert one.status_code == 200
        assert one.json()["id"] == key_id
        assert "api_key" not in one.json()

        rev = client.delete(f"/api/v1/auth/api-keys/{key_id}", headers=_auth(token))
        assert rev.status_code == 204

        listed2 = client.get("/api/v1/auth/api-keys", headers=_auth(token))
        assert key_id not in {i["id"] for i in listed2.json()["items"]}
        assert full_key not in listed.text

    def test_foreign_key_404(self, client: TestClient) -> None:
        t1 = _register_and_login(client)
        t2 = _register_and_login(client)
        created = client.post(
            "/api/v1/auth/api-keys",
            headers=_auth(t1),
            json={"name": "Owner Key"},
        )
        assert created.status_code == 201
        key_id = created.json()["id"]
        assert client.get(f"/api/v1/auth/api-keys/{key_id}", headers=_auth(t2)).status_code == 404
        assert client.delete(f"/api/v1/auth/api-keys/{key_id}", headers=_auth(t2)).status_code == 404

    def test_unauthenticated_401(self, client: TestClient) -> None:
        assert client.get("/api/v1/auth/api-keys").status_code == 401
        assert client.post("/api/v1/auth/api-keys", json={"name": "x"}).status_code == 401

    def test_create_validation_422(self, client: TestClient, token: str) -> None:
        r = client.post(
            "/api/v1/auth/api-keys",
            headers=_auth(token),
            json={"name": ""},
        )
        assert r.status_code == 422
