import os

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.settings import REDIS_URL

# When SLOWAPI_NO_LIMITS is set (e.g. in tests / e2e) disable limiting entirely:
# skip Redis storage so no connection is opened, and turn the limiter off so the
# e2e suite — whose many registrations share one Traefik-sourced IP bucket — is
# never throttled.
_no_limits = bool(os.environ.get("SLOWAPI_NO_LIMITS"))
_storage_uri = None if _no_limits else REDIS_URL
limiter = Limiter(
    key_func=get_remote_address, storage_uri=_storage_uri, enabled=not _no_limits
)
