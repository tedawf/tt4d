# API Overview

## Auth

Draw endpoints are public. All `*/jobs/*` endpoints require `X-API-Key`.

## Draws (Public)

### Toto

- `GET /toto/draws`
  - Query params: `skip`, `limit`, `start_date`, `end_date` (`YYYY-MM-DD`)
- `GET /toto/draws/latest`
- `GET /toto/draws/{draw_number}`
- `GET /toto/draws/search?numbers=1 2 3`

### 4D

- `GET /dddd/draws`
  - Query params: `skip`, `limit`, `start_date`, `end_date` (`YYYY-MM-DD`)
- `GET /dddd/draws/latest`
- `GET /dddd/draws/{draw_number}`

## Jobs (Triggers)

These endpoints fetch HTML, parse, validate, and (unless `dryRun=true`) persist results.

### Toto

- `POST /toto/jobs/trigger`
- `POST /toto/jobs/trigger/{draw_number}`

### 4D

- `POST /dddd/jobs/trigger`
- `POST /dddd/jobs/trigger/{draw_number}`

Request body:

```json
{
  "validationMode": "current",
  "dryRun": false
}
```

Example:

```bash
curl -X POST "http://localhost:8000/toto/jobs/trigger" \
  -H "X-API-Key: $TT4D_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"validationMode":"current","dryRun":false}'
```

For flow and possible outcomes, see `docs/job_flow.md`.
