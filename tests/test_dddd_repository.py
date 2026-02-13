from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.dddd import repository
from app.dddd.models import DdddDraw, DdddScrapeAttempt
from app.dddd.types import ParsedDdddDraw


def _parsed_draw(draw_number: int = 506) -> ParsedDdddDraw:
    return ParsedDdddDraw(
        requested_draw_number=draw_number,
        actual_draw_number=draw_number,
        draw_date=date(2025, 1, 13),
        first="1234",
        second="2345",
        third="3456",
        starter=["1001", "1002"],
        consolation=["2001", "2002"],
    )


def test_get_next_draw_number_defaults_to_one():
    db = MagicMock()
    db.execute.return_value.scalar.return_value = None

    assert repository.get_next_draw_number(db) == 1


def test_get_next_draw_number_uses_max_plus_one():
    db = MagicMock()
    db.execute.return_value.scalar.return_value = 506

    assert repository.get_next_draw_number(db) == 507


def test_draw_exists_true_when_scalar_present():
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = 506

    assert repository.draw_exists(db, 506) is True


def test_draw_exists_false_when_scalar_missing():
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = None

    assert repository.draw_exists(db, 506) is False


def test_insert_draw_and_prizes_adds_draw_and_rows(monkeypatch):
    db = MagicMock()
    parsed = _parsed_draw()
    sentinel_rows = [object(), object()]
    monkeypatch.setattr(repository, "_build_prize_rows", lambda *_args, **_kwargs: sentinel_rows)

    repository.insert_draw_and_prizes(db, parsed)

    added = db.add.call_args.args[0]
    assert isinstance(added, DdddDraw)
    assert added.draw_number == parsed.actual_draw_number
    assert added.draw_date == parsed.draw_date
    db.flush.assert_called_once()
    db.add_all.assert_called_once_with(sentinel_rows)
    db.commit.assert_called_once()


def test_replace_draw_and_prizes_updates_existing(monkeypatch):
    db = MagicMock()
    parsed = _parsed_draw()
    existing = SimpleNamespace(draw_date=date(2024, 1, 1), updated_at=None)
    db.get.return_value = existing
    sentinel_rows = [object()]
    monkeypatch.setattr(repository, "_build_prize_rows", lambda *_args, **_kwargs: sentinel_rows)

    repository.replace_draw_and_prizes(db, parsed)

    assert existing.draw_date == parsed.draw_date
    assert existing.updated_at is not None
    db.add.assert_not_called()
    db.execute.assert_called_once()
    db.add_all.assert_called_once_with(sentinel_rows)
    db.commit.assert_called_once()


def test_replace_draw_and_prizes_adds_when_missing(monkeypatch):
    db = MagicMock()
    parsed = _parsed_draw()
    db.get.return_value = None
    sentinel_rows = [object()]
    monkeypatch.setattr(repository, "_build_prize_rows", lambda *_args, **_kwargs: sentinel_rows)

    repository.replace_draw_and_prizes(db, parsed)

    added = db.add.call_args.args[0]
    assert isinstance(added, DdddDraw)
    assert added.draw_number == parsed.actual_draw_number
    db.execute.assert_called_once()
    db.add_all.assert_called_once_with(sentinel_rows)
    db.commit.assert_called_once()


def test_write_attempt_returns_false_when_suppressed(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(repository, "should_insert_attempt", lambda *_args, **_kwargs: False)

    inserted = repository.write_attempt(
        db,
        requested_draw_number=506,
        actual_draw_number=506,
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
        requested_draw_number=506,
        actual_draw_number=506,
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
    assert isinstance(saved, DdddScrapeAttempt)
    assert saved.response_html == "<html>archive</html>"
    assert saved.validation_mode == "past"
    db.commit.assert_called_once()


def test_build_prize_rows_requires_core_prizes():
    parsed = _parsed_draw()
    parsed.first = None

    with pytest.raises(ValueError):
        repository._build_prize_rows(506, parsed)
