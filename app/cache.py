import hashlib
import json

from loguru import logger
from redis.asyncio import Redis

from app.settings import CONTACT_RATE_LIMIT, CONTACT_RATE_WINDOW, REDIS_URL

_redis: Redis | None = None
VERIFY_TTL = 300  # 5 minutes


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(REDIS_URL, decode_responses=True)
    return _redis


def _token_key(token: str) -> str:
    return f"auth:verify:{hashlib.sha256(token.encode()).hexdigest()}"


def _user_tokens_key(user_id: str) -> str:
    return f"auth:user_tokens:{user_id}"


async def get_verify_cache(token: str) -> dict | None:
    try:
        data = await get_redis().get(_token_key(token))
        return json.loads(data) if data else None
    except Exception:
        logger.warning("Redis get failed — skipping cache", exc_info=True)
        return None


async def set_verify_cache(token: str, user_id: str, payload: dict) -> None:
    try:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        pipe = get_redis().pipeline()
        pipe.setex(_token_key(token), VERIFY_TTL, json.dumps(payload))
        pipe.sadd(_user_tokens_key(user_id), token_hash)
        pipe.expire(_user_tokens_key(user_id), VERIFY_TTL)
        await pipe.execute()
    except Exception:
        logger.warning("Redis set failed — skipping cache", exc_info=True)


async def check_contact_rate_limit(ip: str) -> bool:
    """Returns True if the request is allowed, False if rate-limited."""
    key = f"contact:rate:{ip}"
    try:
        r = get_redis()
        current = await r.incr(key)
        if current == 1:
            await r.expire(key, CONTACT_RATE_WINDOW)
        return current <= CONTACT_RATE_LIMIT
    except Exception:
        logger.warning("Redis rate-limit check failed — allowing request", exc_info=True)
        return True


async def invalidate_user_cache(user_id: str) -> None:
    try:
        r = get_redis()
        user_key = _user_tokens_key(user_id)
        token_hashes = await r.smembers(user_key)
        if token_hashes:
            keys = [f"auth:verify:{h}" for h in token_hashes]
            await r.delete(*keys, user_key)
        else:
            await r.delete(user_key)
    except Exception:
        logger.warning("Redis invalidate failed", exc_info=True)
