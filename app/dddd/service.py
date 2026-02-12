import logging
import os
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.dddd.client import fetch_dddd_html
from app.dddd.parser import parse_dddd_html, validate_parsed_draw
from app.dddd.repository import (
    draw_exists,
    get_next_draw_number,
    insert_draw_and_prizes,
    release_lock,
    replace_draw_and_prizes,
    try_acquire_lock,
    write_audit,
)
from app.dddd.types import DdddRunResult

logger = logging.getLogger(__name__)


def is_strict_mode() -> bool:
    return os.getenv("DDDD_STRICT", "true").strip().lower() == "true"


def run_fetch_next(db: Session, strict: bool) -> DdddRunResult:
    lock_acquired = try_acquire_lock(db)
    if not lock_acquired:
        return DdddRunResult(
            outcome="skipped_locked",
            requested_draw_number=-1,
            message="another dddd fetch job is running",
        )

    try:
        requested_draw_number = get_next_draw_number(db)
        return _run_fetch(db, requested_draw_number, strict=strict, replay=False)
    finally:
        try:
            release_lock(db)
        except SQLAlchemyError:
            logger.exception("failed to release dddd advisory lock")
            db.rollback()


def run_fetch_replay(db: Session, draw_number: int, strict: bool) -> DdddRunResult:
    lock_acquired = try_acquire_lock(db)
    if not lock_acquired:
        return DdddRunResult(
            outcome="skipped_locked",
            requested_draw_number=draw_number,
            message="another dddd fetch job is running",
        )

    try:
        return _run_fetch(db, draw_number, strict=strict, replay=True)
    finally:
        try:
            release_lock(db)
        except SQLAlchemyError:
            logger.exception("failed to release dddd advisory lock")
            db.rollback()


def _run_fetch(
    db: Session,
    requested_draw_number: int,
    *,
    strict: bool,
    replay: bool,
) -> DdddRunResult:
    fetch_result = fetch_dddd_html(requested_draw_number)
    response_html = fetch_result.html

    if fetch_result.error_message:
        _write_audit_safely(
            db,
            requested_draw_number=requested_draw_number,
            actual_draw_number=None,
            source_url=fetch_result.source_url,
            http_status=fetch_result.http_status,
            outcome="fetch_error",
            error_message=fetch_result.error_message,
            response_html=response_html,
        )
        return DdddRunResult(
            outcome="fetch_error",
            requested_draw_number=requested_draw_number,
            message=fetch_result.error_message,
        )

    if fetch_result.http_status is None or fetch_result.http_status >= 400:
        _write_audit_safely(
            db,
            requested_draw_number=requested_draw_number,
            actual_draw_number=None,
            source_url=fetch_result.source_url,
            http_status=fetch_result.http_status,
            outcome="fetch_error",
            error_message=f"http_status_{fetch_result.http_status}",
            response_html=response_html,
        )
        return DdddRunResult(
            outcome="fetch_error",
            requested_draw_number=requested_draw_number,
            message=f"http error status {fetch_result.http_status}",
        )

    parsed = parse_dddd_html(response_html or "", requested_draw_number)

    if parsed.actual_draw_number is None:
        parse_error_message = ";".join(parsed.parse_errors) if parsed.parse_errors else "missing_actual_draw_number"
        _write_audit_safely(
            db,
            requested_draw_number=requested_draw_number,
            actual_draw_number=None,
            source_url=fetch_result.source_url,
            http_status=fetch_result.http_status,
            outcome="parse_error",
            error_message=parse_error_message,
            response_html=response_html,
        )
        return DdddRunResult(
            outcome="parse_error",
            requested_draw_number=requested_draw_number,
            message=parse_error_message,
        )

    if parsed.actual_draw_number < requested_draw_number:
        return DdddRunResult(
            outcome="no_new_draw",
            requested_draw_number=requested_draw_number,
            actual_draw_number=parsed.actual_draw_number,
            message="latest available draw is still behind requested draw",
        )

    if parsed.actual_draw_number > requested_draw_number:
        mismatch = (
            f"requested_draw_number_{requested_draw_number}_actual_draw_number_{parsed.actual_draw_number}"
        )
        _write_audit_safely(
            db,
            requested_draw_number=requested_draw_number,
            actual_draw_number=parsed.actual_draw_number,
            source_url=fetch_result.source_url,
            http_status=fetch_result.http_status,
            outcome="sequence_mismatch",
            error_message=mismatch,
            response_html=response_html,
        )
        return DdddRunResult(
            outcome="sequence_mismatch",
            requested_draw_number=requested_draw_number,
            actual_draw_number=parsed.actual_draw_number,
            message=mismatch,
        )

    if parsed.parse_errors:
        parse_error_message = ";".join(parsed.parse_errors)
        _write_audit_safely(
            db,
            requested_draw_number=requested_draw_number,
            actual_draw_number=parsed.actual_draw_number,
            source_url=fetch_result.source_url,
            http_status=fetch_result.http_status,
            outcome="parse_error",
            error_message=parse_error_message,
            response_html=response_html,
        )
        return DdddRunResult(
            outcome="parse_error",
            requested_draw_number=requested_draw_number,
            actual_draw_number=parsed.actual_draw_number,
            message=parse_error_message,
        )

    validation_errors = validate_parsed_draw(parsed, strict=strict)
    if validation_errors:
        validation_error_message = ";".join(validation_errors)
        _write_audit_safely(
            db,
            requested_draw_number=requested_draw_number,
            actual_draw_number=parsed.actual_draw_number,
            source_url=fetch_result.source_url,
            http_status=fetch_result.http_status,
            outcome="validation_error",
            error_message=validation_error_message,
            response_html=response_html,
        )
        return DdddRunResult(
            outcome="validation_error",
            requested_draw_number=requested_draw_number,
            actual_draw_number=parsed.actual_draw_number,
            message=validation_error_message,
        )

    try:
        if replay:
            replace_draw_and_prizes(db, parsed)
        else:
            if draw_exists(db, requested_draw_number):
                _write_audit_safely(
                    db,
                    requested_draw_number=requested_draw_number,
                    actual_draw_number=parsed.actual_draw_number,
                    source_url=fetch_result.source_url,
                    http_status=fetch_result.http_status,
                    outcome="already_exists",
                    error_message="draw already exists",
                    response_html=response_html,
                )
                return DdddRunResult(
                    outcome="already_exists",
                    requested_draw_number=requested_draw_number,
                    actual_draw_number=parsed.actual_draw_number,
                    message="draw already exists",
                )
            insert_draw_and_prizes(db, parsed)

        _write_audit_safely(
            db,
            requested_draw_number=requested_draw_number,
            actual_draw_number=parsed.actual_draw_number,
            source_url=fetch_result.source_url,
            http_status=fetch_result.http_status,
            outcome="success",
            error_message=None,
            response_html=response_html,
        )
        return DdddRunResult(
            outcome="success",
            requested_draw_number=requested_draw_number,
            actual_draw_number=parsed.actual_draw_number,
            message="draw persisted",
        )
    except SQLAlchemyError as exc:
        db.rollback()
        _write_audit_safely(
            db,
            requested_draw_number=requested_draw_number,
            actual_draw_number=parsed.actual_draw_number,
            source_url=fetch_result.source_url,
            http_status=fetch_result.http_status,
            outcome="db_error",
            error_message=str(exc),
            response_html=response_html,
        )
        return DdddRunResult(
            outcome="db_error",
            requested_draw_number=requested_draw_number,
            actual_draw_number=parsed.actual_draw_number,
            message=str(exc),
        )


def _write_audit_safely(
    db: Session,
    *,
    requested_draw_number: int,
    actual_draw_number: Optional[int],
    source_url: str,
    http_status: Optional[int],
    outcome: str,
    error_message: Optional[str],
    response_html: Optional[str],
) -> None:
    try:
        write_audit(
            db,
            requested_draw_number=requested_draw_number,
            actual_draw_number=actual_draw_number,
            source_url=source_url,
            http_status=http_status,
            outcome=outcome,
            error_message=error_message,
            response_html=response_html,
        )
    except SQLAlchemyError:
        db.rollback()
        logger.exception("failed to write dddd audit row")
