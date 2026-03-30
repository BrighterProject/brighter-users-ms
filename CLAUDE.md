# CLAUDE.md — brighter-users-ms

FastAPI microservice that is the **auth authority** for the entire BrighterProject platform. It issues JWTs, validates them for Traefik's `forwardAuth`, and owns all user and scope management.

## Package management

Always use `uv`. Never use `pip` directly.

```bash
uv add <package>       # add dependency
uv sync                # install from lockfile
uv run <command>       # run in the venv
```

## Running

```bash
uv run pytest                                                     # run tests
uv run uvicorn main:application --host 0.0.0.0 --port 8000       # dev server
```

## Architecture

### Technology Stack

- **API Framework**: FastAPI + Uvicorn (port 8000)
- **Database**: PostgreSQL with Tortoise ORM and Aerich migrations
- **JWT**: `python-jose` (HS256), bcrypt for password hashing
- **Testing**: pytest with `monkeypatch` and `dependency_overrides`

### Auth role — critical distinction from other services

**This service IS the JWT issuer and validator.** It is the only service that validates JWTs.

- `POST /auth/token` — issues a JWT from credentials and sets an **httpOnly `access_token` cookie** (SameSite=Lax; TTL = `ACCESS_TOKEN_EXPIRE_MINUTES`)
- `POST /auth/google` — same as above for Google OAuth
- `GET /auth/verify` — called by Traefik `forwardAuth`; reads token from cookie first, falls back to `Authorization: Bearer` header; returns `X-User-Id`, `X-Username`, `X-User-Scopes` headers to Traefik
- `POST /auth/logout` — clears the `access_token` cookie

`get_current_user()` in `app/deps.py` validates the JWT using `python-jose`. Token is extracted via `APIKeyCookie(name="access_token")` — **cookie only, no Bearer fallback**. Do **not** remove this validation — it is the gateway check for the entire system.

Downstream services (properties-ms, bookings-ms) do **not** validate JWTs — they only read the headers Traefik injects after this service approves the request.

## Project structure

```
app/
  auth.py              # JWT creation/verification, bcrypt helpers
  crud.py              # user_crud (CRUD instance) + standalone helpers
  deps.py              # get_current_user() (JWT validation), get_current_active_user, get_current_admin_user, require_scopes()
  models.py            # User Tortoise model
  schemas.py           # UserCreate, UserPublic, UserUpdate, UserScopesUpdate, Token, TokenData
  scopes.py            # UserScope, PropertyScope, BookingScope StrEnums + DEFAULT_*_SCOPES
  settings.py          # DB_URL, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
  routers/
    auth.py            # POST /auth/token, GET /auth/verify
    users.py           # /users CRUD + GET /@me/get + scopes endpoints
    scopes.py          # GET /scopes/ (admin only)
tests/
  test_users_auth.py   # monkeypatch-based tests, DummyUser, dependency_overrides
```

## Scopes

This service is the **central scope registry** for the whole platform. `app/scopes.py` defines all scopes across all microservices:

| Scope group | StrEnum class | Super-scope |
|---|---|---|
| Users | `UserScope` | `admin:users` |
| Properties | `PropertyScope` | `admin:properties` |
| Bookings | `BookingScope` | `admin:bookings` |
| Payments | `PaymentScope` | `admin:payments` |

### Default scope sets assigned on registration

| Set | Assigned to | Contents |
|---|---|---|
| `DEFAULT_USER_SCOPES` | Regular user | `users:me`, `properties:read`, `bookings:read`, `bookings:write`, `bookings:cancel` |
| `DEFAULT_OWNER_SCOPES` | Property owner | + `properties:me/write/delete/images/schedule`, `bookings:manage` |
| `DEFAULT_ADMIN_SCOPES` | Admin | `admin:users`, `admin:properties`, `admin:bookings` |

### Scope escalation (admin-only)

`PUT /users/{id}/scopes` — replaces a user's scopes list entirely. Used by the admin panel to escalate a regular user to property owner by assigning `DEFAULT_OWNER_SCOPES`.

`GET /scopes/` — returns all defined scopes with descriptions (admin only). Used by the admin panel scope picker UI.

## Authorization patterns

```python
# Any authenticated user
Depends(get_current_active_user)

# Admin only
Security(get_current_admin_user)

# Custom scope check
Depends(require_scopes("users:read"))
```

`require_scopes(*scopes)` is a factory that returns a dependency; it checks `current_user.scopes` directly (not the JWT — the user object is loaded from DB).

## Testing conventions

- **No conftest.py** — fixtures are defined inline in the test file
- Use `DummyUser` (plain class, not Tortoise model) to represent auth'd users
- Use `application.dependency_overrides` to replace `get_current_active_user` / `get_current_admin_user`
- Use `monkeypatch.setattr(router_module, "function_name", fake_async_fn)` to mock CRUD calls — no `AsyncMock`/`patch` needed
- Tests run against SQLite in-memory (default `DB_URL`)

```python
# Typical pattern
def test_something(monkeypatch, client: TestClient):
    from app.routers import users as users_router

    async def fake_get_user_by_username(username: str):
        return None

    monkeypatch.setattr(users_router, "get_user_by_username", fake_get_user_by_username)
    resp = client.post("/users/", json={...})
    assert resp.status_code == 201
```

## Redis cache (`app/cache.py`)
- Caches `GET /auth/verify` results keyed by `auth:verify:{sha256(token)}`, TTL 5 min
- Reverse index `auth:user_tokens:{user_id}` allows full invalidation on user mutation
- `invalidate_user_cache(user_id)` is called from `PATCH /users/{id}` and `PUT /users/{id}/scopes`
- All Redis ops silently degrade on failure — auth is never blocked by a Redis outage

## Database

- Tests: SQLite in-memory (default)
- Production: PostgreSQL (`DB_URL` env var)
- Migrations: Aerich — config in `pyproject.toml`, stored in `./migrations/`

```bash
uv run aerich migrate --name <description>
uv run aerich upgrade
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `DB_URL` | `sqlite://:memory:` | Database connection string |
| `SECRET_KEY` | `change-me-in-production` | JWT signing key — **must** be set in prod |
| `ALGORITHM` | `HS256` | JWT signing algorithm (hardcoded, not overridable) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT TTL |
| `REDIS_URL`                   | `redis://localhost:6379/0` | Redis connection string (auth cache) |
| `COOKIE_SECURE`               | `false`                   | Set `true` in production (HTTPS) — wired via Helm `values.prod.yaml` |
