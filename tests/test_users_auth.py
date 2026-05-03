"""
Endpoint tests for /auth, /users, and /scopes.

Testing strategy:
  - Auth deps are overridden via conftest.build_app()
  - CRUD functions are patched per-test with AsyncMock (no DB)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.scopes import UserScope

from .factories import OTHER_USER_ID, USER_ID, DummyUser, make_user, user_response

USERS_CRUD_PATH = "app.routers.users"
AUTH_CRUD_PATH = "app.routers.auth"


# ---------------------------------------------------------------------------
# POST /auth/token
# ---------------------------------------------------------------------------


class TestLogin:
    def test_success(self, user_client: TestClient):
        dummy = DummyUser(user_id=uuid4(), username="alice", scopes=["users:me"])
        with patch(f"{AUTH_CRUD_PATH}.authenticate_user", new=AsyncMock(return_value=dummy)):
            resp = user_client.post(
                "/auth/token",
                data={"username": "alice", "password": "secret"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_wrong_credentials(self, user_client: TestClient):
        with patch(f"{AUTH_CRUD_PATH}.authenticate_user", new=AsyncMock(return_value=None)):
            resp = user_client.post(
                "/auth/token",
                data={"username": "alice", "password": "wrong"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /users/
# ---------------------------------------------------------------------------


class TestRegisterUser:
    def test_success(self, user_client: TestClient):
        created = DummyUser(
            user_id=uuid4(),
            username="newuser",
            email="newuser@example.com",
            full_name="New User",
            is_active=False,
            scopes=["users:me"],
            email_verification_token="test-token",
        )
        with (
            patch(f"{USERS_CRUD_PATH}.get_user_by_username", new=AsyncMock(return_value=None)),
            patch(f"{USERS_CRUD_PATH}.get_user_by_email", new=AsyncMock(return_value=None)),
            patch(f"{USERS_CRUD_PATH}.create_user", new=AsyncMock(return_value=created)),
            patch(f"{USERS_CRUD_PATH}._send_verification_email", new=AsyncMock()),
        ):
            resp = user_client.post(
                "/users/",
                json={
                    "username": "newuser",
                    "password": "strongpassword",
                    "email": "newuser@example.com",
                    "full_name": "New User",
                },
            )
        assert resp.status_code == 201
        body = resp.json()
        assert body["username"] == "newuser"
        assert body["email"] == "newuser@example.com"
        assert body["is_active"] is False

    def test_duplicate_username(self, user_client: TestClient):
        existing = make_user()
        with patch(
            f"{USERS_CRUD_PATH}.get_user_by_username", new=AsyncMock(return_value=existing)
        ):
            resp = user_client.post(
                "/users/",
                json={"username": "taken", "password": "pw"},
            )
        assert resp.status_code == 400
        assert "Username" in resp.json()["detail"]

    def test_duplicate_email(self, user_client: TestClient):
        existing = make_user()
        with (
            patch(f"{USERS_CRUD_PATH}.get_user_by_username", new=AsyncMock(return_value=None)),
            patch(
                f"{USERS_CRUD_PATH}.get_user_by_email", new=AsyncMock(return_value=existing)
            ),
        ):
            resp = user_client.post(
                "/users/",
                json={"username": "someone", "password": "pw", "email": "taken@example.com"},
            )
        assert resp.status_code == 400
        assert "Email" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# POST /users/register-owner
# ---------------------------------------------------------------------------

OWNER_PAYLOAD = {
    "username": "owner1",
    "password": "strongpassword",
    "email": "owner1@example.com",
    "full_name": "Иван Иванов",
    "phone": "+359888123456",
}


class TestRegisterOwner:
    def _make_owner_user(self) -> DummyUser:
        from app.scopes import DEFAULT_OWNER_SCOPES

        return DummyUser(
            user_id=uuid4(),
            username="owner1",
            email="owner1@example.com",
            full_name="Иван Иванов",
            is_active=False,
            scopes=list(DEFAULT_OWNER_SCOPES),
            email_verification_token="token-abc",
        )

    def test_success(self, user_client: TestClient):
        created = self._make_owner_user()
        with (
            patch(f"{USERS_CRUD_PATH}.get_user_by_username", new=AsyncMock(return_value=None)),
            patch(f"{USERS_CRUD_PATH}.get_user_by_email", new=AsyncMock(return_value=None)),
            patch(f"{USERS_CRUD_PATH}.create_user", new=AsyncMock(return_value=created)),
            patch(f"{USERS_CRUD_PATH}._send_verification_email", new=AsyncMock()),
        ):
            resp = user_client.post("/users/register-owner", json=OWNER_PAYLOAD)
        assert resp.status_code == 201
        body = resp.json()
        assert body["username"] == "owner1"
        assert body["is_active"] is False

    def test_owner_has_owner_scopes(self, user_client: TestClient):
        from app.scopes import DEFAULT_OWNER_SCOPES, PropertyScope

        created = self._make_owner_user()
        with (
            patch(f"{USERS_CRUD_PATH}.get_user_by_username", new=AsyncMock(return_value=None)),
            patch(f"{USERS_CRUD_PATH}.get_user_by_email", new=AsyncMock(return_value=None)),
            patch(f"{USERS_CRUD_PATH}.create_user", new=AsyncMock(return_value=created)),
            patch(f"{USERS_CRUD_PATH}._send_verification_email", new=AsyncMock()),
        ):
            resp = user_client.post("/users/register-owner", json=OWNER_PAYLOAD)
        assert resp.status_code == 201
        assert PropertyScope.WRITE in resp.json()["scopes"]
        assert PropertyScope.ME in resp.json()["scopes"]

    def test_phone_required(self, user_client: TestClient):
        payload = {**OWNER_PAYLOAD}
        del payload["phone"]
        resp = user_client.post("/users/register-owner", json=payload)
        assert resp.status_code == 422

    def test_email_required(self, user_client: TestClient):
        payload = {k: v for k, v in OWNER_PAYLOAD.items() if k != "email"}
        resp = user_client.post("/users/register-owner", json=payload)
        assert resp.status_code == 422

    def test_duplicate_username(self, user_client: TestClient):
        existing = make_user()
        with patch(f"{USERS_CRUD_PATH}.get_user_by_username", new=AsyncMock(return_value=existing)):
            resp = user_client.post("/users/register-owner", json=OWNER_PAYLOAD)
        assert resp.status_code == 400
        assert "Username" in resp.json()["detail"]

    def test_duplicate_email(self, user_client: TestClient):
        existing = make_user()
        with (
            patch(f"{USERS_CRUD_PATH}.get_user_by_username", new=AsyncMock(return_value=None)),
            patch(f"{USERS_CRUD_PATH}.get_user_by_email", new=AsyncMock(return_value=existing)),
        ):
            resp = user_client.post("/users/register-owner", json=OWNER_PAYLOAD)
        assert resp.status_code == 400
        assert "Email" in resp.json()["detail"]

    def test_with_company_name(self, user_client: TestClient):
        created = self._make_owner_user()
        created.company_name = "Иванов ЕООД"
        with (
            patch(f"{USERS_CRUD_PATH}.get_user_by_username", new=AsyncMock(return_value=None)),
            patch(f"{USERS_CRUD_PATH}.get_user_by_email", new=AsyncMock(return_value=None)),
            patch(
                f"{USERS_CRUD_PATH}.create_user", new=AsyncMock(return_value=created)
            ) as mock_create,
            patch(f"{USERS_CRUD_PATH}._send_verification_email", new=AsyncMock()),
        ):
            resp = user_client.post(
                "/users/register-owner",
                json={**OWNER_PAYLOAD, "company_name": "Иванов ЕООД"},
            )
        assert resp.status_code == 201
        _, kwargs = mock_create.call_args
        assert kwargs.get("company_name") == "Иванов ЕООД"


# ---------------------------------------------------------------------------
# GET /scopes/
# ---------------------------------------------------------------------------


class TestScopes:
    def test_admin_can_list_scopes(self, admin_client: TestClient):
        resp = admin_client.get("/scopes/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_anon_is_rejected(self, anon_app):
        client = TestClient(anon_app, raise_server_exceptions=False)
        resp = client.get("/scopes/")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /users/{id}/scopes  &  PUT /users/{id}/scopes
# ---------------------------------------------------------------------------


class TestUserScopes:
    def test_get_user_scopes(self, admin_client: TestClient):
        stored = DummyUser(user_id=OTHER_USER_ID, scopes=[UserScope.READ])
        with patch(f"{USERS_CRUD_PATH}.get_user_by_id", new=AsyncMock(return_value=stored)):
            resp = admin_client.get(f"/users/{OTHER_USER_ID}/scopes")
        assert resp.status_code == 200
        assert resp.json() == {"scopes": [UserScope.READ]}

    def test_get_user_scopes_not_found(self, admin_client: TestClient):
        with patch(f"{USERS_CRUD_PATH}.get_user_by_id", new=AsyncMock(return_value=None)):
            resp = admin_client.get(f"/users/{uuid4()}/scopes")
        assert resp.status_code == 404

    def test_put_user_scopes(self, admin_client: TestClient):
        stored = DummyUser(user_id=OTHER_USER_ID, scopes=[UserScope.READ, UserScope.ADMIN])
        new_scopes = [UserScope.READ, UserScope.ADMIN]
        with patch(
            f"{USERS_CRUD_PATH}.update_user_scopes", new=AsyncMock(return_value=stored)
        ):
            resp = admin_client.put(
                f"/users/{OTHER_USER_ID}/scopes", json={"scopes": new_scopes}
            )
        assert resp.status_code == 200
        assert resp.json() == {"scopes": new_scopes}

    def test_put_user_scopes_not_found(self, admin_client: TestClient):
        with patch(
            f"{USERS_CRUD_PATH}.update_user_scopes", new=AsyncMock(return_value=None)
        ):
            resp = admin_client.put(
                f"/users/{uuid4()}/scopes", json={"scopes": [UserScope.READ]}
            )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /auth/verify-email
# ---------------------------------------------------------------------------


class TestVerifyEmail:
    def test_success(self, user_client: TestClient):
        unverified = DummyUser(
            user_id=uuid4(),
            username="pending",
            email="pending@example.com",
            is_active=False,
            email_verification_token="valid-token",
        )
        with patch(
            f"{AUTH_CRUD_PATH}.get_user_by_verification_token",
            new=AsyncMock(return_value=unverified),
        ):
            resp = user_client.get("/auth/verify-email?token=valid-token")
        assert resp.status_code == 200
        assert resp.json()["message"] == "Email verified successfully"
        assert unverified.is_active is True
        assert unverified.email_verification_token is None

    def test_already_verified(self, user_client: TestClient):
        already_active = DummyUser(
            user_id=uuid4(),
            username="active",
            is_active=True,
            email_verification_token="some-token",
        )
        with patch(
            f"{AUTH_CRUD_PATH}.get_user_by_verification_token",
            new=AsyncMock(return_value=already_active),
        ):
            resp = user_client.get("/auth/verify-email?token=some-token")
        assert resp.status_code == 200
        assert resp.json()["message"] == "Email already verified"

    def test_invalid_token(self, user_client: TestClient):
        with patch(
            f"{AUTH_CRUD_PATH}.get_user_by_verification_token",
            new=AsyncMock(return_value=None),
        ):
            resp = user_client.get("/auth/verify-email?token=bad-token")
        assert resp.status_code == 400

    def test_missing_token(self, user_client: TestClient):
        resp = user_client.get("/auth/verify-email")
        assert resp.status_code == 422
