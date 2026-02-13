"""Toto HTML parser with best-effort recovery for partially published draws."""

import re
from typing import Optional

from bs4 import BeautifulSoup

from app.core.parser_utils import parse_draw_date, parse_draw_number, text_or_none
from app.toto.types import (
    ParsedGroupResult,
    ParsedItotoLocation,
    ParsedTotoDraw,
    ParsedWinningShare,
    ParsedWinningTicket,
)


def parse_toto_html(html_content: str, requested_draw_number: int) -> ParsedTotoDraw:
    """Parse a Toto draw page into a normalized structure.

    Missing core identity fields are reported in `parse_errors`.
    Missing late-published sections set `is_complete=False` so current-mode validation
    can fail without losing already parsed fields.
    """
    parsed = ParsedTotoDraw(requested_draw_number=requested_draw_number)

    if not html_content:
        parsed.parse_errors.append("empty_html")
        return parsed

    soup = BeautifulSoup(html_content, "html.parser")
    result_div = soup.find("div", class_="divSingleDraw")
    if not result_div:
        parsed.parse_errors.append("missing_divSingleDraw")
        return parsed

    draw_number_text = text_or_none(result_div.find("th", class_="drawNumber"))
    if not draw_number_text:
        parsed.parse_errors.append("missing_draw_number")
    else:
        parsed.actual_draw_number = parse_draw_number(draw_number_text)
        if parsed.actual_draw_number is None:
            parsed.parse_errors.append("invalid_draw_number")

    draw_date_text = text_or_none(result_div.find("th", class_="drawDate"))
    if not draw_date_text:
        parsed.parse_errors.append("missing_draw_date")
    else:
        draw_date = parse_draw_date(draw_date_text)
        if draw_date is None:
            parsed.parse_errors.append("invalid_draw_date")
        else:
            parsed.draw_date = draw_date

    for i in range(1, 7):
        number_td = result_div.find("td", class_=f"win{i}")
        if number_td and number_td.text:
            try:
                parsed.winning_numbers.append(int(number_td.text.strip()))
            except ValueError:
                parsed.parse_errors.append(f"invalid_win{i}")

    additional_td = result_div.find("td", class_="additional")
    if not additional_td or not additional_td.text:
        parsed.parse_errors.append("missing_additional_number")
    else:
        try:
            parsed.additional_number = int(additional_td.text.strip())
        except ValueError:
            parsed.parse_errors.append("invalid_additional_number")

    winning_outlets_div = soup.find("div", class_="divWinningOutlets")
    if winning_outlets_div:
        parsed.group1_result, parsed.group2_result = _parse_group_results(
            winning_outlets_div
        )
    else:
        # Winning outlets are sometimes published later than the main result table.
        parsed.is_complete = False

    winning_shares_table = result_div.find("table", class_="tableWinningShares")
    if winning_shares_table:
        parsed.winning_shares = _parse_winning_shares(winning_shares_table)
        if len(parsed.winning_shares) >= 2:
            parsed.group1_result.prize_amount = parsed.winning_shares[0].amount
            parsed.group1_result.winning_count = parsed.winning_shares[0].count
            parsed.group2_result.prize_amount = parsed.winning_shares[1].amount
            parsed.group2_result.winning_count = parsed.winning_shares[1].count
    else:
        # Keep partial data while flagging incomplete status for strict mode.
        parsed.is_complete = False

    jackpot_td = result_div.find("td", class_="jackpotPrize")
    if jackpot_td and jackpot_td.text:
        parsed.jackpot = _parse_money_amount(jackpot_td.text.strip())
    else:
        # Jackpot can lag behind during live updates.
        parsed.is_complete = False

    return parsed


def validate_parsed_draw(parsed: ParsedTotoDraw, validation_mode: str) -> list[str]:
    """Validate parsed Toto data.

    `current` requires complete publication state.
    `past` accepts partial historical pages while keeping core integrity checks.
    """
    errors: list[str] = []

    if parsed.actual_draw_number is None:
        errors.append("actual_draw_number_required")
    if parsed.draw_date is None:
        errors.append("draw_date_required")

    if validation_mode == "past":
        if len(parsed.winning_numbers) < 5:
            errors.append(
                f"winning_numbers_expected_at_least_5_got_{len(parsed.winning_numbers)}"
            )
    else:
        if len(parsed.winning_numbers) != 6:
            errors.append(f"winning_numbers_expected_6_got_{len(parsed.winning_numbers)}")

    if parsed.additional_number is None:
        errors.append("additional_number_required")

    if validation_mode == "current":
        if not parsed.is_complete:
            errors.append("incomplete_draw_data")
        if len(parsed.winning_shares) < 2:
            errors.append(
                f"winning_shares_expected_at_least_2_got_{len(parsed.winning_shares)}"
            )
        if parsed.jackpot is None:
            errors.append("jackpot_required")

    return errors


def _parse_winning_shares(shares_table) -> list[ParsedWinningShare]:
    winning_shares: list[ParsedWinningShare] = []
    rows = shares_table.find_all("tr")[2:]
    for row in rows:
        cols = row.find_all("td")
        if len(cols) != 3:
            continue
        group = cols[0].text.strip().replace("Group ", "")
        amount = cols[1].text.strip()
        count = cols[2].text.strip()
        try:
            winning_shares.append(
                ParsedWinningShare(
                    group=int(group),
                    amount=_parse_money_amount(amount),
                    count=_parse_number(count),
                )
            )
        except ValueError:
            continue
    return winning_shares


def _parse_group_results(
    winning_outlets_div,
) -> tuple[ParsedGroupResult, ParsedGroupResult]:
    group1 = ParsedGroupResult()
    group2 = ParsedGroupResult()

    snowball_messages = winning_outlets_div.find_all("strong")
    for msg in snowball_messages:
        if not msg or not msg.text:
            continue
        if "Group 1 has no winner" in msg.text:
            amount_match = re.search(r"\$([0-9,]+)", msg.text)
            if amount_match:
                group1.snowball_amount = _parse_money_amount(amount_match.group(0))
        elif "Group 2 has no winner" in msg.text:
            amount_match = re.search(r"\$([0-9,]+)", msg.text)
            if amount_match:
                group2.snowball_amount = _parse_money_amount(amount_match.group(0))

    g1_tickets: list[ParsedWinningTicket] = []
    g1_section = winning_outlets_div.find(
        "p", string=lambda x: x and "Group 1 winning tickets sold at:" in x
    )
    if g1_section and g1_section.find_next("ul"):
        g1_tickets = _parse_winning_tickets(g1_section.find_next("ul"))

    group1.winning_tickets = g1_tickets
    group1.has_winner = bool(g1_tickets)

    g2_tickets: list[ParsedWinningTicket] = []
    g2_section = winning_outlets_div.find(
        "p", string=lambda x: x and "Group 2 winning tickets sold at:" in x
    )
    if g2_section and g2_section.find_next("ul"):
        g2_tickets = _parse_winning_tickets(g2_section.find_next("ul"))

    group2.winning_tickets = g2_tickets
    group2.has_winner = bool(g2_tickets)
    return group1, group2


def _parse_winning_tickets(ul) -> list[ParsedWinningTicket]:
    tickets: list[ParsedWinningTicket] = []

    if not ul:
        return tickets

    for li in ul.find_all("li", recursive=False):
        if not li or not li.text.strip():
            continue

        text = li.text.strip()

        if text.startswith("iTOTO"):
            itoto_ticket = ParsedWinningTicket(
                outlet_name="iTOTO - System 12",
                outlet_address="-",
                entry_type="iTOTO - System 12",
                is_itoto=True,
            )

            lines = li.get_text(separator="\n").strip().split("\n")
            for line in lines[1:]:
                line = line.strip()
                if line and "•" in line:
                    itoto_location = _parse_itoto_ticket(line)
                    if itoto_location:
                        itoto_ticket.itoto_locations.append(itoto_location)

            tickets.append(itoto_ticket)
        else:
            tickets.extend(_parse_regular_tickets(text))

    return tickets


def _parse_regular_tickets(location_text: str) -> list[ParsedWinningTicket]:
    if not location_text or not isinstance(location_text, str):
        return []

    parts = location_text.split("(")
    if len(parts) < 2:
        return []

    outlet_part = parts[0].strip()
    outlet_name, outlet_address = _parse_address(outlet_part)
    entry_part = parts[-1].replace(")", "").strip()

    count = 1
    entry_type = entry_part

    count_match = re.match(r"(\d+)\s+(.+)", entry_part)
    if count_match:
        count = int(count_match.group(1))
        entry_type = count_match.group(2).strip()

    tickets: list[ParsedWinningTicket] = []
    for _ in range(count):
        tickets.append(
            ParsedWinningTicket(
                outlet_name=outlet_name,
                outlet_address=outlet_address,
                entry_type=entry_type,
                is_itoto=False,
            )
        )
    return tickets


def _parse_itoto_ticket(location_text: str) -> Optional[ParsedItotoLocation]:
    if not location_text or not isinstance(location_text, str):
        return None

    outlet_text = re.sub(r"^\s*•\s*", "", location_text, flags=re.MULTILINE)

    share_count = 1
    share_match = re.search(r"\((\d+)\)$", location_text)
    if share_match:
        share_count = int(share_match.group(1))
        outlet_text = re.sub(r"\(\d+\)$", "", outlet_text).strip()

    outlet_name, outlet_address = _parse_address(outlet_text)
    return ParsedItotoLocation(
        outlet_name=outlet_name,
        outlet_address=outlet_address,
        share_count=share_count,
    )


def _parse_address(location_str: str) -> tuple[str, str]:
    location_str = location_str.strip()
    parts = location_str.rsplit(" - ", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return location_str, "-"


def _parse_number(number_str: str) -> int:
    if number_str == "-":
        return 0
    return int(number_str.replace(",", ""))


def _parse_money_amount(amount_str: Optional[str]) -> float:
    if amount_str in {"-", None}:
        return 0
    return float(amount_str.replace(",", "").replace("$", ""))
