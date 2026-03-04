import secrets
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Security, status
from loguru import logger

from app import Schema, user_crud
from app.auth import get_password_hash
from app.cache import invalidate_user_cache
from app.crud import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
    get_users_by_ids,
    update_user_scopes,
)
from app.deps import (
    get_current_active_user,
    get_current_admin_user,
    require_scopes,
)
from app.models import User
from app.schemas import UserCreate, UserPublic, UserScopesUpdate, UserUpdate
from app.scopes import DEFAULT_USER_SCOPES, UserScope
from app.settings import FRONTEND_BASE_URL, NOTIFICATIONS_MS_URL

router = APIRouter(prefix="/users", tags=["users"])


async def _send_verification_email(email: str, token: str, locale: str = "bg") -> None:
    """Fire-and-forget call to notifications-ms to send the verification email."""
    verify_url = f"{FRONTEND_BASE_URL}/{locale}/auth/verify-email?token={token}"
    html = (
        "<h2>Потвърдете имейла си / Verify your email</h2>"
        f'<p>Натиснете бутона по-долу, за да активирате акаунта си:</p>'
        f'<p>Click the button below to activate your account:</p>'
        f'<a href="{verify_url}" style="display:inline-block;padding:12px 24px;'
        f'background:#10b981;color:#fff;text-decoration:none;border-radius:6px;'
        f'font-weight:600;">Потвърди / Verify</a>'
        f"<p style=\"color:#888;font-size:12px;margin-top:24px;\">"
        f"Ако не сте създали акаунт, игнорирайте този имейл.<br>"
        f"If you didn't create an account, ignore this email.</p>"
    )
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{NOTIFICATIONS_MS_URL}/notifications/send",
                json={
                    "to": email,
                    "subject": "Потвърдете имейла си | Verify your email",
                    "html": html,
                    "template": "email_verification",
                    "triggered_by": "users-ms",
                },
                headers={
                    "X-User-Id": "00000000-0000-0000-0000-000000000000",
                    "X-Username": "system",
                    "X-User-Scopes": "admin:notifications:write",
                },
                timeout=10.0,
            )
            resp.raise_for_status()
    except Exception as exc:
        logger.error("Failed to send verification email to {}: {}", email, exc)


@router.post("/", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register_user(payload: UserCreate, locale: str = Query(default="bg")) -> UserPublic:
    existing_username = await get_user_by_username(payload.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    if payload.email:
        existing_email = await get_user_by_email(str(payload.email))
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

    hashed_password = get_password_hash(payload.password)
    verification_token = secrets.token_urlsafe(32)

    user = await create_user(
        username=payload.username,
        email=str(payload.email) if payload.email else None,
        full_name=payload.full_name,
        hashed_password=hashed_password,
        scopes=DEFAULT_USER_SCOPES,
        is_active=False,
        email_verification_token=verification_token,
    )

    if payload.email:
        await _send_verification_email(str(payload.email), verification_token, locale)
        logger.info("Verification email sent to {}", payload.email)

    return UserPublic.model_validate(user)


@router.get("/", response_model=list[Schema])
async def list_users(
    _=Depends(require_scopes("users:read")),
) -> list[Schema]:
    return await user_crud.get_all()


@router.get("/bulk", response_model=list[Schema])
async def get_users_bulk(
    ids: list[UUID] = Query(...),
) -> list[Schema]:
    """Internal bulk lookup by ID — called by peer services on the Docker network."""
    users = await get_users_by_ids(ids)
    return [Schema.model_validate(u, from_attributes=True) for u in users]


@router.get("/{user_id}", response_model=Schema)
async def get_user(
    _=Security(get_current_active_user), user_id: UUID = Path()
) -> Schema | None:
    return await user_crud.get_by_id(user_id)


@router.patch("/{user_id}", response_model=UserPublic)
async def update_user(
    payload: UserUpdate,
    user_id: UUID = Path(),
    current_user: User = Security(get_current_active_user),
) -> UserPublic:
    if current_user.id != user_id and (UserScope.ADMIN not in current_user.scopes):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this user",
        )

    update_data = payload.model_dump(exclude_unset=True)

    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

    updated_user = await user_crud.update_by(update_data, id=user_id)

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    await invalidate_user_cache(str(user_id))
    logger.info("User updated and cache invalidated: user_id={}", user_id)
    return UserPublic.model_validate(updated_user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    _=Security(get_current_admin_user), user_id: UUID = Path()
) -> None:
    await user_crud.delete_by(id=user_id)


@router.get("/@me/get", response_model=UserPublic)
async def read_users_me(
    current_user: User = Security(get_current_active_user),
) -> UserPublic:
    return UserPublic.model_validate(current_user)


@router.get("/{user_id}/scopes", response_model=UserScopesUpdate, tags=["admin"])
async def get_user_scopes(
    user_id: UUID = Path(),
    _=Security(get_current_admin_user),
) -> UserScopesUpdate:
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return UserScopesUpdate(scopes=user.scopes or [])


@router.put("/{user_id}/scopes", response_model=UserScopesUpdate, tags=["admin"])
async def set_user_scopes(
    user_id: UUID,
    payload: UserScopesUpdate,
    _=Security(get_current_admin_user),
) -> UserScopesUpdate:
    user = await update_user_scopes(user_id, payload.scopes)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    await invalidate_user_cache(str(user_id))
    logger.info("Scopes updated and cache invalidated: user_id={}", user_id)
    return UserScopesUpdate(scopes=user.scopes or [])
