from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.dddd import routes
from tests._fakes import FakeDB


def _prize(tier: str, tier_idx: int, number: str):
    return SimpleNamespace(tier=tier, tier_idx=tier_idx, number=number)


def _draw(draw_number: int, draw_date_value: date, prizes):
    return SimpleNamespace(draw_number=draw_number, draw_date=draw_date_value, prizes=prizes)


def test_map_draw_result_sorts_tier_indexes():
    row = _draw(
        draw_number=506,
        draw_date_value=date(2024, 1, 2),
        prizes=[
            _prize("1", 1, "7777"),
            _prize("2", 1, "8888"),
            _prize("3", 1, "9999"),
            _prize("S", 2, "3002"),
            _prize("S", 1, "3001"),
            _prize("C", 2, "4002"),
            _prize("C", 1, "4001"),
        ],
    )

    result = routes._map_draw_result(row)

    assert result.draw_number == 506
    assert result.first == "7777"
    assert result.second == "8888"
    assert result.third == "9999"
    assert result.starter == ["3001", "3002"]
    assert result.consolation == ["4001", "4002"]


def test_get_draws_returns_mapped_rows():
    rows = [
        _draw(
            draw_number=601,
            draw_date_value=date(2025, 5, 1),
            prizes=[_prize("1", 1, "1111"), _prize("2", 1, "2222"), _prize("3", 1, "3333")],
        ),
        _draw(
            draw_number=602,
            draw_date_value=date(2025, 5, 3),
            prizes=[_prize("1", 1, "4444"), _prize("2", 1, "5555"), _prize("3", 1, "6666")],
        ),
    ]

    result = routes.get_draws(db=FakeDB(execute_rows=[rows]))

    assert len(result) == 2
    assert result[0].draw_number == 601
    assert result[1].draw_number == 602


def test_get_draw_returns_404_when_missing():
    with pytest.raises(HTTPException) as exc_info:
        routes.get_draw(draw_number=999, db=FakeDB(execute_rows=[[]]))

    assert exc_info.value.status_code == 404
