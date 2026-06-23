import secrets
from uuid import UUID

import httpx
from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Path,
    Query,
    Request,
    Security,
    status,
)
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
from app.crud import (
    get_user_by_id as get_by_id,
)
from app.deps import (
    get_current_active_user,
    get_current_admin_user,
    require_scopes,
)
from app.limiter import limiter
from app.models import User
from app.schemas import (
    GrantRolePayload,
    GrantRoleResponse,
    OwnerCreate,
    UserCreate,
    UserPublic,
    UserScopesUpdate,
    UserUpdate,
)
from app.scopes import DEFAULT_OWNER_SCOPES, DEFAULT_USER_SCOPES, UserScope
from app.settings import FRONTEND_BASE_URL, NOTIFICATIONS_MS_URL

router = APIRouter(prefix="/users", tags=["users"])


async def _send_verification_email(email: str, token: str, locale: str = "bg") -> None:
    """Fire-and-forget call to notifications-ms to send the verification email."""
    verify_url = f"{FRONTEND_BASE_URL}/{locale}/auth/verify-email?token={token}"
    html = (
        "<h2>Потвърдете имейла си / Verify your email</h2>"
        f"<p>Натиснете бутона по-долу, за да активирате акаунта си:</p>"
        f"<p>Click the button below to activate your account:</p>"
        f'<a href="{verify_url}" style="display:inline-block;padding:12px 24px;'
        f"background:#10b981;color:#fff;text-decoration:none;border-radius:6px;"
        f'font-weight:600;">Потвърди / Verify</a>'
        f'<p style="color:#888;font-size:12px;margin-top:24px;">'
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
@limiter.limit("10/minute")
async def register_user(
    request: Request, payload: UserCreate, locale: str = Query(default="bg")
) -> UserPublic:
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
        locale=locale,
    )

    if payload.email:
        await _send_verification_email(str(payload.email), verification_token, locale)
        logger.info("Verification email sent to {}", payload.email)

    return UserPublic.model_validate(user)


@router.post("/register-owner", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register_owner(
    request: Request,
    payload: OwnerCreate,
    locale: str = Query(default="bg"),
) -> UserPublic:
    """Owner self-registration. Grants DEFAULT_OWNER_SCOPES immediately.

    Account is inactive until email is verified; properties go to pending_approval.
    """
    if await get_user_by_username(payload.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    if await get_user_by_email(str(payload.email)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    hashed_password = get_password_hash(payload.password)
    verification_token = secrets.token_urlsafe(32)

    user = await create_user(
        username=payload.username,
        email=str(payload.email),
        full_name=payload.full_name,
        hashed_password=hashed_password,
        scopes=DEFAULT_OWNER_SCOPES,
        is_active=False,
        email_verification_token=verification_token,
        phone=payload.phone,
        company_name=payload.company_name,
        locale=locale,
    )

    await _send_verification_email(str(payload.email), verification_token, locale)
    logger.info("Owner registered, verification email sent to {}", payload.email)

    return UserPublic.model_validate(user)


@router.get("/", response_model=list[Schema])
@limiter.limit("200/minute")
async def list_users(
    request: Request,
    _=Depends(require_scopes("users:read")),
) -> list[Schema]:
    return await user_crud.get_all()


@router.get("/bulk", response_model=list[Schema])
@limiter.limit("500/minute")
async def get_users_bulk(
    request: Request,
    ids: list[UUID] = Query(...),
) -> list[Schema]:
    """Internal bulk lookup by ID — called by peer services on the Docker network."""
    users = await get_users_by_ids(ids)
    return [Schema.model_validate(u, from_attributes=True) for u in users]


@router.get("/{user_id}", response_model=Schema)
@limiter.limit("200/minute")
async def get_user(
    request: Request, _=Security(get_current_active_user), user_id: UUID = Path()
) -> Schema | None:
    return await user_crud.get_by_id(user_id)


@router.patch("/{user_id}", response_model=UserPublic)
@limiter.limit("60/minute")
async def update_user(
    request: Request,
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await invalidate_user_cache(str(user_id))
    logger.info("User updated and cache invalidated: user_id={}", user_id)
    return UserPublic.model_validate(updated_user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("60/minute")
async def delete_user(
    request: Request, _=Security(get_current_admin_user), user_id: UUID = Path()
) -> None:
    await user_crud.delete_by(id=user_id)


@router.get("/@me/get", response_model=UserPublic)
@limiter.limit("200/minute")
async def read_users_me(
    request: Request,
    current_user: User = Security(get_current_active_user),
) -> UserPublic:
    return UserPublic.model_validate(current_user)


@router.get("/{user_id}/scopes", response_model=UserScopesUpdate, tags=["admin"])
@limiter.limit("60/minute")
async def get_user_scopes(
    request: Request,
    user_id: UUID = Path(),
    _=Security(get_current_admin_user),
) -> UserScopesUpdate:
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserScopesUpdate(scopes=user.scopes or [])


@router.put("/{user_id}/scopes", response_model=UserScopesUpdate, tags=["admin"])
@limiter.limit("60/minute")
async def set_user_scopes(
    request: Request,
    user_id: UUID,
    payload: UserScopesUpdate,
    _=Security(get_current_admin_user),
) -> UserScopesUpdate:
    user = await update_user_scopes(user_id, payload.scopes)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await invalidate_user_cache(str(user_id))
    logger.info("Scopes updated and cache invalidated: user_id={}", user_id)
    return UserScopesUpdate(scopes=user.scopes or [])


@router.post("/{user_id}/grant-role", response_model=GrantRoleResponse, tags=["admin"])
@limiter.limit("30/minute")
async def grant_user_role(
    request: Request,
    user_id: UUID,
    payload: GrantRolePayload,
    _=Security(get_current_admin_user),
) -> GrantRoleResponse:
    """Grant a named role to a user by merging the role's scopes into their existing scopes."""
    owner_scope_strs = {str(s) for s in DEFAULT_OWNER_SCOPES}
    user = await get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot grant role to an inactive user",
        )

    current_scopes = set(user.scopes or [])
    if owner_scope_strs.issubset(current_scopes):
        return GrantRoleResponse(scopes=list(current_scopes))

    merged = list(current_scopes | owner_scope_strs)
    updated = await update_user_scopes(user_id, merged)
    await invalidate_user_cache(str(user_id))
    logger.info("grant_role: granted owner scopes to user_id={}", user_id)
    return GrantRoleResponse(scopes=merged if updated is None else (updated.scopes or []))


@router.post("/{user_id}/grant-owner", response_model=GrantRoleResponse, tags=["internal"])
async def grant_owner_internal(
    user_id: UUID,
    x_user_scopes: str = Header(default=""),
) -> GrantRoleResponse:
    """Internal-only endpoint for service-to-service calls (no JWT required).
    Requires admin:scopes in X-User-Scopes header — provided by the calling service.
    Only reachable on the internal Docker network."""
    if "admin:scopes" not in x_user_scopes.split():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    owner_scope_strs = {str(s) for s in DEFAULT_OWNER_SCOPES}
    user = await get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot grant role to an inactive user",
        )

    current_scopes = set(user.scopes or [])
    if owner_scope_strs.issubset(current_scopes):
        return GrantRoleResponse(scopes=list(current_scopes))

    merged = list(current_scopes | owner_scope_strs)
    updated = await update_user_scopes(user_id, merged)
    await invalidate_user_cache(str(user_id))
    logger.info("grant_owner_internal: granted owner scopes to user_id={}", user_id)
    return GrantRoleResponse(scopes=merged if updated is None else (updated.scopes or []))


@router.post("/{user_id}/revoke-owner", response_model=GrantRoleResponse, tags=["internal"])
async def revoke_owner_internal(
    user_id: UUID,
    x_user_scopes: str = Header(default=""),
) -> GrantRoleResponse:
    """Internal-only endpoint. Strips DEFAULT_OWNER_SCOPES from the user.
    Requires admin:scopes in X-User-Scopes header. Only reachable on the internal Docker network."""
    if "admin:scopes" not in x_user_scopes.split():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    owner_scope_strs = {str(s) for s in DEFAULT_OWNER_SCOPES}
    user = await get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    current_scopes = set(user.scopes or [])
    stripped = list(current_scopes - owner_scope_strs)
    if len(stripped) == len(current_scopes):
        return GrantRoleResponse(scopes=stripped)

    updated = await update_user_scopes(user_id, stripped)
    await invalidate_user_cache(str(user_id))
    logger.info("revoke_owner_internal: revoked owner scopes from user_id={}", user_id)
    return GrantRoleResponse(scopes=stripped if updated is None else (updated.scopes or []))
