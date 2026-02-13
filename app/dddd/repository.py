from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.audit import should_insert_attempt
from app.core.locks import release_advisory_lock, try_acquire_advisory_lock
from app.dddd.models import DdddDraw, DdddPrize, DdddScrapeAttempt
from app.dddd.types import ParsedDdddDraw

DDDD_ADVISORY_LOCK_KEY = 4040404


def try_acquire_lock(db: Session) -> bool:
    return try_acquire_advisory_lock(db, DDDD_ADVISORY_LOCK_KEY)


def release_lock(db: Session) -> None:
    release_advisory_lock(db, DDDD_ADVISORY_LOCK_KEY)


def get_next_draw_number(db: Session) -> int:
    current_max = db.execute(select(func.max(DdddDraw.draw_number))).scalar()
    if current_max is None:
        return 1
    return int(current_max) + 1


def draw_exists(db: Session, draw_number: int) -> bool:
    existing = db.execute(
        select(DdddDraw.draw_number).where(DdddDraw.draw_number == draw_number)
    ).scalar_one_or_none()
    return existing is not None


def insert_draw_and_prizes(db: Session, parsed: ParsedDdddDraw) -> None:
    draw_number = _required(parsed.actual_draw_number)
    draw_date = _required(parsed.draw_date)

    db.add(DdddDraw(draw_number=draw_number, draw_date=draw_date))
    db.flush()

    db.add_all(_build_prize_rows(draw_number, parsed))
    db.commit()


def replace_draw_and_prizes(db: Session, parsed: ParsedDdddDraw) -> None:
    draw_number = _required(parsed.actual_draw_number)
    draw_date = _required(parsed.draw_date)

    existing = db.get(DdddDraw, draw_number)
    if existing:
        existing.draw_date = draw_date
        existing.updated_at = datetime.now(timezone.utc)
    else:
        db.add(DdddDraw(draw_number=draw_number, draw_date=draw_date))

    db.execute(delete(DdddPrize).where(DdddPrize.draw_number == draw_number))
    db.add_all(_build_prize_rows(draw_number, parsed))
    db.commit()


def write_attempt(
    db: Session,
    *,
    requested_draw_number: int,
    actual_draw_number: Optional[int],
    source_url: str,
    http_status: Optional[int],
    outcome: str,
    validation_mode: str,
    result_sha256: Optional[str],
    error_message: Optional[str] = None,
    response_html: Optional[str] = None,
) -> bool:
    should_insert = should_insert_attempt(
        db,
        DdddScrapeAttempt,
        requested_draw_number=requested_draw_number,
        outcome=outcome,
        validation_mode=validation_mode,
        result_sha256=result_sha256,
    )
    if not should_insert:
        return False

    db.add(
        DdddScrapeAttempt(
            requested_draw_number=requested_draw_number,
            actual_draw_number=actual_draw_number,
            source_url=source_url,
            http_status=http_status,
            outcome=outcome,
            error_message=error_message,
            validation_mode=validation_mode,
            result_sha256=result_sha256,
            response_html=response_html,
        )
    )
    db.commit()
    return True


def _build_prize_rows(draw_number: int, parsed: ParsedDdddDraw) -> list[DdddPrize]:
    rows: list[DdddPrize] = []

    rows.append(
        DdddPrize(
            draw_number=draw_number,
            tier="1",
            tier_idx=1,
            number=_required(parsed.first),
        )
    )
    rows.append(
        DdddPrize(
            draw_number=draw_number,
            tier="2",
            tier_idx=1,
            number=_required(parsed.second),
        )
    )
    rows.append(
        DdddPrize(
            draw_number=draw_number,
            tier="3",
            tier_idx=1,
            number=_required(parsed.third),
        )
    )

    for idx, number in enumerate(parsed.starter, start=1):
        rows.append(
            DdddPrize(draw_number=draw_number, tier="S", tier_idx=idx, number=number)
        )

    for idx, number in enumerate(parsed.consolation, start=1):
        rows.append(
            DdddPrize(draw_number=draw_number, tier="C", tier_idx=idx, number=number)
        )

    return rows


def _required(value):
    if value is None:
        raise ValueError("required value missing")
    return value
