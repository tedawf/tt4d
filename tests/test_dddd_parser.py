from datetime import date
from pathlib import Path

from app.dddd.parser import parse_dddd_html, validate_parsed_draw


SAMPLES_DIR = Path(__file__).resolve().parents[1] / "samples"


def _read_sample(name: str) -> str:
    return (SAMPLES_DIR / name).read_text(encoding="utf-8")


def test_historical_draw_accepts_variable_counts_in_past_mode():
    parsed = parse_dddd_html(_read_sample("4d_505.html"), requested_draw_number=505)

    assert parsed.actual_draw_number == 505
    assert parsed.draw_date == date(1991, 3, 30)
    assert parsed.first == "4853"
    assert parsed.second == "9355"
    assert parsed.third == "6007"
    assert len(parsed.starter) == 8
    assert len(parsed.consolation) == 10

    assert validate_parsed_draw(parsed, validation_mode="past") == []


def test_historical_draw_fails_current_count_validation():
    parsed = parse_dddd_html(_read_sample("4d_505.html"), requested_draw_number=505)

    errors = validate_parsed_draw(parsed, validation_mode="current")
    assert "starter_count_expected_10_got_8" in errors
    assert "consolation_count_expected_10_got_10" not in errors


def test_live_draw_with_full_23_passes_current_validation():
    parsed = parse_dddd_html(_read_sample("4d_506.html"), requested_draw_number=506)

    assert parsed.actual_draw_number == 506
    assert parsed.draw_date == date(1991, 3, 31)
    assert len(parsed.starter) == 10
    assert len(parsed.consolation) == 10

    # Ensure leading zero prize strings remain normalized as 4-digit values.
    assert "0492" in parsed.starter
    assert "0622" in parsed.consolation

    assert validate_parsed_draw(parsed, validation_mode="current") == []
