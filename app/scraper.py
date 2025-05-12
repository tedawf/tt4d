import base64
import logging
import re
from datetime import datetime
from typing import List, Optional

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.parsing_types import (
    ParsedDrawResult,
    ParsedGroupResult,
    ParsedItotoLocation,
    ParsedWinningShare,
    ParsedWinningTicket,
)
from app.queries import get_html_content, save_html_content

logger = logging.getLogger(__name__)

BASE_URL = "https://www.singaporepools.com.sg/en/product/sr/Pages/toto_results.aspx"


def fetch_draw(db: Session, draw_no: int):
    """Fetch TOTO draw results from db, if not website"""

    # First check if we already have the html content
    html_content = get_html_content(db, draw_no)
    if html_content:
        logger.info(f"Using cached HTML for draw {draw_no}")
        try:
            result = _parse_draw(html_content, draw_no)
            return result
        except Exception:
            logger.exception(
                f"Error parsing cached HTML for draw {draw_no}. Will attempt to re-fetch."
            )

    logger.info(f"Fetching draw {draw_no} from website...")
    draw_str = f"DrawNumber={draw_no}"
    encoded_draw_no = base64.b64encode(draw_str.encode()).decode()
    url = f"{BASE_URL}?sppl={encoded_draw_no}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        raw_html = response.text.strip()
        result = _parse_draw(raw_html, draw_no)

        if not result:
            logger.warning(f"No data successfully parsed for draw {draw_no}")
            return None

        # Store the raw HTML
        save_success = save_html_content(db, draw_no, raw_html)
        if save_success:
            logger.info(f"HTML content for draw {draw_no} saved successfully")
        else:
            logger.error(f"Failed to save HTML content for draw {draw_no}")

        return result

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error fetching draw {draw_no}: {e}")
        return None
    except requests.exceptions.Timeout:
        logger.error(f"Timeout while fetching draw {draw_no}")
        return None
    except requests.exceptions.RequestException as e:
        # Catch other network related errors
        logger.error(f"Request failed for draw {draw_no}: {e}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error during fetch for draw {draw_no}: {e}")
        return None


def _parse_draw(html_content: str, given_draw_no) -> Optional[ParsedDrawResult]:
    """Parse TOTO draw results from HTML content."""
    if not html_content:
        logger.warning(
            f"Attempted to parse empty HTML content for draw {given_draw_no}."
        )
        return None

    try:
        # Get main result div
        soup = BeautifulSoup(html_content, "html.parser")
        result_div = soup.find("div", class_="divSingleDraw")
        if not result_div:
            logger.error(
                f"Could not find 'divSingleDraw' in HTML for draw {given_draw_no}. Page structure might have changed."
            )
            return None

        # Check draw number is same as given
        draw_number_th = result_div.find("th", class_="drawNumber")
        if not draw_number_th or not draw_number_th.text:
            logger.error(
                f"Could not find draw number element or text for draw {given_draw_no}."
            )
            return None
        draw_number_text = draw_number_th.text.strip()
        draw_number = _parse_draw_number(draw_number_text)
        if draw_number != int(given_draw_no):
            logger.warning(
                f"HTML draw number ({draw_number}) does not match requested draw number ({given_draw_no}). Skipping..."
            )
            return None

        # Get draw date
        draw_date_th = result_div.find("th", class_="drawDate")
        if not draw_date_th or not draw_date_th.text:
            logger.error(
                f"Could not find draw date element or text for draw {given_draw_no}."
            )
            return None
        draw_date_text = draw_date_th.text.strip()
        draw_date = _parse_date(draw_date_text)
        if not draw_date:
            logger.error(f"Failed to parse draw date for draw {given_draw_no}.")
            return None

        # Winning numbers
        winning_numbers = []
        for i in range(1, 7):
            number_td = result_div.find("td", class_=f"win{i}")
            if number_td and number_td.text:
                winning_numbers.append(int(number_td.text.strip()))
            else:
                logger.warning(
                    f"Could not find winning number win{i} for draw {given_draw_no}."
                )

        # Additional number
        additional_td = result_div.find("td", class_="additional")
        if not additional_td or not additional_td.text:
            logger.error(f"Could not find additional number for draw {given_draw_no}.")
            return None
        additional_number = int(additional_td.text.strip())

        # Get winning outlets
        group1_result = ParsedGroupResult()
        group2_result = ParsedGroupResult()

        winning_outlets_div = soup.find("div", class_="divWinningOutlets")
        if winning_outlets_div:
            group1_result, group2_result = _parse_group_results(winning_outlets_div)
        else:
            logger.warning(f"No 'divWinningOutlets' found for draw {given_draw_no}.")

        # Get winning shares (1194+)
        parsed_winning_shares = []
        winning_shares_table = result_div.find("table", class_="tableWinningShares")
        if winning_shares_table:
            parsed_winning_shares = _parse_winning_shares(winning_shares_table)

            if parsed_winning_shares and len(parsed_winning_shares) >= 2:
                if parsed_winning_shares[0]:  # Group 1 shares
                    group1_result.prize_amount = parsed_winning_shares[0].amount
                    group1_result.winning_count = parsed_winning_shares[0].count
                if parsed_winning_shares[1]:  # Group 2 shares
                    group2_result.prize_amount = parsed_winning_shares[1].amount
                    group2_result.winning_count = parsed_winning_shares[1].count
        else:
            logger.warning(f"No 'tableWinningShares' found for draw {given_draw_no}.")

        # Get group 1 prize (2995+)
        jackpot_td = result_div.find("td", class_="jackpotPrize")
        jackpot = None
        if jackpot_td and jackpot_td.text:
            jackpot = _parse_money_amount(jackpot_td.text.strip())
        else:
            logger.warning(f"No jackpot prize element found for draw {given_draw_no}.")

        return ParsedDrawResult(
            draw_date=draw_date,
            draw_number=draw_number,
            winning_numbers=winning_numbers,
            additional_number=additional_number,
            winning_shares=parsed_winning_shares,
            jackpot=jackpot,
            group1_result=group1_result,
            group2_result=group2_result,
        )

    except Exception as e:
        logger.exception(
            f"Unexpected error parsing draw results for draw {given_draw_no}: {e}"
        )
        return None


def _parse_winning_shares(shares_table: str) -> List[ParsedWinningShare]:
    winning_shares = []

    rows = shares_table.find_all("tr")[2:]  # Skip header rows
    for row in rows:
        cols = row.find_all("td")
        if len(cols) == 3:
            group = cols[0].text.strip().replace("Group ", "")
            amount = cols[1].text.strip()
            count = cols[2].text.strip()
            winning_shares.append(
                ParsedWinningShare(
                    group=int(group),
                    amount=_parse_money_amount(amount),
                    count=_parse_number(count),
                )
            )
    return winning_shares


def _parse_group_results(winning_outlets_div) -> tuple[ParsedGroupResult, ParsedGroupResult]:
    """
    Parse Group 1 and Group 2 results from the winning outlets div.
    """
    group1 = ParsedGroupResult()
    group2 = ParsedGroupResult()

    if not winning_outlets_div:
        return group1, group2

    try:
        # Check for snowball messages
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

        # Parse Group 1 winning tickets
        g1_tickets = []
        g1_section = winning_outlets_div.find(
            "p", string=lambda x: x and "Group 1 winning tickets sold at:" in x
        )
        if g1_section and g1_section.find_next("ul"):
            g1_tickets = _parse_winning_tickets(g1_section.find_next("ul"))

        group1.winning_tickets = g1_tickets
        group1.has_winner = bool(g1_tickets)

        # Parse Group 2
        g2_tickets = []
        g2_section = winning_outlets_div.find(
            "p", string=lambda x: x and "Group 2 winning tickets sold at:" in x
        )
        if g2_section and g2_section.find_next("ul"):
            g2_tickets = _parse_winning_tickets(g2_section.find_next("ul"))

        group2.winning_tickets = g2_tickets
        group2.has_winner = bool(g2_tickets)

    except Exception as e:
        print(f"Error parsing group results: {e}")
        print(f"Winning outlets div: {winning_outlets_div}")

    return group1, group2


def _parse_winning_tickets(ul) -> list:
    tickets = []
    ticket_order = 0

    if not ul:
        return tickets

    for li in ul.find_all("li", recursive=False):
        if not li or not li.text.strip():
            continue

        text = li.text.strip()
        ticket_order += 1

        # Check if its itoto ticket
        if text.startswith("iTOTO"):
            itoto_ticket = ParsedWinningTicket(
                outlet_name="iTOTO - System 12",
                outlet_address="-",
                entry_type="iTOTO - System 12",
                is_itoto=True,
            )

            # Parse all locations for this iTOTO ticket
            location_texts = []

            lines = li.get_text(separator="\n").strip().split("\n")

            # Skip first line
            for line in lines[1:]:
                line = line.strip()
                if line and "•" in line:
                    location_texts.append(line)

            # Parse each itoto location
            for idx, location_text in enumerate(location_texts):
                itoto_location = _parse_itoto_ticket(location_text)
                if itoto_location:
                    itoto_ticket.itoto_locations.append(itoto_location)

            tickets.append(itoto_ticket)

        else:
            parsed_tickets = _parse_regular_tickets(text)
            if parsed_tickets:
                tickets.extend(parsed_tickets)

    return tickets


def _parse_regular_tickets(location_text: str) -> List[ParsedWinningTicket]:
    result_tickets = []

    try:
        if not location_text or not isinstance(location_text, str):
            return result_tickets

        # Split by parentheses to get outlet address and entry type
        parts = location_text.split("(")
        if len(parts) < 2:
            return None

        outlet_part = parts[0].strip()
        outlet_name, outlet_address = _parse_address(outlet_part)

        # Remove parentheses
        entry_part = parts[-1].replace(")", "").strip()

        # Parse count and entry type
        count = 1
        entry_type = entry_part

        count_match = re.match(r"(\d+)\s+(.+)", entry_part)
        if count_match:
            count = int(count_match.group(1))
            entry_type = count_match.group(2).strip()

        # Create a ticket object for each share
        for _ in range(count):
            ticket = ParsedWinningTicket(
                outlet_name=outlet_name,
                outlet_address=outlet_address,
                entry_type=entry_type,
                is_itoto=False,
            )
            result_tickets.append(ticket)

        return result_tickets

    except Exception as e:
        print(f"Error parsing regular tickets: {e}")
        print(f"Location text: {location_text}")
        return result_tickets


def _parse_itoto_ticket(location_text: str) -> Optional[ParsedItotoLocation]:
    try:
        if not location_text or not isinstance(location_text, str):
            return None

        # Remove the bullet point and whitespace
        outlet_text = re.sub(r"^\s*•\s*", "", location_text, flags=re.MULTILINE)

        # Get share count
        share_count = 1
        share_match = re.search(r"\((\d+)\)$", location_text)
        if share_match:
            share_count = int(share_match.group(1))
            # Remove the share count from the text
            outlet_text = re.sub(r"\(\d+\)$", "", outlet_text).strip()

        outlet_name, outlet_address = _parse_address(outlet_text)

        return ParsedItotoLocation(
            outlet_name=outlet_name,
            outlet_address=outlet_address,
            share_count=share_count,
        )

    except Exception as e:
        print(f"Error parsing iTOTO location: {e}")
        print(f"Location text: {location_text}")
        return None


def _parse_address(location_str: str):
    location_str = location_str.strip()

    # it works cos of the last " - ", unit number no count
    parts = location_str.rsplit(" - ", 1)

    if len(parts) == 2:
        outlet_name, address = parts
    else:
        outlet_name, address = location_str, "-"  # No address found

    return outlet_name, address


def _parse_number(number_str):
    """Remove "," from numbers"""
    if number_str == "-":
        return 0
    return int(number_str.replace(",", ""))


def _parse_money_amount(amount_str):
    """Convert "$1,234,567" to decimal"""
    if amount_str == "-" or amount_str is None:
        return 0
    return float(amount_str.replace(",", "").replace("$", ""))


def _parse_date(date_str):
    """Convert "Thu, 01 Jan 2025" to datetime"""
    return datetime.strptime(date_str, "%a, %d %b %Y")


def _parse_draw_number(draw_str):
    """Extract draw number from "Draw No. 1234" """
    return int(draw_str.replace("Draw No. ", "").strip())


def print_group_result(group_name: str, result: ParsedGroupResult) -> None:
    """
    Print formatted group result information.
    """
    if not result:
        return

    print(f"\n{group_name} Results:")
    print("-" * 50)

    # Print basic information
    if result.has_winner:
        print(f"Winners: {result.winning_count:,}")
        if result.prize_amount:
            print(f"Prize Amount: ${result.prize_amount:,.2f}")
    else:
        print("No winners")
        if result.snowball_amount:
            print(f"Snowball Amount: ${result.snowball_amount:,.2f}")

    # Print winning tickets if any
    if result.winning_tickets and any(result.winning_tickets):
        print("\nWinning tickets sold at:")

        # Print regular tickets
        regular_tickets = [t for t in result.winning_tickets if not t.is_itoto]
        if regular_tickets:
            for ticket in regular_tickets:
                print(
                    f"{ticket.outlet_name} - {ticket.outlet_address} ( {ticket.entry_type} )"
                )

        # Print iTOTO tickets
        itoto_tickets = [t for t in result.winning_tickets if t.is_itoto]
        for ticket in itoto_tickets:
            print(ticket.entry_type)
            for loc in ticket.itoto_locations:
                bullet = "•"
                if loc.share_count > 1:
                    print(
                        f"{bullet} {loc.outlet_name} - {loc.outlet_address} ({loc.share_count})"
                    )
                else:
                    print(f"{bullet} {loc.outlet_name} - {loc.outlet_address}")


# Test scraper
if __name__ == "__main__":
    import sys

    from app.database import SessionLocal
    from app.queries import get_latest_draw_number

    print("Fetching results...")
    db = SessionLocal()

    try:

        # Get latest draw number if not provided
        if len(sys.argv) != 2:
            draw_number = get_latest_draw_number(db) + 1
        else:
            draw_number = sys.argv[1]

        result = fetch_draw(db, draw_number)

        if result:
            print("Parsing completed")
            print("\nResults:")
            print("Draw Date:", result.draw_date)
            print("Draw Number:", result.draw_number)
            print("Winning Numbers:", result.winning_numbers)
            print("Additional Number:", result.additional_number)

            if result.jackpot:
                print("Group 1 Prize:", f"${result.jackpot}")

            if result.winning_shares:
                print("\nWinning Shares:")
                for share in result.winning_shares:
                    print(
                        f"Group {share.group}: ${share.amount} ({share.count} winners)"
                    )
            if result.group1_result:
                print_group_result("Group 1", result.group1_result)
            if result.group2_result:
                print_group_result("Group 2", result.group2_result)

    finally:
        db.close()
