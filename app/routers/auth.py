from typing import Annotated
from urllib.parse import quote

import urllib3
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from google.auth.transport import urllib3 as google_urllib3
from google.oauth2 import id_token as google_id_token
from loguru import logger
from pydantic import BaseModel

from app.auth import authenticate_user, create_access_token
from app.cache import get_verify_cache, set_verify_cache
from app.limiter import limiter
from app.crud import (
    create_user,
    get_user_by_email,
    get_user_by_google_id,
    get_user_by_username,
    get_user_by_verification_token,
)
from app.deps import resolve_user
from app.schemas import Token
from app.scopes import DEFAULT_USER_SCOPES
from app.settings import ACCESS_TOKEN_EXPIRE_MINUTES, COOKIE_SECURE, GOOGLE_CLIENT_ID

router = APIRouter(prefix="/auth", tags=["auth"])

_http = urllib3.PoolManager()
_google_request = google_urllib3.Request(_http)


class GoogleTokenRequest(BaseModel):
    credential: str


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )


@router.post("/token", response_model=Token)
@limiter.limit("10/minute")
async def login_for_access_token(
    request: Request,
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        logger.warning("Failed login attempt for username={}", form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    logger.info("User logged in: username={}", form_data.username)

    access_token = create_access_token(
        data={"sub": user.username}, scopes=user.scopes or []
    )
    _set_auth_cookie(response, access_token)
    return Token(access_token=access_token, token_type="bearer")


@router.get("/verify")
async def verify_token(request: Request):
    """Called by Traefik forwardAuth for every protected request."""
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )
        token = auth_header[7:]

    cached = await get_verify_cache(token)
    if cached:
        logger.debug("Cache hit for verify: username={}", cached["username"])
        return Response(
            status_code=200,
            headers={
                "X-User-Id": cached["user_id"],
                "X-User-Scopes": cached["scopes"],
                "X-Username": quote(cached["username"]),
            },
        )

    user = await resolve_user(token)
    logger.debug("Cache miss for verify: username={}", user.username)
    payload = {
        "user_id": str(user.id),
        "username": user.username,
        "scopes": " ".join(user.scopes or []),
    }
    await set_verify_cache(token, str(user.id), payload)

    return Response(
        status_code=200,
        headers={
            "X-User-Id": payload["user_id"],
            "X-User-Scopes": payload["scopes"],
            "X-Username": quote(payload["username"]),
        },
    )


@router.post("/logout")
@limiter.limit("30/minute")
async def logout(request: Request, response: Response):
    """Clear the authentication cookie."""
    response.delete_cookie(key="access_token", path="/")
    return {"message": "Logged out"}


@router.get("/verify-email")
@limiter.limit("10/minute")
async def verify_email(request: Request, token: str = Query(..., min_length=1)):
    """Public endpoint — activates a user account via the email verification token."""
    user = await get_user_by_verification_token(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    if user.is_active:
        return {"message": "Email already verified"}

    user.is_active = True
    user.email_verification_token = None
    await user.save()
    logger.info("Email verified for user: username={}", user.username)
    return {"message": "Email verified successfully"}


@router.post("/google", response_model=Token)
@limiter.limit("10/minute")
async def login_with_google(request: Request, response: Response, body: GoogleTokenRequest) -> Token:
    """Exchange a Google ID token for a platform JWT."""
    try:
        claims = google_id_token.verify_oauth2_token(
            body.credential, _google_request, GOOGLE_CLIENT_ID
        )
    except Exception as exc:
        logger.warning("Google token verification failed: {}", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google credential",
        )

    google_sub: str = claims["sub"]
    email: str = claims.get("email", "")
    full_name: str | None = claims.get("name")

    # 1. Look up by google_id first (fastest path for returning users)
    user = await get_user_by_google_id(google_sub)

    if user is None and email:
        # 2. Auto-link: existing account with the same email
        user = await get_user_by_email(email)
        if user is not None:
            user.google_id = google_sub
            await user.save()
            logger.info(
                "Linked Google account to existing user: username={}", user.username
            )

    if user is None:
        # 3. First-time Google sign-in — create a new account
        username_base = email.split("@")[0] if email else google_sub[:20]
        username = username_base
        counter = 1
        while await get_user_by_username(username) is not None:
            username = f"{username_base}{counter}"
            counter += 1

        user = await create_user(
            username=username,
            email=email or None,
            full_name=full_name,
            hashed_password=None,
            scopes=[str(s) for s in DEFAULT_USER_SCOPES],
            google_id=google_sub,
        )
        logger.info("Created new user via Google OAuth: username={}", user.username)

    access_token = create_access_token(
        data={"sub": user.username}, scopes=user.scopes or []
    )
    _set_auth_cookie(response, access_token)
    return Token(access_token=access_token, token_type="bearer")
