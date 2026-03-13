"""
Tests for POST /auth/google.

Strategy:
  - Patch google_id_token.verify_oauth2_token to avoid real network calls
  - Patch CRUD functions per-test with AsyncMock
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from .factories import DummyUser

AUTH_ROUTER_PATH = "app.routers.auth"

GOOGLE_CLAIMS = {
    "sub": "google-uid-123",
    "email": "alice@example.com",
    "name": "Alice Smith",
}


class TestGoogleLogin:
    def test_existing_google_user_gets_token(self, user_client: TestClient):
        """User already linked with google_id logs in and gets a JWT."""
        existing = DummyUser(
            user_id=uuid4(),
            username="alice",
            email="alice@example.com",
            scopes=["users:me"],
        )
        with (
            patch(f"{AUTH_ROUTER_PATH}.google_id_token.verify_oauth2_token", return_value=GOOGLE_CLAIMS),
            patch(f"{AUTH_ROUTER_PATH}.get_user_by_google_id", new=AsyncMock(return_value=existing)),
        ):
            resp = user_client.post("/auth/google", json={"credential": "fake-id-token"})

        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_auto_link_existing_email_account(self, user_client: TestClient):
        """User registered with email/password; Google login auto-links and returns token."""
        existing = DummyUser(
            user_id=uuid4(),
            username="alice",
            email="alice@example.com",
            scopes=["users:me"],
        )
        # Simulate: no google_id match, but email match exists
        mock_user = MagicMock()
        mock_user.username = existing.username
        mock_user.scopes = existing.scopes
        mock_user.google_id = None
        mock_user.save = AsyncMock()

        with (
            patch(f"{AUTH_ROUTER_PATH}.google_id_token.verify_oauth2_token", return_value=GOOGLE_CLAIMS),
            patch(f"{AUTH_ROUTER_PATH}.get_user_by_google_id", new=AsyncMock(return_value=None)),
            patch(f"{AUTH_ROUTER_PATH}.get_user_by_email", new=AsyncMock(return_value=mock_user)),
        ):
            resp = user_client.post("/auth/google", json={"credential": "fake-id-token"})

        assert resp.status_code == 200
        assert "access_token" in resp.json()
        mock_user.save.assert_awaited_once()
        assert mock_user.google_id == GOOGLE_CLAIMS["sub"]

    def test_new_user_created_on_first_google_login(self, user_client: TestClient):
        """No existing user — a new account is created with default scopes."""
        created = DummyUser(
            user_id=uuid4(),
            username="alice",
            email="alice@example.com",
            scopes=["users:me", "properties:read"],
        )
        with (
            patch(f"{AUTH_ROUTER_PATH}.google_id_token.verify_oauth2_token", return_value=GOOGLE_CLAIMS),
            patch(f"{AUTH_ROUTER_PATH}.get_user_by_google_id", new=AsyncMock(return_value=None)),
            patch(f"{AUTH_ROUTER_PATH}.get_user_by_email", new=AsyncMock(return_value=None)),
            patch(f"{AUTH_ROUTER_PATH}.get_user_by_username", new=AsyncMock(return_value=None)),
            patch(f"{AUTH_ROUTER_PATH}.create_user", new=AsyncMock(return_value=created)),
        ):
            resp = user_client.post("/auth/google", json={"credential": "fake-id-token"})

        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_username_collision_resolved(self, user_client: TestClient):
        """If 'alice' is taken, the new user gets 'alice1'."""
        taken = DummyUser(username="alice")
        created = DummyUser(
            user_id=uuid4(), username="alice1", email="alice@example.com", scopes=[]
        )

        get_by_username_calls = [taken, None]  # first call returns taken, second returns None

        with (
            patch(f"{AUTH_ROUTER_PATH}.google_id_token.verify_oauth2_token", return_value=GOOGLE_CLAIMS),
            patch(f"{AUTH_ROUTER_PATH}.get_user_by_google_id", new=AsyncMock(return_value=None)),
            patch(f"{AUTH_ROUTER_PATH}.get_user_by_email", new=AsyncMock(return_value=None)),
            patch(
                f"{AUTH_ROUTER_PATH}.get_user_by_username",
                new=AsyncMock(side_effect=get_by_username_calls),
            ),
            patch(
                f"{AUTH_ROUTER_PATH}.create_user",
                new=AsyncMock(return_value=created),
            ) as mock_create,
        ):
            resp = user_client.post("/auth/google", json={"credential": "fake-id-token"})

        assert resp.status_code == 200
        _, kwargs = mock_create.call_args
        assert kwargs.get("username") == "alice1" or mock_create.call_args[0][0] == "alice1"

    def test_invalid_google_token_returns_401(self, user_client: TestClient):
        """Bad/expired Google credential → 401."""
        with patch(
            f"{AUTH_ROUTER_PATH}.google_id_token.verify_oauth2_token",
            side_effect=ValueError("Token expired"),
        ):
            resp = user_client.post("/auth/google", json={"credential": "bad-token"})

        assert resp.status_code == 401
        assert "Google" in resp.json()["detail"]
