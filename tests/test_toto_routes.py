from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.toto import routes
from tests._fakes import FakeDB


def _share(group_number: int, share_amount: str, winner_count: int):
    return SimpleNamespace(
        group_number=group_number,
        share_amount=Decimal(share_amount),
        winner_count=winner_count,
    )


def _draw(draw_number: int, draw_date_value: date, shares):
    return SimpleNamespace(
        draw_number=draw_number,
        draw_date=draw_date_value,
        winning_numbers=[1, 2, 3, 4, 5, 6],
        additional_number=7,
        jackpot=Decimal("1000000.00"),
        is_complete=True,
        winning_shares=shares,
    )


def test_get_latest_draw_returns_404_when_empty():
    with pytest.raises(HTTPException) as exc_info:
        routes.get_latest_draw(db=FakeDB(execute_rows=[[]]))

    assert exc_info.value.status_code == 404


def test_get_draws_maps_totals_from_winning_shares():
    shares = [_share(1, "100.00", 2), _share(2, "50.00", 3)]
    row = _draw(4043, date(2025, 1, 13), shares)

    results = routes.get_draws(db=FakeDB(execute_rows=[[row]]))

    assert len(results) == 1
    assert results[0].draw_number == 4043
    assert results[0].total_winners == 5
    assert results[0].total_prize == 350.0


def test_search_numbers_rejects_duplicate_values():
    with pytest.raises(HTTPException) as exc_info:
        routes.search_numbers(numbers="1 1", db=FakeDB(execute_rows=[]))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Numbers must not repeat"


def test_get_draw_returns_404_when_missing():
    with pytest.raises(HTTPException) as exc_info:
        routes.get_draw(
            draw_number=4043,
            db=FakeDB(execute_rows=[[], [], []], get_row=None),
        )

    assert exc_info.value.status_code == 404
