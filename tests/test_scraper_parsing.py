from datetime import datetime
from pathlib import Path

from app.scraper import _parse_draw


FIXTURES_DIR = Path(__file__).resolve().parents[1] / "mocks"


def _load_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def _parse_fixture(name: str, draw_no: int):
    parsed = _parse_draw(_load_fixture(name), draw_no)
    assert parsed is not None
    return parsed


def test_parse_all_groups_have_winners():
    result, is_complete = _parse_fixture("toto_4043_all.html", 4043)

    assert is_complete is True
    assert result.draw_number == 4043
    assert result.draw_date == datetime(2025, 1, 13)
    assert result.winning_numbers == [3, 7, 11, 13, 34, 35]
    assert result.additional_number == 17
    assert result.jackpot == 6088704.0

    assert len(result.winning_shares) == 7
    assert result.winning_shares[0].amount == 3044352.0
    assert result.winning_shares[0].count == 2
    assert result.winning_shares[1].amount == 91930.0
    assert result.winning_shares[1].count == 7

    assert result.group1_result.has_winner is True
    assert result.group1_result.winning_count == 2
    assert result.group1_result.prize_amount == 3044352.0
    assert len(result.group1_result.winning_tickets) == 2
    assert result.group1_result.snowball_amount is None

    assert result.group2_result.has_winner is True
    assert result.group2_result.winning_count == 7
    assert result.group2_result.prize_amount == 91930.0
    assert len(result.group2_result.winning_tickets) == 7
    assert result.group2_result.snowball_amount is None


def test_parse_group2_has_no_winner_snowball():
    result, is_complete = _parse_fixture("toto_4003_no_g2.html", 4003)

    assert is_complete is True

    assert result.group1_result.has_winner is True
    assert result.group1_result.snowball_amount is None
    assert len(result.group1_result.winning_tickets) == 1
    assert result.group1_result.prize_amount == 1248227.0
    assert result.group1_result.winning_count == 1

    assert result.group2_result.has_winner is False
    assert result.group2_result.snowball_amount == 262784.0
    assert len(result.group2_result.winning_tickets) == 0
    assert result.group2_result.prize_amount == 0
    assert result.group2_result.winning_count == 0


def test_parse_group1_and_group2_have_no_winner():
    result, is_complete = _parse_fixture("toto_4014_no_g1_g2.html", 4014)

    assert is_complete is True

    assert result.group1_result.has_winner is False
    assert result.group1_result.snowball_amount == 1227298.0
    assert len(result.group1_result.winning_tickets) == 0
    assert result.group1_result.prize_amount == 0
    assert result.group1_result.winning_count == 0

    assert result.group2_result.has_winner is False
    assert result.group2_result.snowball_amount == 258378.0
    assert len(result.group2_result.winning_tickets) == 0
    assert result.group2_result.prize_amount == 0
    assert result.group2_result.winning_count == 0


def test_parse_group2_with_itoto_locations():
    result, is_complete = _parse_fixture("toto_4042_no_g1.html", 4042)

    assert is_complete is True

    assert result.group1_result.has_winner is False
    assert result.group1_result.snowball_amount == 3032056.0
    assert result.group1_result.prize_amount == 0
    assert result.group1_result.winning_count == 0

    assert result.group2_result.has_winner is True
    assert result.group2_result.prize_amount == 75163.0
    assert result.group2_result.winning_count == 5
    assert len(result.group2_result.winning_tickets) == 5

    itoto_ticket = next(
        ticket for ticket in result.group2_result.winning_tickets if ticket.is_itoto
    )
    assert itoto_ticket.outlet_name == "iTOTO - System 12"
    assert itoto_ticket.entry_type == "iTOTO - System 12"
    assert len(itoto_ticket.itoto_locations) == 18
    assert all(location.share_count == 1 for location in itoto_ticket.itoto_locations)


def test_parse_draw_number_mismatch_returns_none():
    parsed = _parse_draw(_load_fixture("toto_4043_all.html"), 4044)
    assert parsed is None


def test_parse_missing_winning_outlets_sets_incomplete():
    html = _load_fixture("toto_4043_all.html").replace(
        'class="divWinningOutlets"',
        'class="divWinningOutletsMissing"',
        1,
    )

    parsed = _parse_draw(html, 4043)
    assert parsed is not None
    result, is_complete = parsed

    assert is_complete is False
    assert result.group1_result.has_winner is False
    assert result.group2_result.has_winner is False
    assert len(result.group1_result.winning_tickets) == 0
    assert len(result.group2_result.winning_tickets) == 0
    assert result.group1_result.prize_amount == 3044352.0
    assert result.group2_result.prize_amount == 91930.0
    assert result.group1_result.winning_count == 2
    assert result.group2_result.winning_count == 7


def test_parse_missing_winning_shares_sets_incomplete():
    html = _load_fixture("toto_4043_all.html").replace(
        'class="table table-striped tableWinningShares"',
        'class="table table-striped tableWinningSharesMissing"',
        1,
    )

    parsed = _parse_draw(html, 4043)
    assert parsed is not None
    result, is_complete = parsed

    assert is_complete is False
    assert result.winning_shares == []
    assert result.group1_result.prize_amount is None
    assert result.group2_result.prize_amount is None
    assert result.group1_result.winning_count == 0
    assert result.group2_result.winning_count == 0


def test_parse_missing_jackpot_sets_incomplete():
    html = _load_fixture("toto_4043_all.html").replace(
        'class="jackpotPrize"',
        'class="jackpotPrizeMissing"',
        1,
    )

    parsed = _parse_draw(html, 4043)
    assert parsed is not None
    result, is_complete = parsed

    assert is_complete is False
    assert result.jackpot is None


def test_parse_missing_one_winning_number_returns_partial_numbers():
    html = _load_fixture("toto_4043_all.html").replace(
        'class="win6"',
        'class="win6Missing"',
        1,
    )

    parsed = _parse_draw(html, 4043)
    assert parsed is not None
    result, is_complete = parsed

    assert is_complete is True
    assert result.winning_numbers == [3, 7, 11, 13, 34]
