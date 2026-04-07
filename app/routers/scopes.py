from fastapi import APIRouter, Request, Security

from app.deps import get_current_admin_user
from app.limiter import limiter
from app.scopes import SCOPE_DESCS

router = APIRouter(prefix="/scopes", tags=["scopes"])


@router.get("/", response_model=list[str])
@limiter.limit("60/minute")
async def list_all_scopes(request: Request, _=Security(get_current_admin_user)) -> list[str]:
    """
    List all known scopes in the system.

    Currently these are composed from:
    - default user scopes
    - admin scopes management scope
    """
    return sorted(SCOPE_DESCS.keys())
