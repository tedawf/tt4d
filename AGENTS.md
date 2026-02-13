# Repository Guidelines

## Project Structure & Module Organization

Core API code lives in `app/`:

- `app/main.py` boots FastAPI and registers routers.
- `app/core/` contains shared infrastructure and utilities:
  - `auth.py` (API key auth for job triggers)
  - `client.py` (shared URL builder + HTTP fetch transport)
  - `database.py` (SQLAlchemy engine + session)
  - `locks.py` (PostgreSQL advisory locks)
  - `audit.py` (attempt logging + suppression helpers)
  - `schemas.py` (shared Pydantic base model + aliases)
  - `validation.py` (validation mode helpers)
- `app/toto/` contains Toto domain code:
  - `parser.py`, `repository.py`, `service.py`, `schemas.py`, `routes.py`, `models.py`
- `app/dddd/` contains 4D domain code:
  - `parser.py`, `repository.py`, `service.py`, `schemas.py`, `routes.py`, `models.py`

Routers are exposed under domain prefixes:

- Toto draws: `/toto/draws/*` (public)
- Toto jobs: `/toto/jobs/*` (requires `X-API-Key`)
- 4D draws: `/dddd/draws/*` (public)
- 4D jobs: `/dddd/jobs/*` (requires `X-API-Key`)

Database migrations are in `migrations/` (Alembic). Runtime and local tooling files are at repo root: `Makefile`, `docker-compose.yaml`, `Dockerfile`, and `deploy.sh`.

Test fixtures:

- Toto HTML fixtures: `samples/toto_*.html`
- 4D sample HTML: `samples/4d_*.html`

## Build, Test, and Development Commands

- Always activate the repo virtualenv before Python commands: `source .venv/bin/activate`.
- `make help`: list available make targets.
- `make venv && source .venv/bin/activate`: create and activate local virtualenv.
- `pip install -r requirements.txt`: install dependencies.
- `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`: run API locally.
- `make docker-up` / `make docker-down`: start or stop API + Postgres via Docker Compose.
- `make migrate-up`: apply pending migrations.
- `make migrate-new`: generate new Alembic revision.
- `make migrate-down`: roll back one migration.
- `pytest -q`: run test suite.

## Coding Style & Naming Conventions

Follow existing Python style in `app/`:

- 4-space indentation, PEP 8 spacing, explicit imports.
- `snake_case` for functions/variables, `PascalCase` for schema/model classes, `UPPER_SNAKE_CASE` for constants.
- Keep route handlers thin; keep orchestration in `service.py`, persistence in `repository.py`, and parsing in `parser.py`.
- Use type hints consistently.

Validation mode conventions:

- Use `validation_mode` (not `validation_profile`).
- Allowed values: `current`, `past`.

## Testing Guidelines

There is no CI test gate yet. Validate parser and service changes with `pytest` and fixture/sample HTML.

When adding tests:

- Use `pytest` with files named `tests/test_*.py`.
- Prioritize regression coverage for scraping and validation-mode behavior.
- For endpoint changes, manually verify with `curl` and include `X-API-Key` for `*/jobs/*` routes.

## Commit & Pull Request Guidelines

Recent history favors short, imperative commit subjects (for example: `fix trailing slash`, `add logging`). Keep commits focused and scoped to one concern.

PRs should include:

- Clear summary of behavior changes.
- Migration notes (if `migrations/versions/` changed).
- `.env` variable impacts (`DB_*`, `TT4D_API_KEY`).
- Sample request/response for API-facing changes.
