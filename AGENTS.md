# Repository Guidelines

## Project Structure & Module Organization

Core API code lives in `app/`:

- `app/main.py` boots FastAPI and registers routers.
- `app/routes/` contains HTTP endpoints (`draw_router.py`, `scrape_router.py`).
- `app/models.py`, `app/schemas.py`, and `app/queries.py` define persistence and response shapes.
- `app/scraper.py` handles Singapore Pools fetch/parse logic.

Database migrations are in `migrations/` (Alembic). Runtime and local tooling files are at repo root: `Makefile`, `docker-compose.yaml`, `Dockerfile`, `deploy.sh`, and `trigger_scrape.sh`. HTML fixtures for parser checks are under `mocks/`.

## Build, Test, and Development Commands

- Always activate the repo virtualenv before any Python-related command: `source .venv/bin/activate`.
- `make help`: list available make targets.
- `make venv && source .venv/bin/activate`: create and activate local virtualenv.
- `pip install -r requirements.txt`: install Python dependencies.
- `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`: run API locally.
- `make docker-up` / `make docker-down`: start or stop API + Postgres via Docker Compose.
- `make migrate-up`: apply pending migrations.
- `make migrate-new`: generate a new Alembic revision.
- `make migrate-down`: roll back one migration.

## Coding Style & Naming Conventions

Follow existing Python style in `app/`:

- 4-space indentation, PEP 8 spacing, and explicit imports.
- `snake_case` for functions/variables, `PascalCase` for schema/model classes, `UPPER_SNAKE_CASE` for constants.
- Keep route handlers thin; put DB and parsing logic in `queries.py`/`scraper.py`.
- Use type hints (`Optional`, `List`, tuple return types) consistently.

No formatter/linter is currently enforced in-repo; keep changes consistent with surrounding code.

## Testing Guidelines

There is no committed automated test suite yet and no CI test gate. For parser or query changes, validate with local runs and `mocks/*.html`. For endpoint changes, manually verify with `curl` (include `X-API-Key` for `/scrape`).

When adding tests, use `pytest` with files named `tests/test_*.py` and prioritize regression coverage for scraping edge cases.

## Commit & Pull Request Guidelines

Recent history favors short, imperative commit subjects (for example: `fix trailing slash`, `add logging`). Keep commits focused and scoped to one concern.

PRs should include:

- Clear summary of behavior changes.
- Migration notes (if `migrations/versions/` changed).
- `.env` variable impacts (`DB_*`, `TT4D_API_KEY`).
- Sample request/response for API-facing changes.
