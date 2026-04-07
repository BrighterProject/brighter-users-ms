"""
Shared pytest fixtures available to every test file automatically.
"""

from __future__ import annotations

import os

# Disable slowapi rate limiting in tests — must be set before app.limiter is imported.
os.environ["SLOWAPI_NO_LIMITS"] = "true"

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.deps import get_current_active_user, get_current_admin_user
from app.routers.auth import router as auth_router
from app.routers.scopes import router as scopes_router
from app.routers.users import router as users_router

from .factories import make_admin, make_user

# In-memory limiter for unit tests — avoids any Redis connection at import time.
_limiter = Limiter(key_func=get_remote_address)


# ---------------------------------------------------------------------------
# App builder
# ---------------------------------------------------------------------------


def build_app(active_user, admin_user=None) -> FastAPI:
    """
    Fresh FastAPI app with auth dependencies overridden.
    `admin_user` defaults to `active_user` when not provided.
    """
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(scopes_router)
    app.state.limiter = _limiter

    _admin = admin_user if admin_user is not None else active_user

    app.dependency_overrides[get_current_active_user] = lambda: active_user
    app.dependency_overrides[get_current_admin_user] = lambda: _admin

    return app


# ---------------------------------------------------------------------------
# Client fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def user_client():
    """TestClient authenticated as a regular user."""
    return TestClient(build_app(make_user()), raise_server_exceptions=True)


@pytest.fixture()
def admin_client():
    """TestClient authenticated as an admin."""
    return TestClient(build_app(make_admin()), raise_server_exceptions=True)


@pytest.fixture()
def anon_app():
    """
    Bare app with NO dependency overrides.
    Use this to assert 401/403 from real auth deps.
    """
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(scopes_router)
    return app


@pytest.fixture()
def client_factory():
    """
    Callable fixture: call it with any DummyUser (and optional admin_user).

    Usage:
        def test_something(client_factory):
            client = client_factory(make_user(scopes=[...]))
            resp = client.get("/users/")
    """

    def _make(active_user, admin_user=None) -> TestClient:
        return TestClient(
            build_app(active_user, admin_user=admin_user),
            raise_server_exceptions=True,
        )

    return _make


# ---------------------------------------------------------------------------
# Redis cache mock — keeps unit tests free of any Redis dependency.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _mock_cache():
    with (
        patch("app.routers.auth.get_verify_cache", new=AsyncMock(return_value=None)),
        patch("app.routers.auth.set_verify_cache", new=AsyncMock()),
        patch("app.routers.users.invalidate_user_cache", new=AsyncMock()),
        patch("app.routers.contact.check_contact_rate_limit", new=AsyncMock(return_value=True)),
    ):
        yield
