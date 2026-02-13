"""Toto trigger orchestration.

Flow shape:
1) fetch HTML
2) parse + validate (by validation_mode)
3) persist draw (unless dry_run)
4) write audit attempt row with suppression
"""

import logging
import os
from typing import Optional

import app.core.client as core_client
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.audit import stable_result_sha
from app.core.validation import ensure_validation_mode
from app.toto.parser import parse_toto_html, validate_parsed_draw
from app.toto.repository import (
    get_draw,
    get_incomplete_draws,
    get_latest_draw_number,
    increment_scrape_attempt,
    release_lock,
    try_acquire_lock,
    upsert_draw,
    write_attempt,
)
from app.toto.types import TotoRunResult

logger = logging.getLogger(__name__)

MAX_SCRAPE_ATTEMPTS = int(os.getenv("MAX_SCRAPE_ATTEMPTS", "20"))
TOTO_BASE_URL = "https://www.singaporepools.com.sg/en/product/sr/Pages/toto_results.aspx"
REQUEST_TIMEOUT_SECONDS = 10


def run_trigger_next(
    db: Session,
    *,
    validation_mode: str,
    dry_run: bool,
) -> TotoRunResult:
    """Trigger the next Toto scrape cycle.

    Prefers retrying the latest incomplete draw before moving to a new draw number.
    """
    ensure_validation_mode(validation_mode)

    incomplete = get_incomplete_draws(db, limit=1, max_attempts=MAX_SCRAPE_ATTEMPTS)
    if incomplete:
        requested_draw_number = incomplete[0].draw_number
        replay = True
    else:
        requested_draw_number = get_latest_draw_number(db) + 1
        replay = False

    return _run_with_lock(
        db,
        requested_draw_number=requested_draw_number,
        validation_mode=validation_mode,
        dry_run=dry_run,
        replay=replay,
    )


def run_trigger_replay(
    db: Session,
    *,
    draw_number: int,
    validation_mode: str,
    dry_run: bool,
) -> TotoRunResult:
    """Trigger Toto scraping for an explicit draw number."""
    ensure_validation_mode(validation_mode)
    return _run_with_lock(
        db,
        requested_draw_number=draw_number,
        validation_mode=validation_mode,
        dry_run=dry_run,
        replay=True,
    )


def _run_with_lock(
    db: Session,
    *,
    requested_draw_number: int,
    validation_mode: str,
    dry_run: bool,
    replay: bool,
) -> TotoRunResult:
    """Run a Toto fetch flow under the advisory lock."""
    if not try_acquire_lock(db):
        return _audit_and_result(
            db,
            outcome="skipped_locked",
            requested_draw_number=requested_draw_number,
            actual_draw_number=None,
            validation_mode=validation_mode,
            source_url=core_client.build_source_url(
                TOTO_BASE_URL, requested_draw_number
            ),
            http_status=None,
            result_sha256=None,
            message="another toto trigger job is running",
            response_html=None,
        )

    try:
        return _run_fetch(
            db,
            requested_draw_number=requested_draw_number,
            validation_mode=validation_mode,
            dry_run=dry_run,
            replay=replay,
        )
    finally:
        _release_lock_safely(db)


def _run_fetch(
    db: Session,
    *,
    requested_draw_number: int,
    validation_mode: str,
    dry_run: bool,
    replay: bool,
) -> TotoRunResult:
    """Execute one Toto fetch/parse/validate/persist attempt."""
    fetch_result = core_client.fetch_draw_html(
        TOTO_BASE_URL,
        requested_draw_number,
        timeout_seconds=REQUEST_TIMEOUT_SECONDS,
    )
    response_html = fetch_result.html

    if fetch_result.error_message:
        return _audit_and_result(
            db,
            outcome="fetch_error",
            requested_draw_number=requested_draw_number,
            actual_draw_number=None,
            validation_mode=validation_mode,
            source_url=fetch_result.source_url,
            http_status=fetch_result.http_status,
            result_sha256=None,
            message=fetch_result.error_message,
            response_html=response_html,
            increment_attempt=True,
        )

    if fetch_result.http_status is None or fetch_result.http_status >= 400:
        message = f"http error status {fetch_result.http_status}"
        return _audit_and_result(
            db,
            outcome="fetch_error",
            requested_draw_number=requested_draw_number,
            actual_draw_number=None,
            validation_mode=validation_mode,
            source_url=fetch_result.source_url,
            http_status=fetch_result.http_status,
            result_sha256=None,
            message=message,
            response_html=response_html,
            increment_attempt=True,
        )

    parsed = parse_toto_html(fetch_result.html or "", requested_draw_number)
    result_sha256 = stable_result_sha(parsed.normalized_payload())

    if parsed.actual_draw_number is None:
        message = (
            ";".join(parsed.parse_errors)
            if parsed.parse_errors
            else "missing_actual_draw_number"
        )
        return _audit_and_result(
            db,
            outcome="parse_error",
            requested_draw_number=requested_draw_number,
            actual_draw_number=None,
            validation_mode=validation_mode,
            source_url=fetch_result.source_url,
            http_status=fetch_result.http_status,
            result_sha256=result_sha256,
            message=message,
            response_html=response_html,
            increment_attempt=True,
        )

    if parsed.actual_draw_number < requested_draw_number:
        return _audit_and_result(
            db,
            outcome="no_new_draw",
            requested_draw_number=requested_draw_number,
            actual_draw_number=parsed.actual_draw_number,
            validation_mode=validation_mode,
            source_url=fetch_result.source_url,
            http_status=fetch_result.http_status,
            result_sha256=result_sha256,
            message="latest available draw is still behind requested draw",
            response_html=response_html,
            increment_attempt=True,
        )

    if parsed.actual_draw_number > requested_draw_number:
        message = f"requested_draw_number_{requested_draw_number}_actual_draw_number_{parsed.actual_draw_number}"
        return _audit_and_result(
            db,
            outcome="sequence_mismatch",
            requested_draw_number=requested_draw_number,
            actual_draw_number=parsed.actual_draw_number,
            validation_mode=validation_mode,
            source_url=fetch_result.source_url,
            http_status=fetch_result.http_status,
            result_sha256=result_sha256,
            message=message,
            response_html=response_html,
            increment_attempt=True,
        )

    if parsed.parse_errors:
        return _audit_and_result(
            db,
            outcome="parse_error",
            requested_draw_number=requested_draw_number,
            actual_draw_number=parsed.actual_draw_number,
            validation_mode=validation_mode,
            source_url=fetch_result.source_url,
            http_status=fetch_result.http_status,
            result_sha256=result_sha256,
            message=";".join(parsed.parse_errors),
            response_html=response_html,
            increment_attempt=True,
        )

    validation_errors = validate_parsed_draw(parsed, validation_mode)
    if validation_errors:
        return _audit_and_result(
            db,
            outcome="validation_error",
            requested_draw_number=requested_draw_number,
            actual_draw_number=parsed.actual_draw_number,
            validation_mode=validation_mode,
            source_url=fetch_result.source_url,
            http_status=fetch_result.http_status,
            result_sha256=result_sha256,
            message=";".join(validation_errors),
            response_html=response_html,
            increment_attempt=True,
        )

    if not replay:
        existing = get_draw(db, requested_draw_number)
        if existing and existing.is_complete:
            return _audit_and_result(
                db,
                outcome="already_exists",
                requested_draw_number=requested_draw_number,
                actual_draw_number=parsed.actual_draw_number,
                validation_mode=validation_mode,
                source_url=fetch_result.source_url,
                http_status=fetch_result.http_status,
                result_sha256=result_sha256,
                message="draw already exists",
                response_html=response_html,
            )

    if dry_run:
        return _audit_and_result(
            db,
            outcome="dry_run",
            requested_draw_number=requested_draw_number,
            actual_draw_number=parsed.actual_draw_number,
            validation_mode=validation_mode,
            source_url=fetch_result.source_url,
            http_status=fetch_result.http_status,
            result_sha256=result_sha256,
            message="validated but not persisted",
            response_html=response_html,
        )

    try:
        upsert_draw(db, parsed)
        return _audit_and_result(
            db,
            outcome="success",
            requested_draw_number=requested_draw_number,
            actual_draw_number=parsed.actual_draw_number,
            validation_mode=validation_mode,
            source_url=fetch_result.source_url,
            http_status=fetch_result.http_status,
            result_sha256=result_sha256,
            message="draw persisted",
            response_html=response_html,
        )
    except SQLAlchemyError as exc:
        db.rollback()
        return _audit_and_result(
            db,
            outcome="db_error",
            requested_draw_number=requested_draw_number,
            actual_draw_number=parsed.actual_draw_number,
            validation_mode=validation_mode,
            source_url=fetch_result.source_url,
            http_status=fetch_result.http_status,
            result_sha256=result_sha256,
            message=str(exc),
            response_html=response_html,
        )


def _audit_and_result(
    db: Session,
    *,
    outcome: str,
    requested_draw_number: int,
    actual_draw_number: Optional[int],
    validation_mode: str,
    source_url: str,
    http_status: Optional[int],
    result_sha256: Optional[str],
    message: Optional[str],
    response_html: Optional[str],
    increment_attempt: bool = False,
) -> TotoRunResult:
    """Persist attempt audit and return a consistent API result payload."""
    _write_audit_safely(
        db,
        requested_draw_number=requested_draw_number,
        actual_draw_number=actual_draw_number,
        source_url=source_url,
        http_status=http_status,
        outcome=outcome,
        validation_mode=validation_mode,
        result_sha256=result_sha256,
        error_message=message,
        response_html=response_html,
    )

    if increment_attempt:
        _increment_attempt_if_existing(db, requested_draw_number)

    return TotoRunResult(
        outcome=outcome,
        requested_draw_number=requested_draw_number,
        actual_draw_number=actual_draw_number,
        validation_mode=validation_mode,
        message=message,
    )


def _write_audit_safely(
    db: Session,
    *,
    requested_draw_number: int,
    actual_draw_number: Optional[int],
    source_url: str,
    http_status: Optional[int],
    outcome: str,
    validation_mode: str,
    result_sha256: Optional[str],
    error_message: Optional[str],
    response_html: Optional[str],
) -> None:
    try:
        write_attempt(
            db,
            requested_draw_number=requested_draw_number,
            actual_draw_number=actual_draw_number,
            source_url=source_url,
            http_status=http_status,
            outcome=outcome,
            validation_mode=validation_mode,
            result_sha256=result_sha256,
            error_message=error_message,
            response_html=response_html,
        )
    except SQLAlchemyError:
        db.rollback()
        logger.exception("failed to write toto audit row")


def _increment_attempt_if_existing(db: Session, draw_number: int) -> None:
    try:
        increment_scrape_attempt(db, draw_number)
    except SQLAlchemyError:
        db.rollback()
        logger.exception("failed to increment toto scrape attempt")


def _release_lock_safely(db: Session) -> None:
    try:
        release_lock(db)
    except SQLAlchemyError:
        logger.exception("failed to release toto advisory lock")
        db.rollback()
