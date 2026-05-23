from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.users import router
from app.scopes import DEFAULT_OWNER_SCOPES


def _make_user(*, is_active: bool = True, scopes: list[str] | None = None):
    u = type("User", (), {
        "id": uuid4(),
        "is_active": is_active,
        "scopes": scopes or [],
    })()
    return u


def _build_app(admin: bool = True):
    """Build a minimal test app with the users router."""
    from app.deps import get_current_admin_user, get_current_user

    app = FastAPI()
    app.include_router(router)

    async def _admin():
        if not admin:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Forbidden")
        return _make_user(scopes=["admin:users"])

    app.dependency_overrides[get_current_admin_user] = _admin
    return app


@pytest.fixture()
def admin_client():
    return TestClient(_build_app(admin=True), raise_server_exceptions=True)


@pytest.fixture()
def non_admin_client():
    return TestClient(_build_app(admin=False), raise_server_exceptions=True)


def test_grant_owner_role_success(admin_client):
    user_id = uuid4()
    existing_scopes = ["users:me", "properties:read"]
    owner_scope_strs = [str(s) for s in DEFAULT_OWNER_SCOPES]
    merged = list(set(existing_scopes) | set(owner_scope_strs))
    mock_updated = _make_user(scopes=merged)

    with (
        patch("app.routers.users.get_by_id", new=AsyncMock(return_value=_make_user(scopes=existing_scopes))),
        patch("app.routers.users.update_user_scopes", new=AsyncMock(return_value=mock_updated)),
        patch("app.routers.users.invalidate_user_cache", new=AsyncMock()),
    ):
        resp = admin_client.post(f"/users/{user_id}/grant-role", json={"role": "owner"})

    assert resp.status_code == 200
    returned = set(resp.json()["scopes"])
    assert set(owner_scope_strs).issubset(returned)


def test_grant_role_unknown_role_is_422(admin_client):
    resp = admin_client.post(f"/users/{uuid4()}/grant-role", json={"role": "superadmin"})
    assert resp.status_code == 422


def test_grant_role_user_not_found_is_404(admin_client):
    with patch("app.routers.users.get_by_id", new=AsyncMock(return_value=None)):
        resp = admin_client.post(f"/users/{uuid4()}/grant-role", json={"role": "owner"})
    assert resp.status_code == 404


def test_grant_role_inactive_user_is_409(admin_client):
    with patch("app.routers.users.get_by_id", new=AsyncMock(return_value=_make_user(is_active=False))):
        resp = admin_client.post(f"/users/{uuid4()}/grant-role", json={"role": "owner"})
    assert resp.status_code == 409


def test_grant_role_idempotent_no_db_write_when_already_owner(admin_client):
    owner_scope_strs = [str(s) for s in DEFAULT_OWNER_SCOPES]
    mock_update = AsyncMock()

    with (
        patch("app.routers.users.get_by_id", new=AsyncMock(
            return_value=_make_user(scopes=owner_scope_strs)
        )),
        patch("app.routers.users.update_user_scopes", new=mock_update),
        patch("app.routers.users.invalidate_user_cache", new=AsyncMock()),
    ):
        resp = admin_client.post(f"/users/{uuid4()}/grant-role", json={"role": "owner"})

    assert resp.status_code == 200
    mock_update.assert_not_called()


def test_grant_role_requires_admin(non_admin_client):
    resp = non_admin_client.post(f"/users/{uuid4()}/grant-role", json={"role": "owner"})
    assert resp.status_code == 403
