# brighter-users-ms

Auth authority for the BrighterProject platform. Issues and validates JWTs, manages users and scopes.

**Port:** `8000` | **Prefix:** `/auth`, `/users`, `/scopes`

## Endpoints

| Method | Path | Auth |
|---|---|---|
| `POST` | `/auth/token` | Public — returns JWT |
| `GET` | `/auth/verify` | Called by Traefik `forwardAuth` |
| `POST` | `/users` | Public — registration |
| `GET` | `/users/@me/get` | Any user |
| `GET/PATCH` | `/users/{id}` | Admin |
| `PUT` | `/users/{id}/scopes` | Admin |
| `GET` | `/scopes` | Admin |

## Running

```bash
uv run uvicorn main:application --host 0.0.0.0 --port 8000
uv run pytest
```

## Key env vars

| Variable | Default |
|---|---|
| `DB_URL` | `sqlite://:memory:` |
| `SECRET_KEY` | `change-me-in-production` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` |
| `REDIS_URL` | `redis://redis:6379/0` |
| `GOOGLE_CLIENT_ID` | — |

## Notes

- This is the **only** service that validates JWTs. All others read Traefik-injected headers.
- Redis caches `/auth/verify` results keyed by `SHA256(token)`, TTL 5 min.
- Scope changes invalidate the cache immediately.
- Tests use `monkeypatch` + `DummyUser` — no `conftest.py` or factories.
