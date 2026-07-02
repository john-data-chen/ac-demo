# API Architecture Context

> Load this file when working on `apps/api`. Referenced by `fastapi-python` / `sqlalchemy-postgres` skills.

## Project-Specific Conventions

- `Router → Session (SQLAlchemy)` — no repository layer; routers use `Depends(get_db)` directly
- Modules: `app/routers/{auth,users,boards,projects,tasks}.py`, models in `app/models.py`, engine/session in `app/database.py`, settings in `app/config.py`, shared response serializers in `app/serializers.py`
- Cascade deletes: ORM `cascade="all, delete-orphan"` on Board→Projects→Tasks relationships, plus `ON DELETE CASCADE` on member-association FKs — deletes must go through the ORM (raw SQL board delete would hit the `tasks.board_id` FK)
- Error shape kept NestJS-compatible: top-level `{ statusCode, message, error }` via global exception handlers in `app/main.py` (`StarletteHTTPException` + `RequestValidationError`); validation errors return **400 with a message array** (NestJS ValidationPipe behavior), not FastAPI's default 422 — the web client reads top-level `.message` (`apps/web/src/lib/api/fetchWithAuth.ts`)
- Routers raise `HTTPException(status, detail={dict in NestJS shape})`; the global handler passes dict details through as the response body
- `status` fields are `Literal` types in Pydantic bodies (task: TODO/IN_PROGRESS/DONE; project: +ARCHIVED); referenced board/project existence is checked before insert (400, never FK IntegrityError 500)
- Auth: PyJWT + cookie, passwordless email login (mirrors old `passport-jwt` + `EmailStrategy` behavior); cookie takes precedence over Bearer header
- Tests: `httpx.AsyncClient(ASGITransport)` against the real app + Postgres; all fixtures live in `tests/conftest.py` (session-scoped engine reads `settings.database_url`, so `DATABASE_URL` env drives CI); never `drop_all` — the DB is shared
- IDs are UUID (Postgres `UUID` column), not Mongo ObjectId; responses keep Mongo-era field names (`_id`, camelCase)

## StorageAdapter (API side)

`@repo/store` → `createAuthStore(adapter)`. Web uses `localStorage` adapter (`apps/web/src/stores/auth.ts`).
