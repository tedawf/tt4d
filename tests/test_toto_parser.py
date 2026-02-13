from datetime import date
from pathlib import Path

from app.toto.parser import parse_toto_html, validate_parsed_draw


SAMPLES_DIR = Path(__file__).resolve().parents[1] / "samples"


def _load_fixture(name: str) -> str:
    return (SAMPLES_DIR / name).read_text(encoding="utf-8")


def _parse_fixture(name: str, draw_no: int):
    return parse_toto_html(_load_fixture(name), draw_no)


def test_parse_all_groups_have_winners():
    result = _parse_fixture("toto_4043_all.html", 4043)

    assert result.is_complete is True
    assert result.actual_draw_number == 4043
    assert result.draw_date == date(2025, 1, 13)
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
    result = _parse_fixture("toto_4003_no_g2.html", 4003)

    assert result.is_complete is True

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
    result = _parse_fixture("toto_4014_no_g1_g2.html", 4014)

    assert result.is_complete is True

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
    result = _parse_fixture("toto_4042_no_g1.html", 4042)

    assert result.is_complete is True

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


def test_parse_draw_number_mismatch_returns_actual_draw_number():
    parsed = parse_toto_html(_load_fixture("toto_4043_all.html"), 4044)
    assert parsed.requested_draw_number == 4044
    assert parsed.actual_draw_number == 4043


def test_parse_missing_winning_outlets_sets_incomplete():
    html = _load_fixture("toto_4043_all.html").replace(
        'class="divWinningOutlets"',
        'class="divWinningOutletsMissing"',
        1,
    )

    result = parse_toto_html(html, 4043)

    assert result.is_complete is False
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

    result = parse_toto_html(html, 4043)

    assert result.is_complete is False
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

    result = parse_toto_html(html, 4043)

    assert result.is_complete is False
    assert result.jackpot is None


def test_parse_missing_one_winning_number_returns_partial_numbers():
    html = _load_fixture("toto_4043_all.html").replace(
        'class="win6"',
        'class="win6Missing"',
        1,
    )

    result = parse_toto_html(html, 4043)

    assert result.is_complete is True
    assert result.winning_numbers == [3, 7, 11, 13, 34]


def test_validate_past_mode_accepts_five_winning_numbers():
    html = _load_fixture("toto_4043_all.html").replace(
        'class="win6"',
        'class="win6Missing"',
        1,
    )
    parsed = parse_toto_html(html, 4043)

    assert validate_parsed_draw(parsed, validation_mode="past") == []


def test_validate_current_mode_requires_six_winning_numbers():
    html = _load_fixture("toto_4043_all.html").replace(
        'class="win6"',
        'class="win6Missing"',
        1,
    )
    parsed = parse_toto_html(html, 4043)

    assert "winning_numbers_expected_6_got_5" in validate_parsed_draw(
        parsed, validation_mode="current"
    )
