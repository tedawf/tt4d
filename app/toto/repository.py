from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, desc, func, select
from sqlalchemy.orm import Session

from app.core.audit import should_insert_attempt
from app.core.locks import release_advisory_lock, try_acquire_advisory_lock
from app.toto.models import (
    TotoDraw,
    TotoItotoLocation,
    TotoScrapeAttempt,
    TotoSnowball,
    TotoWinningShare,
    TotoWinningTicket,
)
from app.toto.types import ParsedTotoDraw

TOTO_ADVISORY_LOCK_KEY = 4040001


def try_acquire_lock(db: Session) -> bool:
    return try_acquire_advisory_lock(db, TOTO_ADVISORY_LOCK_KEY)


def release_lock(db: Session) -> None:
    release_advisory_lock(db, TOTO_ADVISORY_LOCK_KEY)


def get_latest_draw_number(db: Session) -> int:
    current_max = db.execute(select(func.max(TotoDraw.draw_number))).scalar()
    if current_max is None:
        return 0
    return int(current_max)


def get_latest_draw(db: Session) -> Optional[TotoDraw]:
    return (
        db.execute(select(TotoDraw).order_by(desc(TotoDraw.draw_number)).limit(1))
        .scalars()
        .first()
    )


def get_draw(db: Session, draw_number: int) -> Optional[TotoDraw]:
    return db.get(TotoDraw, draw_number)


def get_incomplete_draws(db: Session, limit: int, max_attempts: int) -> list[TotoDraw]:
    return (
        db.execute(
            select(TotoDraw)
            .where(TotoDraw.is_complete.is_(False))
            .where(TotoDraw.scrape_attempt_count < max_attempts)
            .order_by(desc(TotoDraw.draw_number))
            .limit(limit)
        )
        .scalars()
        .all()
    )


def draw_exists(db: Session, draw_number: int) -> bool:
    return get_draw(db, draw_number) is not None


def upsert_draw(db: Session, parsed: ParsedTotoDraw) -> None:
    if parsed.actual_draw_number is None or parsed.draw_date is None:
        raise ValueError("parsed draw is missing required identity fields")

    draw_number = parsed.actual_draw_number
    now = datetime.now(timezone.utc)
    existing = get_draw(db, draw_number)

    if existing:
        existing.draw_date = parsed.draw_date
        existing.winning_numbers = parsed.winning_numbers
        existing.additional_number = parsed.additional_number
        existing.jackpot = parsed.jackpot
        existing.has_winning_shares = bool(parsed.winning_shares)
        existing.has_winning_outlets = bool(
            parsed.group1_result.winning_tickets or parsed.group2_result.winning_tickets
        )
        existing.has_jackpot = parsed.jackpot is not None
        existing.is_complete = parsed.is_complete
        existing.scrape_attempt_count = (existing.scrape_attempt_count or 0) + 1
        existing.last_scrape_attempt_at = now
        existing.updated_at = now

        db.execute(
            delete(TotoWinningShare).where(TotoWinningShare.draw_number == draw_number)
        )
        db.execute(delete(TotoSnowball).where(TotoSnowball.draw_number == draw_number))
        db.execute(
            delete(TotoWinningTicket).where(
                TotoWinningTicket.draw_number == draw_number
            )
        )
    else:
        existing = TotoDraw(
            draw_number=draw_number,
            draw_date=parsed.draw_date,
            winning_numbers=parsed.winning_numbers,
            additional_number=parsed.additional_number,
            jackpot=parsed.jackpot,
            has_winning_shares=bool(parsed.winning_shares),
            has_winning_outlets=bool(
                parsed.group1_result.winning_tickets
                or parsed.group2_result.winning_tickets
            ),
            has_jackpot=parsed.jackpot is not None,
            is_complete=parsed.is_complete,
            scrape_attempt_count=1,
            last_scrape_attempt_at=now,
        )
        db.add(existing)

    db.flush()

    _save_group_data(db, draw_number, parsed)

    db.commit()


def increment_scrape_attempt(db: Session, draw_number: int) -> None:
    draw = get_draw(db, draw_number)
    if draw is None:
        return
    draw.scrape_attempt_count = (draw.scrape_attempt_count or 0) + 1
    draw.last_scrape_attempt_at = datetime.now(timezone.utc)
    draw.updated_at = datetime.now(timezone.utc)
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
        TotoScrapeAttempt,
        requested_draw_number=requested_draw_number,
        outcome=outcome,
        validation_mode=validation_mode,
        result_sha256=result_sha256,
    )
    if not should_insert:
        return False

    db.add(
        TotoScrapeAttempt(
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


def _save_group_data(db: Session, draw_number: int, parsed: ParsedTotoDraw) -> None:
    if parsed.winning_shares:
        db.add_all(
            [
                TotoWinningShare(
                    draw_number=draw_number,
                    group_number=share.group,
                    share_amount=share.amount,
                    winner_count=share.count,
                )
                for share in parsed.winning_shares
            ]
        )

    for group_number, group in [(1, parsed.group1_result), (2, parsed.group2_result)]:
        if group.has_winner and group.winning_tickets:
            _save_winning_tickets(db, draw_number, group_number, group.winning_tickets)
        elif group.snowball_amount:
            db.add(
                TotoSnowball(
                    draw_number=draw_number,
                    group_number=group_number,
                    amount=group.snowball_amount,
                )
            )


def _save_winning_tickets(
    db: Session, draw_number: int, group_number: int, tickets
) -> None:
    for ticket_order, ticket in enumerate(tickets, start=1):
        db_ticket = TotoWinningTicket(
            draw_number=draw_number,
            group_number=group_number,
            ticket_order=ticket_order,
            outlet_name=ticket.outlet_name,
            outlet_address=ticket.outlet_address,
            entry_type=ticket.entry_type,
            is_itoto=ticket.is_itoto,
        )
        db.add(db_ticket)
        db.flush()

        if ticket.is_itoto and ticket.itoto_locations:
            db.add_all(
                [
                    TotoItotoLocation(
                        ticket_id=db_ticket.id,
                        location_order=location_order,
                        outlet_name=location.outlet_name,
                        outlet_address=location.outlet_address,
                        share_count=location.share_count,
                    )
                    for location_order, location in enumerate(
                        ticket.itoto_locations, start=1
                    )
                ]
            )
