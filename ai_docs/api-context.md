# API Architecture Context

> Load this file when working on `apps/api`. Referenced by `fastapi-python` / `sqlalchemy-postgres` skills.

## Project-Specific Conventions

- `Router → Session (SQLAlchemy)` — no repository layer; routers use `Depends(get_db)` directly
- Modules: `app/routers/{auth,users,boards,projects,tasks}.py`, models in `app/models.py`, engine/session in `app/database.py`, settings in `app/config.py`
- Cascade deletes via Postgres `ON DELETE CASCADE` (Board→Projects→Tasks) — no application-level events
- Error shape kept NestJS-compatible: `{ statusCode, message, error }` (see `http_error()` in `app/main.py`)
- Auth: PyJWT + cookie, passwordless email login (mirrors old `passport-jwt` + `EmailStrategy` behavior)
- Tests: `httpx.TestClient` against the real app + test DB, function-scoped `client` fixture (not manual mocks)
- IDs are UUID (Postgres `UUID` column), not Mongo ObjectId

## StorageAdapter (API side)

`@repo/store` → `createAuthStore(adapter)`. Web uses `localStorage` adapter (`apps/web/src/stores/auth.ts`).
