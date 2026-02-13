"""Small wrapper for PostgreSQL advisory locks.

Services use this to avoid overlapping cron/manual runs for the same game job.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session


def try_acquire_advisory_lock(db: Session, lock_key: int) -> bool:
    """Try to acquire a session-scoped advisory lock key."""
    return bool(
        db.execute(
            text("SELECT pg_try_advisory_lock(:key)"),
            {"key": lock_key},
        ).scalar_one()
    )


def release_advisory_lock(db: Session, lock_key: int) -> None:
    """Release a previously acquired advisory lock key."""
    db.execute(
        text("SELECT pg_advisory_unlock(:key)"),
        {"key": lock_key},
    )
