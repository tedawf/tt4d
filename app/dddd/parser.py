import re
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup

from app.dddd.types import ParsedDdddDraw

DRAW_NO_RE = re.compile(r"Draw\s+No\.\s*(\d+)")
FOUR_DIGIT_RE = re.compile(r"^[0-9]{4}$")


def parse_dddd_html(html: str, requested_draw_number: int) -> ParsedDdddDraw:
    parsed = ParsedDdddDraw(requested_draw_number=requested_draw_number)

    if not html:
        parsed.parse_errors.append("empty_html")
        return parsed

    soup = BeautifulSoup(html, "html.parser")
    single_draw = soup.find("div", class_="divSingleDraw")
    if not single_draw:
        parsed.parse_errors.append("missing_divSingleDraw")
        return parsed

    draw_number_text = _text_or_none(single_draw.find("th", class_="drawNumber"))
    if draw_number_text is None:
        parsed.parse_errors.append("missing_draw_number")
    else:
        parsed.actual_draw_number = _parse_draw_number(draw_number_text)
        if parsed.actual_draw_number is None:
            parsed.parse_errors.append("invalid_draw_number")

    draw_date_text = _text_or_none(single_draw.find("th", class_="drawDate"))
    if draw_date_text is None:
        parsed.parse_errors.append("missing_draw_date")
    else:
        parsed.draw_date = _parse_draw_date(draw_date_text)
        if parsed.draw_date is None:
            parsed.parse_errors.append("invalid_draw_date")

    parsed.first = _extract_prize_number(single_draw, "tdFirstPrize")
    parsed.second = _extract_prize_number(single_draw, "tdSecondPrize")
    parsed.third = _extract_prize_number(single_draw, "tdThirdPrize")

    for name, value in [("first", parsed.first), ("second", parsed.second), ("third", parsed.third)]:
        if value is None:
            parsed.parse_errors.append(f"missing_{name}_prize")

    parsed.starter = _extract_prize_list(single_draw, "tbodyStarterPrizes")
    parsed.consolation = _extract_prize_list(single_draw, "tbodyConsolationPrizes")

    return parsed


def validate_parsed_draw(parsed: ParsedDdddDraw, strict: bool) -> list[str]:
    errors: list[str] = []

    if parsed.actual_draw_number is None:
        errors.append("actual_draw_number_required")

    if parsed.draw_date is None:
        errors.append("draw_date_required")

    for name, value in [("first", parsed.first), ("second", parsed.second), ("third", parsed.third)]:
        if value is None:
            errors.append(f"{name}_required")
        elif not FOUR_DIGIT_RE.match(value):
            errors.append(f"{name}_not_4_digit")

    for prize in parsed.all_prizes():
        if not FOUR_DIGIT_RE.match(prize):
            errors.append(f"invalid_prize_number:{prize}")

    if strict:
        if len(parsed.starter) != 10:
            errors.append(f"starter_count_expected_10_got_{len(parsed.starter)}")
        if len(parsed.consolation) != 10:
            errors.append(f"consolation_count_expected_10_got_{len(parsed.consolation)}")

    return errors


def _text_or_none(node) -> Optional[str]:
    if node is None:
        return None
    value = node.get_text(strip=True)
    return value if value else None


def _parse_draw_number(value: str) -> Optional[int]:
    match = DRAW_NO_RE.search(value)
    if not match:
        return None
    return int(match.group(1))


def _parse_draw_date(value: str):
    try:
        return datetime.strptime(value, "%a, %d %b %Y").date()
    except ValueError:
        return None


def _extract_prize_number(single_draw, css_class: str) -> Optional[str]:
    value = _text_or_none(single_draw.find("td", class_=css_class))
    if value is None:
        return None
    return value


def _extract_prize_list(single_draw, tbody_class: str) -> list[str]:
    tbody = single_draw.find("tbody", class_=tbody_class)
    if not tbody:
        return []

    prizes: list[str] = []
    for td in tbody.find_all("td"):
        text = td.get_text(strip=True)
        if text:
            prizes.append(text)
    return prizes
