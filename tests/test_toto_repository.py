from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.toto import repository
from app.toto.models import TotoDraw, TotoScrapeAttempt
from app.toto.types import (
    ParsedGroupResult,
    ParsedTotoDraw,
    ParsedWinningShare,
    ParsedWinningTicket,
)


def _parsed_draw(draw_number: int = 4043) -> ParsedTotoDraw:
    parsed = ParsedTotoDraw(
        requested_draw_number=draw_number,
        actual_draw_number=draw_number,
        draw_date=date(2025, 1, 13),
        winning_numbers=[3, 7, 11, 13, 34, 35],
        additional_number=17,
        jackpot=6088704.0,
        winning_shares=[ParsedWinningShare(group=1, amount=3044352.0, count=2)],
    )
    parsed.group1_result = ParsedGroupResult(
        has_winner=True,
        winning_tickets=[
            ParsedWinningTicket(
                outlet_name="Outlet A",
                outlet_address="Address A",
                entry_type="QuickPick",
                is_itoto=False,
            )
        ],
    )
    parsed.group2_result = ParsedGroupResult()
    parsed.is_complete = True
    return parsed


def test_get_latest_draw_number_returns_zero_when_empty():
    db = MagicMock()
    db.execute.return_value.scalar.return_value = None

    assert repository.get_latest_draw_number(db) == 0


def test_get_latest_draw_number_returns_max_value():
    db = MagicMock()
    db.execute.return_value.scalar.return_value = 4043

    assert repository.get_latest_draw_number(db) == 4043


def test_upsert_draw_requires_identity_fields():
    db = MagicMock()
    parsed = ParsedTotoDraw(requested_draw_number=1)

    with pytest.raises(ValueError):
        repository.upsert_draw(db, parsed)


def test_upsert_draw_existing_row_updates_fields(monkeypatch):
    db = MagicMock()
    parsed = _parsed_draw()
    existing = SimpleNamespace(
        draw_date=date(2024, 1, 1),
        winning_numbers=[1, 2, 3, 4, 5, 6],
        additional_number=10,
        jackpot=100.0,
        has_winning_shares=False,
        has_winning_outlets=False,
        has_jackpot=False,
        is_complete=False,
        scrape_attempt_count=2,
        last_scrape_attempt_at=None,
        updated_at=None,
    )

    monkeypatch.setattr(repository, "get_draw", lambda _db, _draw_no: existing)
    save_calls = []
    monkeypatch.setattr(
        repository,
        "_save_group_data",
        lambda db_obj, draw_number, parsed_draw: save_calls.append(
            (db_obj, draw_number, parsed_draw)
        ),
    )

    repository.upsert_draw(db, parsed)

    assert existing.draw_date == parsed.draw_date
    assert existing.winning_numbers == parsed.winning_numbers
    assert existing.additional_number == parsed.additional_number
    assert existing.jackpot == parsed.jackpot
    assert existing.has_winning_shares is True
    assert existing.has_winning_outlets is True
    assert existing.has_jackpot is True
    assert existing.is_complete is True
    assert existing.scrape_attempt_count == 3
    assert existing.last_scrape_attempt_at is not None
    assert existing.updated_at is not None
    assert db.execute.call_count == 3
    db.flush.assert_called_once()
    db.commit.assert_called_once()
    assert save_calls == [(db, parsed.actual_draw_number, parsed)]


def test_upsert_draw_new_row_adds_draw(monkeypatch):
    db = MagicMock()
    parsed = _parsed_draw()
    monkeypatch.setattr(repository, "get_draw", lambda _db, _draw_no: None)
    save_calls = []
    monkeypatch.setattr(
        repository,
        "_save_group_data",
        lambda db_obj, draw_number, parsed_draw: save_calls.append(
            (db_obj, draw_number, parsed_draw)
        ),
    )

    repository.upsert_draw(db, parsed)

    added = db.add.call_args.args[0]
    assert isinstance(added, TotoDraw)
    assert added.draw_number == parsed.actual_draw_number
    assert added.winning_numbers == parsed.winning_numbers
    assert added.additional_number == parsed.additional_number
    assert added.jackpot == parsed.jackpot
    assert added.scrape_attempt_count == 1
    assert added.last_scrape_attempt_at is not None
    db.flush.assert_called_once()
    db.commit.assert_called_once()
    assert save_calls == [(db, parsed.actual_draw_number, parsed)]


def test_increment_scrape_attempt_skips_when_draw_missing(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(repository, "get_draw", lambda _db, _draw_no: None)

    repository.increment_scrape_attempt(db, 4043)

    db.commit.assert_not_called()


def test_increment_scrape_attempt_updates_existing_draw(monkeypatch):
    db = MagicMock()
    draw = SimpleNamespace(scrape_attempt_count=4, last_scrape_attempt_at=None, updated_at=None)
    monkeypatch.setattr(repository, "get_draw", lambda _db, _draw_no: draw)

    repository.increment_scrape_attempt(db, 4043)

    assert draw.scrape_attempt_count == 5
    assert draw.last_scrape_attempt_at is not None
    assert draw.updated_at is not None
    db.commit.assert_called_once()


def test_write_attempt_returns_false_when_suppressed(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(repository, "should_insert_attempt", lambda *_args, **_kwargs: False)

    inserted = repository.write_attempt(
        db,
        requested_draw_number=4043,
        actual_draw_number=4043,
        source_url="https://example.test",
        http_status=200,
        outcome="fetch_error",
        validation_mode="current",
        result_sha256=None,
        response_html="<html/>",
    )

    assert inserted is False
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_write_attempt_stores_response_html(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(repository, "should_insert_attempt", lambda *_args, **_kwargs: True)

    inserted = repository.write_attempt(
        db,
        requested_draw_number=4043,
        actual_draw_number=4043,
        source_url="https://example.test",
        http_status=200,
        outcome="success",
        validation_mode="past",
        result_sha256="abc123",
        error_message=None,
        response_html="<html>archive</html>",
    )

    assert inserted is True
    saved = db.add.call_args.args[0]
    assert isinstance(saved, TotoScrapeAttempt)
    assert saved.response_html == "<html>archive</html>"
    assert saved.validation_mode == "past"
    db.commit.assert_called_once()
