# Job Flow

This project has two independent trigger APIs because Toto and 4D run on different schedules:

- `POST /toto/jobs/trigger`
- `POST /toto/jobs/trigger/{draw_number}`
- `POST /dddd/jobs/trigger`
- `POST /dddd/jobs/trigger/{draw_number}`

All trigger endpoints share the same request body:

```json
{
  "validationMode": "current",
  "dryRun": false
}
```

`validationMode` can be `current` or `past`.

## Toto Trigger Flow

1. Acquire Toto advisory lock.
2. Decide requested draw:
   - `/toto/jobs/trigger`: retry latest incomplete draw first, otherwise next draw number.
   - `/toto/jobs/trigger/{draw_number}`: use exact draw number.
3. Fetch source HTML.
4. Parse and validate.
5. If valid and not `dryRun`, upsert draw + related rows.
6. Write audit attempt row (with suppression for noisy repeated outcomes).
7. Release lock.

## 4D Trigger Flow

1. Acquire 4D advisory lock.
2. Decide requested draw:
   - `/dddd/jobs/trigger`: next draw number.
   - `/dddd/jobs/trigger/{draw_number}`: use exact draw number.
3. Fetch source HTML.
4. Parse and validate.
5. If valid and not `dryRun`, insert or replace draw rows.
6. Write audit attempt row (with suppression for noisy repeated outcomes).
7. Release lock.

## Common Outcomes

- `success`
- `dry_run`
- `already_exists`
- `no_new_draw`
- `skipped_locked`
- `fetch_error`
- `parse_error`
- `validation_error`
- `sequence_mismatch`
- `db_error`
