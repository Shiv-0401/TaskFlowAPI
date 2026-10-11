# TaskFlowAPI

A production-grade REST API for a task management system, built with Flask, SQLAlchemy, and JWT authentication. Each user registers, logs in, and manages their own tasks — other users' tasks are inaccessible.

## Architecture

- **App factory pattern** (`app/__init__.py`) — `create_app()` builds and configures the Flask app so tests can spin up isolated instances with a different config (`TestingConfig`) than the running server.
- **Blueprints** (`app/routes/`) — routes are split by resource (`auth`, `tasks`, `users`), each registered under its own `/api/...` prefix.
- **Middleware** (`app/middleware/`) — `auth_middleware.py` provides a `@token_required` decorator that verifies the JWT and attaches the current user to `flask.g.current_user`; `rate_limiter.py` wraps Flask-Limiter as a singleton so it can be imported without circular imports.
- **Validation** (`app/utils/validators.py`) — Marshmallow schemas validate every request body/query string. `load_or_400()` turns a `ValidationError` into a consistent `APIError`.
- **Error handling** (`app/errors.py`) — a single `APIError` exception and three registered handlers (`APIError`, `HTTPException`, generic `Exception`) guarantee every error response has the shape `{"error": "...", "status_code": ...}`.
- **Persistence** — SQLAlchemy models (`app/models.py`) with a `User` → `Task` one-to-many relationship (cascading delete). SQLite for local dev, PostgreSQL in Docker/production, switched purely via the `DATABASE_URL` env var. Alembic (via Flask-Migrate) manages schema migrations in `migrations/`.
- **Auth** — passwords are hashed with `bcrypt`; access tokens (short-lived, 15 min default) and refresh tokens (long-lived, 7 days default) are signed with `PyJWT` using a shared `JWT_SECRET_KEY`. Access tokens carry `"type": "access"` and refresh tokens `"type": "refresh"` so one can't be used in place of the other.

## Endpoints

All error responses share this shape:

```json
{"error": "Task not found", "status_code": 404}
```

Validation errors additionally include a `details` object with per-field Marshmallow error messages.

### Auth

**`POST /api/auth/register`**

```json
// Request
{"email": "ada@example.com", "username": "ada", "password": "password123", "full_name": "Ada Lovelace"}
```
```json
// 201 Response
{
  "user": {"id": 1, "email": "ada@example.com", "username": "ada", "full_name": "Ada Lovelace", "created_at": "...", "updated_at": "..."},
  "access_token": "...",
  "refresh_token": "..."
}
```

**`POST /api/auth/login`**

```json
// Request
{"email": "ada@example.com", "password": "password123"}
```
```json
// 200 Response
{"user": {"...": "..."}, "access_token": "...", "refresh_token": "..."}
```
Returns `401` on wrong email/password.

**`POST /api/auth/refresh`**

```json
// Request
{"refresh_token": "..."}
```
```json
// 200 Response
{"access_token": "...", "refresh_token": "..."}
```
Returns `401` if the token is expired, malformed, or is an access token instead of a refresh token.

### Tasks

All task routes require `Authorization: Bearer <access_token>` and only ever operate on the caller's own tasks.

**`GET /api/tasks?page=1&per_page=20&status=todo&priority=high`**

```json
// 200 Response
{
  "tasks": [{"id": 1, "title": "...", "description": "...", "status": "todo", "priority": "high", "owner_id": 1, "created_at": "...", "updated_at": "..."}],
  "page": 1,
  "per_page": 20,
  "total": 1,
  "total_pages": 1
}
```
`status` and `priority` are optional filters; invalid values return `400`.

**`POST /api/tasks`**

```json
// Request
{"title": "Ship it", "description": "Deploy to prod", "priority": "high"}
```
```json
// 201 Response
{"id": 1, "title": "Ship it", "description": "Deploy to prod", "status": "todo", "priority": "high", "owner_id": 1, "created_at": "...", "updated_at": "..."}
```

**`GET /api/tasks/<id>`** — `200` with the task, `404` if it doesn't exist, `403` if it belongs to another user.

**`PUT /api/tasks/<id>`**

```json
// Request (any subset of fields)
{"status": "in_progress"}
```
`200` with the updated task. `403` if you don't own it, `400` on invalid field values.

**`DELETE /api/tasks/<id>`** — `204` on success, `403` if you don't own it, `404` if it doesn't exist.

### Users

**`GET /api/users/me`** — `200` with the caller's profile.

**`PUT /api/users/me`**

```json
// Request
{"full_name": "Ada Lovelace", "username": "ada2"}
```
`200` with the updated profile. `400` if the new username is already taken.

### Rate limiting

Every route is limited to **100 requests per minute per IP** (Flask-Limiter, configurable via `RATELIMIT_DEFAULT`). Exceeding it returns `429`.

## Running locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # edit as needed; default DATABASE_URL uses SQLite

export FLASK_APP=run.py
flask db upgrade        # creates taskflow.db and applies migrations

python run.py           # serves on http://localhost:5000 (set PORT to override)
```

## Running with Docker

```bash
docker-compose up --build
```

This starts a PostgreSQL container and the API container together. The API entrypoint (`entrypoint.sh`) runs `flask db upgrade` against Postgres before starting Gunicorn, so the schema is always up to date on boot. The API is available at `http://localhost:5000`.

## Running tests

```bash
source venv/bin/activate
pytest -v
```

Tests run against an in-memory SQLite database (`TestingConfig`), created and torn down per test via the `app`/`db` fixtures in `tests/conftest.py`. Coverage includes: registration/login/refresh flows and their failure modes, protected-route rejection (missing/malformed/invalid/expired tokens), full task CRUD, ownership enforcement (a user cannot read/update/delete another user's task), pagination, status/priority filtering, and validation-error paths for every endpoint.

```bash
pytest --cov=app --cov-report=term-missing
```

## Database migrations

Migrations live in `migrations/` and are managed with Alembic via Flask-Migrate:

```bash
flask db migrate -m "describe your change"   # autogenerate a new migration
flask db upgrade                              # apply pending migrations
flask db downgrade                            # roll back one migration
```

## Configuration

All configuration is environment-driven (see `.env.example`):

| Variable | Purpose |
|---|---|
| `APP_ENV` | `development` \| `testing` \| `production` |
| `SECRET_KEY` | Flask session secret |
| `JWT_SECRET_KEY` | Secret used to sign/verify JWTs |
| `JWT_ACCESS_TOKEN_EXPIRES_MINUTES` / `JWT_REFRESH_TOKEN_EXPIRES_DAYS` | Token lifetimes |
| `DATABASE_URL` | SQLAlchemy connection string (SQLite locally, PostgreSQL in Docker) |
| `RATELIMIT_STORAGE_URI` / `RATELIMIT_DEFAULT` / `RATELIMIT_ENABLED` | Flask-Limiter backend and limit |
| `PORT` | Port for the local dev server |
