"""Audit helpers shared by Toto and 4D services.

- `stable_result_sha`: stable hash of normalized parsed output
- `should_insert_attempt`: pre-insert suppression for noisy repeated outcomes
"""

import json
import os
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any, Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

HIGH_SIGNAL_OUTCOMES = {
    "success",
    "parse_error",
    "validation_error",
    "db_error",
    "sequence_mismatch",
}

DEFAULT_AUDIT_THROTTLE_SECONDS = int(os.getenv("TT4D_AUDIT_THROTTLE_SECONDS", "300"))


def stable_result_sha(payload: Optional[dict[str, Any]]) -> Optional[str]:
    """Hash normalized parsed result content for comparison/suppression."""
    if payload is None:
        return None
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(encoded.encode("utf-8")).hexdigest()


def should_insert_attempt(
    db: Session,
    attempt_model,
    *,
    requested_draw_number: int,
    outcome: str,
    validation_mode: str,
    result_sha256: Optional[str],
    throttle_seconds: int = DEFAULT_AUDIT_THROTTLE_SECONDS,
) -> bool:
    """Return whether to insert a new attempt row.

    High-signal outcomes are always inserted. Repetitive outcomes are throttled by
    `(requested_draw_number, outcome, validation_mode, result_sha256, attempted_at)`.
    """
    if outcome in HIGH_SIGNAL_OUTCOMES:
        return True

    latest = (
        db.execute(
            select(attempt_model)
            .where(attempt_model.requested_draw_number == requested_draw_number)
            .where(attempt_model.outcome == outcome)
            .where(attempt_model.validation_mode == validation_mode)
            .order_by(desc(attempt_model.attempted_at))
            .limit(1)
        )
        .scalars()
        .first()
    )
    if latest is None or latest.attempted_at is None:
        return True

    latest_at = latest.attempted_at
    if latest_at.tzinfo is None:
        latest_at = latest_at.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) - latest_at > timedelta(seconds=throttle_seconds):
        return True

    return latest.result_sha256 != result_sha256
