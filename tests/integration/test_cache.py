"""
Integration tests for Redis caching in users-ms.

These tests require a live Redis instance reachable at REDIS_URL
(default: redis://localhost:6379/0).

Run with:
    pytest -m integration
"""

import pytest

from app.cache import get_verify_cache, invalidate_user_cache, set_verify_cache

_PAYLOAD = {"sub": "user-123", "username": "testuser", "scopes": ["users:me"]}


@pytest.mark.integration
class TestVerifyCache:
    async def test_get_returns_none_for_unknown_token(self):
        assert await get_verify_cache("nonexistent-token") is None

    async def test_set_then_get_returns_cached_payload(self):
        token = "integration-test-token-abc"
        await set_verify_cache(token, "user-123", _PAYLOAD)
        result = await get_verify_cache(token)
        assert result == _PAYLOAD

    async def test_invalidate_removes_all_tokens_for_user(self):
        user_id = "user-invalidate-test"
        token1, token2 = "inv-token-1", "inv-token-2"
        payload = {"sub": user_id, "username": "u", "scopes": []}
        await set_verify_cache(token1, user_id, payload)
        await set_verify_cache(token2, user_id, payload)
        await invalidate_user_cache(user_id)
        assert await get_verify_cache(token1) is None
        assert await get_verify_cache(token2) is None

    async def test_invalidate_unknown_user_does_not_raise(self):
        # Should silently succeed even if no tokens exist for this user.
        await invalidate_user_cache("user-that-never-existed")
