import base64
import re
from datetime import datetime
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from toto_models import DrawResult, GroupResult, WinningLocation, WinningShare

BASE_URL = "https://www.singaporepools.com.sg/en/product/sr/Pages/toto_results.aspx"


def fetch_draw(draw_no):
    """Fetch TOTO draw results"""
    draw_str = f"DrawNumber={draw_no}"
    encoded_draw_no = base64.b64encode(draw_str.encode()).decode()

    try:
        response = requests.get(f"{BASE_URL}?sppl={encoded_draw_no}")
        if response.status_code == 200:
            print("Successfully fetched latest TOTO results")
            return _parse_draw(response.text)
        else:
            print(f"Failed to fetch page: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching page: {e}")
        return None


def _parse_draw(html_content: str) -> Optional[DrawResult]:
    """Parse TOTO draw results from HTML content."""
    if not html_content:
        return None

    try:
        # Get main result div
        soup = BeautifulSoup(html_content, "html.parser")
        result_div = soup.find("div", class_="divSingleDraw")
        if not result_div:
            print("Could not find draw results div")
            return None

        # Basic draw info
        draw_date = result_div.find("th", class_="drawDate").text.strip()
        if draw_date:
            draw_date = _parse_date(draw_date)
        draw_number = result_div.find("th", class_="drawNumber").text.strip()
        if draw_number:
            draw_number = _parse_draw_number(draw_number)

        # Winning numbers
        winning_numbers = []
        for i in range(1, 7):
            number = result_div.find("td", class_=f"win{i}")
            if number:
                winning_numbers.append(int(number.text.strip()))
        additional_number = int(result_div.find("td", class_="additional").text.strip())

        # Get winning outlets
        winning_outlets = soup.find("div", class_="divWinningOutlets")
        if winning_outlets:
            group1, group2 = _parse_group_results(winning_outlets)

        # Get winning shares (1194+)
        winning_shares = result_div.find("table", class_="tableWinningShares")
        if winning_shares:
            winning_shares = _parse_winning_shares(winning_shares)

            # Assign group winner count and prize amount
            group1.prize_amount = winning_shares[0].amount
            group1.winning_count = winning_shares[0].count
            group2.prize_amount = winning_shares[1].amount
            group2.winning_count = winning_shares[1].count

        # Get group 1 prize (2995+)
        jackpot = result_div.find("td", class_="jackpotPrize")
        if jackpot:
            jackpot = _parse_money_amount(jackpot.text.strip())

        return DrawResult(
            draw_date=draw_date,
            draw_number=draw_number,
            winning_numbers=winning_numbers,
            additional_number=additional_number,
            winning_shares=winning_shares,
            jackpot=jackpot,
            group1_result=group1,
            group2_result=group2,
        )

    except Exception as e:
        print(f"Error parsing draw results: {e}")
        import traceback

        traceback.print_exc()  # This will print the full error trace
        return None


def _parse_winning_shares(shares_table: str) -> List[WinningShare]:
    winning_shares = []

    rows = shares_table.find_all("tr")[2:]  # Skip header rows
    for row in rows:
        cols = row.find_all("td")
        if len(cols) == 3:
            group = cols[0].text.strip().replace("Group ", "")
            amount = cols[1].text.strip()
            count = cols[2].text.strip()
            winning_shares.append(
                WinningShare(
                    group=int(group),
                    amount=_parse_money_amount(amount),
                    count=_parse_number(count),
                )
            )
    return winning_shares


def _parse_winning_location(
    location_text: str, is_itoto: bool = False, itoto_system: str = ""
) -> Optional[WinningLocation]:
    """
    Parse a location text into a WinningLocation object.

    Args:
        location_text: The text to parse
        is_itoto: Whether this is an iTOTO location
        itoto_system: The iTOTO system type (e.g., "System 12")
    """
    try:
        if not location_text or not isinstance(location_text, str):
            return None

        if is_itoto:
            # For iTOTO locations, get the full outlet name and append iTOTO system
            outlet_name = location_text.replace("•", "").strip()
            entry_type = f"iTOTO - {itoto_system}"
        else:
            # Split by parentheses
            parts = location_text.split("(")
            if len(parts) < 2:
                return None

            # Get everything before the parentheses as outlet name
            outlet_name = parts[0].strip()
            outlet_name = outlet_name.replace(
                " - -", ""
            )  # Handle case: Singapore Pools Account Betting Service - -

            # Get entry type from within parentheses
            entry_type = parts[-1].replace(")", "").strip()

        return WinningLocation(outlet_name, entry_type)

    except Exception as e:
        print(f"Error parsing winning location: {e}")
        print(f"Location text: {location_text}")
        return None


def _parse_group_results(winning_outlets_div) -> tuple[GroupResult, GroupResult]:
    """
    Parse Group 1 and Group 2 results from the winning outlets div.
    """
    group1 = GroupResult()
    group2 = GroupResult()

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

        # Parse Group 1 winning locations
        g1_locations = []
        g1_section = winning_outlets_div.find(
            "p", string=lambda x: x and "Group 1 winning tickets sold at:" in x
        )
        if g1_section and g1_section.find_next("ul"):
            for li in g1_section.find_next("ul").find_all("li"):
                if not li or not li.text:
                    continue

                text = li.text.strip()
                if "iTOTO" in text:
                    # Extract system type from the iTOTO header
                    system_type = (
                        text.split("-")[1].strip() if "-" in text else "Unknown"
                    )
                    # Parse each iTOTO outlet
                    for line in text.split("\n"):
                        if "•" in line:
                            location = _parse_winning_location(
                                line, is_itoto=True, itoto_system=system_type
                            )
                            if location:
                                g1_locations.append(location)
                else:
                    location = _parse_winning_location(text)
                    if location:
                        g1_locations.append(location)

        group1.winning_locations = g1_locations
        group1.has_winner = bool(g1_locations)

        # Parse Group 2 winning locations (similar logic)
        g2_locations = []
        g2_section = winning_outlets_div.find(
            "p", string=lambda x: x and "Group 2 winning tickets sold at:" in x
        )
        if g2_section and g2_section.find_next("ul"):
            for li in g2_section.find_next("ul").find_all("li"):
                if not li or not li.text:
                    continue

                text = li.text.strip()
                if "iTOTO" in text:
                    system_type = (
                        text.split("-")[1].strip() if "-" in text else "Unknown"
                    )
                    for line in text.split("\n"):
                        if "•" in line:
                            location = _parse_winning_location(
                                line, is_itoto=True, itoto_system=system_type
                            )
                            if location:
                                g2_locations.append(location)
                else:
                    location = _parse_winning_location(text)
                    if location:
                        g2_locations.append(location)

        group2.winning_locations = g2_locations
        group2.has_winner = bool(g2_locations)

    except Exception as e:
        print(f"Error parsing group results: {e}")
        print(f"Winning outlets div: {winning_outlets_div}")

    return group1, group2


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


def print_group_result(group_name: str, result: GroupResult) -> None:
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

    # Print winning locations if any
    if result.winning_locations and any(result.winning_locations):
        print("\nWinning Locations:")
        for loc in result.winning_locations:
            if loc:  # Check if location is not None
                print(f"• {loc.outlet_name} ({loc.entry_type})")


# Test scraper
if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        result = fetch_draw(9999)
    else:
        result = fetch_draw(sys.argv[1])

    print("1. Fetching page...")

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
                print(f"Group {share.group}: ${share.amount} ({share.count} winners)")
        if result.group1_result:
            print_group_result("Group 1", result.group1_result)
        if result.group2_result:
            print_group_result("Group 2", result.group2_result)
