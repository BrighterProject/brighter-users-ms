"""Seed dev users: admin, subscribed owner, unsubscribed owner, regular user.

All users are active and email-verified. Run inside the users-ms container:
    docker compose exec -T users-ms uv run python scripts/seed.py

UUIDs are fixed so the payments seed can reference dev_owner_sub by ID.
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tortoise import Tortoise

from app.auth import get_password_hash
from app.models import User
from app.scopes import (
    BookingScope,
    NotificationScope,
    PaymentScope,
    PropertyScope,
    UserScope,
    DEFAULT_OWNER_SCOPES,
    DEFAULT_USER_SCOPES,
)

DB_URL: str = os.environ.get("DB_URL", "asyncpg://brighter:brighter@localhost:5432/brighter")

ALL_SCOPES: list[str] = [
    str(scope)
    for enum_cls in (UserScope, PropertyScope, BookingScope, PaymentScope, NotificationScope)
    for scope in enum_cls
]

USERS: list[dict] = [
    dict(
        id=uuid.UUID("a0000000-0000-0000-0000-000000000001"),
        username="admin@liberhack.org",
        full_name="Dev Admin",
        email="admin@liberhack.org",
        password="admin123!",
        scopes=ALL_SCOPES,
    ),
    dict(
        id=uuid.UUID("a0000000-0000-0000-0000-000000000002"),
        username="owner@liberhack.org",
        full_name="Dev Owner (subscribed)",
        email="owner@liberhack.org",
        password="owner123!",
        scopes=[str(s) for s in DEFAULT_OWNER_SCOPES],
    ),
    dict(
        id=uuid.UUID("a0000000-0000-0000-0000-000000000003"),
        username="owner2@liberhack.org",
        full_name="Dev Owner (no subscription)",
        email="owner2@liberhack.org",
        password="owner123!",
        scopes=[str(s) for s in DEFAULT_OWNER_SCOPES],
    ),
    dict(
        id=uuid.UUID("a0000000-0000-0000-0000-000000000004"),
        username="user@liberhack.org",
        full_name="Dev User",
        email="user@liberhack.org",
        password="user123!",
        scopes=[str(s) for s in DEFAULT_USER_SCOPES],
    ),
]


async def seed() -> None:
    """Upsert all dev seed users."""
    await Tortoise.init(db_url=DB_URL, modules={"models": ["app.models"]})

    for u in USERS:
        password = u.pop("password")
        await User.update_or_create(
            id=u["id"],
            defaults={
                **u,
                "hashed_password": get_password_hash(password),
                "is_active": True,
                "email_verification_token": None,
            },
        )
        u["password"] = password
        print(f"[seed] {u['username']} ({u['email']})")

    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(seed())
