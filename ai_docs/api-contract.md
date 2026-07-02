# API Contract

> **Source**: NestJS `apps/api/src/` — controllers, DTOs, schemas, services, strategies.
> This document is the authoritative reference for the FastAPI rewrite. Do not modify behavior without updating this doc.

---

## Global Configuration

| Item | Value |
|------|-------|
| **Base URL** | No global prefix. Controllers mount at root. |
| **Port** | `3001` (env `PORT` overrides) |
| **Swagger** | `GET /api/docs` |
| **Body parser** | Enabled (JSON) |
| **Validation** | `whitelist: true`, `transform: true`, `forbidNonWhitelisted: true` |
| **Cookie parser** | `cookie-parser` applied before CORS |

### CORS

- `credentials: true`
- Allowed origins: `NEXT_PUBLIC_WEB_URL`, `https://turborepo-starter-kit-web.vercel.app`, Vercel preview regex, `http://localhost:3000`, `http://localhost:8081`, `http://localhost:19006`
- Allowed methods: `GET HEAD PUT PATCH POST DELETE OPTIONS`
- Allowed headers: `Content-Type Accept Authorization X-Requested-With X-XSRF-TOKEN Cookie`
- Exposed headers: `Authorization XSRF-TOKEN Set-Cookie`

---

## Authentication

### Token storage

JWT stored in **two cookies** on successful login:

| Cookie | `httpOnly` | `secure` | `sameSite` | `maxAge` | Notes |
|--------|-----------|---------|----------|---------|-------|
| `jwt` | `true` | prod/vercel | `lax` | 7 days | actual JWT value |
| `isAuthenticated` | `false` | prod/vercel | `lax` | 7 days | `"true"` string, readable by JS |

### JWT extraction order (JwtStrategy)

1. Cookie `req.cookies.jwt`
2. `Authorization: Bearer <token>` header

### JWT payload

```json
{ "sub": "<userId>", "email": "<email>", "iat": 1234, "exp": 1234 }
```

Secret: env `JWT_SECRET`. Expiry: not explicitly set in `JwtModule.register` — check `auth.module.ts` for `signOptions.expiresIn`.

### Email login strategy (`EmailStrategy`)

- Reads `req.body.email` — **no password**. Passwordless auth.
- Finds user by email; throws `401` if not found.

### Guards

| Guard | Passport strategy | Used on |
|-------|-----------------|---------|
| `EmailAuthGuard` | `email` (custom, passport-custom) | `POST /auth/login` |
| `JwtAuthGuard` | `jwt` (passport-jwt) | All other protected routes |

### `@CurrentUser()` decorator

Injects validated user: `{ _id: string, email: string }` (from `JwtStrategy.validate`).

---

## Endpoints

### Auth — `/auth`

#### `POST /auth/login`
- **Auth**: `EmailAuthGuard` (reads `body.email`)
- **Request body**: `{ "email": "string" }`
- **Response 200**:
  ```json
  {
    "user": { "_id": "...", "email": "...", "name": "..." },
    "access_token": "<jwt>"
  }
  ```
- **Sets cookies**: `jwt` + `isAuthenticated`
- **Errors**: `401` — email not found / missing

#### `GET /auth/profile`
- **Auth**: `JwtAuthGuard`
- **Response 200**: `{ "_id": "...", "email": "..." }` (the `@CurrentUser()` object)

#### `POST /auth/logout`
- **Auth**: `JwtAuthGuard`
- **Response 200**: `{ "message": "Successfully logged out" }`
- **Clears cookies**: `jwt` + `isAuthenticated` (maxAge=0)

---

### Users — `/users`

All routes: **JwtAuthGuard**

#### `GET /users`
- **Response 200**: `{ "users": [User, ...] }`
- `User` shape: `{ "_id": "...", "email": "...", "name": "...", "createdAt": "...", "updatedAt": "..." }`

#### `GET /users/search?username=<string>`
- **Query**: `username` (string)
- **Response 200**: `{ "users": [User, ...] }` — filtered by name

---

### Boards — `/boards`

All routes: **JwtAuthGuard**

#### `POST /boards`
- **Request body**:
  ```json
  {
    "title": "string (required)",
    "description": "string (optional)",
    "members": ["mongoId", ...],
    "projects": ["mongoId", ...]
  }
  ```
  > `owner` injected from `@CurrentUser()._id` — do NOT send in body.
- **Response 201**: `Board` object
- **Side effect**: owner auto-added to `members` (deduped set)
- **Errors**: `400`, `401`

#### `GET /boards`
- **Response 200**:
  ```json
  { "myBoards": [Board, ...], "teamBoards": [Board, ...] }
  ```
  - `myBoards`: boards where `owner == currentUser._id`
  - `teamBoards`: boards where `currentUser._id` in `members` but not `owner`

#### `GET /boards/:id`
- **Auth check**: user must be owner OR member
- **Response 200**: `Board`
- **Errors**: `404`, `401`

#### `PATCH /boards/:id`
- **Request body**: any subset of `{ title, description, owner, members, projects }` (all optional)
- **Auth check**: owner or member; non-owner cannot change ownership
- **Response 200**: updated `Board`
- **Errors**: `404`, `401`, `403`

#### `DELETE /boards/:id`
- **Auth check**: owner only
- **Response 200**: `{ "message": "Board deleted successfully" }`
  > Note: Swagger annotates 204 but actual response is 200 with body.
- **Cascade**: Board deleted → all its Projects deleted → all their Tasks deleted (FK CASCADE in PostgreSQL)
- **Errors**: `404`, `401`, `403`

#### `POST /boards/:id/members/:memberId`
- **Auth check**: owner only
- **Response 200**: updated `Board`
- **Errors**: `404`, `401`, `403`

#### `DELETE /boards/:id/members/:memberId`
- **Auth check**: owner only
- **Response 200**: updated `Board`
- **Errors**: `404`, `401`, `403`

**Board response shape**:
```json
{
  "_id": "string",
  "title": "string",
  "description": "string|null",
  "owner": "userId",
  "members": ["userId", ...],
  "projects": ["projectId", ...],
  "createdAt": "ISO8601",
  "updatedAt": "ISO8601"
}
```

---

### Projects — `/projects`

All routes: **JwtAuthGuard**

#### `POST /projects`
- **Request body**:
  ```json
  {
    "title": "string (required)",
    "description": "string (optional)",
    "boardId": "string (required)",
    "orderInBoard": "number (optional, auto-appended if omitted)"
  }
  ```
  > `owner` injected from `@CurrentUser()._id`.
- **Response 201**: `Project` (populated)
- **Side effect**: creator auto-added to `project.members`
- **Errors**: `400` (invalid boardId/ownerId), `401`

#### `GET /projects?boardId=<string>`
- **Query**: `boardId` (required)
- **Response 200**: `[Project, ...]`
- **Errors**: `400` (invalid boardId), `401`

#### `PATCH /projects/:id`
- **Request body** (all optional):
  ```json
  {
    "title": "string",
    "description": "string|null",
    "status": "TODO|IN_PROGRESS|DONE|ARCHIVED",
    "dueDate": "ISO8601",
    "assigneeId": "mongoId|null",
    "orderInBoard": "number"
  }
  ```
- **Permission rules**:
  - Owner → can update any field
  - Non-owner board member → `orderInBoard` only (reorder drag-drop)
  - Other → `400 Forbidden`
- **Response 200**: updated `Project`
- **Errors**: `400`, `401`, `403`, `404`

#### `DELETE /projects/:id`
- **Auth check**: owner only
- **Response 200**: `{ "message": "Project deleted successfully" }`
- **Cascade**: Project deleted → all its Tasks deleted (FK CASCADE); remaining projects in board get `orderInBoard` decremented
- **Errors**: `400`, `401`, `403`, `404`

**Project response shape**:
```json
{
  "_id": "string",
  "title": "string",
  "description": "string|null",
  "owner": "userId",
  "members": ["userId", ...],
  "board": "boardId",
  "orderInBoard": 0,
  "status": "TODO|IN_PROGRESS|DONE|ARCHIVED",
  "dueDate": "ISO8601|null",
  "assignee": "userId|null",
  "createdAt": "ISO8601",
  "updatedAt": "ISO8601"
}
```

---

### Tasks — `/tasks`

All routes: **JwtAuthGuard**. Path `:id` params are validated (ObjectId format).

#### `POST /tasks`
- **Request body**:
  ```json
  {
    "title": "string (required)",
    "description": "string (optional)",
    "status": "TODO|IN_PROGRESS|DONE (optional, default TODO)",
    "dueDate": "ISO8601 (optional)",
    "orderInProject": "number (optional, default 0)",
    "board": "id (required)",
    "project": "id (required)",
    "assignee": "id (optional)"
  }
  ```
  > `creator` + `lastModifier` injected from `@CurrentUser()._id`.
- **Response 201**: `TaskResponse`
- **Side effect**: creator auto-added to `project.members` if not already
- **Errors**: `400`, `401`

#### `GET /tasks?projectId=<string>&assigneeId=<string>`
- **Query** (both optional): `projectId`, `assigneeId`
- **Response 200**: `[TaskResponse, ...]`

#### `GET /tasks/:id`
- **Response 200**: `TaskResponse`
- **Errors**: `404`, `401`

#### `PATCH /tasks/:id`
- **Request body** (all optional):
  ```json
  {
    "title": "string",
    "description": "string|null",
    "status": "TODO|IN_PROGRESS|DONE",
    "dueDate": "ISO8601|null",
    "assigneeId": "id|null",
    "lastModifier": "id",
    "orderInProject": "number"
  }
  ```
  > DTO field is `assigneeId`; internally mapped to `assignee` on the model.
- **Auth check**: current user must be creator OR assignee
- **Auto-sets**: `lastModifier = currentUser._id`, `updatedAt = now`
- **Response 200**: `TaskResponse`
- **Errors**: `400`, `401`, `403`, `404`

#### `DELETE /tasks/:id`
- **Auth check**: creator only (403 if assignee tries)
- **Response 200**: empty body / void
- **Side effect**: remaining tasks in same project get `orderInProject` decremented
- **Errors**: `401`, `403`, `404`

#### `PATCH /tasks/:id/move`
- **Request body**:
  ```json
  { "projectId": "string", "orderInProject": "number" }
  ```
- **Auth check**: creator OR assignee
- **Behavior**:
  - Same project → reorder (shift other tasks)
  - Different project → decrement old project, increment new project from insertion point
- **Response 200**: `TaskResponse`
- **Errors**: `400`, `401`, `404`

**TaskResponse shape**:
```json
{
  "_id": "string",
  "title": "string",
  "description": "string|undefined",
  "status": "TODO|IN_PROGRESS|DONE",
  "dueDate": "ISO8601|undefined",
  "board": "string (id, not populated)",
  "project": "string (id, not populated)",
  "assignee": { "_id": "string", "name": "string|null", "email": "string" } | null,
  "creator": { "_id": "string", "name": "string|null", "email": "string" },
  "lastModifier": { "_id": "string", "name": "string|null", "email": "string" },
  "createdAt": "ISO8601",
  "updatedAt": "ISO8601",
  "orderInProject": 0
}
```

> `assignee`, `creator`, `lastModifier` are **populated** (not raw IDs).
> If DB `lastModifier` is null, response falls back to `creator` value.

---

## Error Response Shape (NestJS default — must match in FastAPI)

```json
{
  "statusCode": 404,
  "message": "Board with ID \"abc\" not found",
  "error": "Not Found"
}
```

---

## Data Model Summary (SQLAlchemy mapping)

| Model | PK | Key fields | Cascade |
|-------|-----|-----------|---------|
| `User` | `UUID` | `email (unique)`, `name`, timestamps | — |
| `Board` | `UUID` | `title`, `description`, `owner_id→User`, timestamps | — |
| `board_members` | join | `board_id`, `user_id` | — |
| `Project` | `UUID` | `title`, `description`, `owner_id→User`, `board_id→Board`, `order_in_board`, `status`, `due_date`, `assignee_id→User`, timestamps | `board_id ON DELETE CASCADE` |
| `project_members` | join | `project_id`, `user_id` | — |
| `Task` | `UUID` | `title`, `description`, `status`, `due_date`, `order_in_project`, `board_id→Board`, `project_id→Project`, `creator_id→User`, `assignee_id→User`, `last_modifier_id→User`, timestamps | `project_id ON DELETE CASCADE` |

**Enums**:
- `ProjectStatus`: `TODO`, `IN_PROGRESS`, `DONE`, `ARCHIVED`
- `TaskStatus`: `TODO`, `IN_PROGRESS`, `DONE`

---

## FastAPI Implementation Notes

1. **No global prefix** — routes: `/auth/login`, `/users`, `/boards`, etc.
2. **Passwordless** — `POST /auth/login` takes `email` only
3. **Cookie names**: exactly `jwt` (httpOnly) and `isAuthenticated` (non-httpOnly)
4. **Wrapped responses**: users → `{ "users": [...] }`, boards → `{ "myBoards": [...], "teamBoards": [...] }`
5. **DELETE /boards/:id** → 200 with `{ "message": "..." }` body (not 204)
6. **DELETE /tasks/:id** → 200, empty body
7. **Task PATCH**: DTO field `assigneeId` → stored as `assignee` in DB
8. **Members auto-add**: board create → owner in members; project create → owner in members; task create → creator in project.members
9. **Order management**: delete project → decrement `orderInBoard` of remaining; delete task → decrement `orderInProject` of remaining
10. **Error shape**: `{ "statusCode": N, "message": "...", "error": "..." }` via FastAPI exception handlers
