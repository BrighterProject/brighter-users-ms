from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyCookie, SecurityScopes
from jose import JWTError, jwt

from app.crud import get_user_by_username
from app.models import User
from app.schemas import TokenData
from app.scopes import UserScope
from app.settings import (
    ALGORITHM,
    SECRET_KEY,
)

cookie_scheme = APIKeyCookie(name="access_token")

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
)


async def resolve_user(token: str) -> User:
    """Decode JWT and load the user from DB. Used by verify route + get_current_user."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise _CREDENTIALS_EXCEPTION
    except JWTError:
        raise _CREDENTIALS_EXCEPTION

    user = await get_user_by_username(username)
    if user is None or not user.is_active:
        raise _CREDENTIALS_EXCEPTION

    return user


async def get_current_user(
    security_scopes: SecurityScopes,
    token: Annotated[str, Depends(cookie_scheme)],
) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        token_scopes: list[str] = payload.get("scopes", [])
        if username is None:
            raise _CREDENTIALS_EXCEPTION
        token_data = TokenData(username=username, scopes=token_scopes)
    except JWTError:
        raise _CREDENTIALS_EXCEPTION

    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )

    user = await get_user_by_username(token_data.username)  # type: ignore[arg-type]
    if user is None:
        raise _CREDENTIALS_EXCEPTION

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated"
        )

    return user


async def get_current_active_user(current_user=Security(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_admin_user(
    current_user=Security(get_current_user, scopes=[UserScope.ADMIN]),
) -> User:
    return current_user


def require_scopes(*required: str):
    """
    Factory that returns a dependency enforcing one or more scopes.

    Usage:
        @router.get("/admin-only")
        async def admin_route(user = Depends(require_scopes("admin:scopes"))):
            ...
    """

    async def _dep(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        missing = [s for s in required if s not in current_user.scopes]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scopes: {', '.join(missing)}",
            )
        return current_user

    return _dep
