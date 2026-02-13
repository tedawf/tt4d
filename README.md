# TT4D API

FastAPI service for Singapore Pools Toto and 4D draw collection, persistence, and trigger jobs.

## Quick Start

1. Create and activate virtualenv:

```bash
make venv
source .venv/bin/activate
```

1. Install dependencies:

```bash
pip install -r requirements.txt
```

1. Configure environment (`.env`):

- `DB_USER`
- `DB_PASS`
- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `TT4D_API_KEY`

1. Run migrations:

```bash
make migrate-up
```

1. Start API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Main Endpoints

### Toto

- `GET /toto/draws`
- `GET /toto/draws/latest`
- `GET /toto/draws/search?numbers=1 2 3`
- `GET /toto/draws/{draw_number}`
- `POST /toto/jobs/trigger`
- `POST /toto/jobs/trigger/{draw_number}`

### 4D

- `GET /dddd/draws`
- `GET /dddd/draws/latest`
- `GET /dddd/draws/{draw_number}`
- `POST /dddd/jobs/trigger`
- `POST /dddd/jobs/trigger/{draw_number}`

Draw endpoints are public; all `*/jobs/*` endpoints require `X-API-Key`.

Request body for all trigger endpoints:

```json
{
  "validationMode": "current",
  "dryRun": false
}
```

Example trigger request:

```bash
curl -X POST "http://localhost:8000/toto/jobs/trigger" \
  -H "X-API-Key: $TT4D_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"validationMode":"current","dryRun":false}'
```

## Validation Mode

`validationMode` request field supports:

- `current` (strict validation)
- `past` (relaxed historical validation)

## Testing

```bash
source .venv/bin/activate
pytest -q
```

## Docs

- API endpoints: `docs/api.md`
- Trigger flow and outcomes: `docs/job_flow.md`
