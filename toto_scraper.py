import base64
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

from toto_models import DrawResult

base_url = "https://www.singaporepools.com.sg/en/product/sr/Pages/toto_results.aspx"


def fetch_draw(draw_no):
    """Fetch TOTO draw results"""
    draw_str = f"DrawNumber={draw_no}"
    encoded_draw_no = base64.b64encode(draw_str.encode()).decode()

    try:
        response = requests.get(f"{base_url}?sppl={encoded_draw_no}")
        if response.status_code == 200:
            print("Successfully fetched latest TOTO results")
            return response.text
        else:
            print(f"Failed to fetch page: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching page: {e}")
        return None


def parse_draw(html_content: str) -> Optional[DrawResult]:
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
        draw_number = result_div.find("th", class_="drawNumber").text.strip()

        # Winning numbers
        winning_numbers = []
        for i in range(1, 7):
            number = result_div.find("td", class_=f"win{i}")
            if number:
                winning_numbers.append(int(number.text.strip()))
        additional_number = int(result_div.find("td", class_="additional").text.strip())

        # Get winning shares (1194+)
        shares_table = result_div.find("table", class_="tableWinningShares")
        winning_shares = parse_winning_shares(shares_table)

        # Get group 1 prize (2995+)
        jackpot = result_div.find("td", class_="jackpotPrize")
        if jackpot:
            jackpot = jackpot.text.strip()

        # Create result dict
        result = {
            "draw_date": parse_date(draw_date),
            "draw_number": parse_draw_number(draw_number),
            "winning_numbers": winning_numbers,
            "additional_number": additional_number,
            "winning_shares": winning_shares,
            "jackpot": parse_money_amount(jackpot),
        }

        return DrawResult(
            draw_date=draw_date,
            draw_number=draw_number,
            winning_numbers=winning_numbers,
            additional_number=additional_number,
            winning_shares=winning_shares,
            jackpot=jackpot,
        )

    except Exception as e:
        print(f"Error parsing draw results: {e}")
        import traceback

        traceback.print_exc()  # This will print the full error trace
        return None


def parse_winning_shares(shares_table: str):
    winning_shares = []
    if shares_table:
        rows = shares_table.find_all("tr")[2:]  # Skip header rows
        for row in rows:
            cols = row.find_all("td")
            if len(cols) == 3:
                group = cols[0].text.strip().replace("Group ", "")
                amount = cols[1].text.strip()
                count = cols[2].text.strip()
                winning_shares.append(
                    {
                        "group": int(group),
                        "amount": parse_money_amount(amount),
                        "count": parse_number(count),
                    }
                )
    return winning_shares


def parse_number(number_str):
    """Remove "," from numbers"""
    if number_str == "-":
        return 0
    return int(number_str.replace(",", ""))


def parse_money_amount(amount_str):
    """Convert "$1,234,567" to decimal"""
    if amount_str == "-" or amount_str is None:
        return 0
    return float(amount_str.replace(",", "").replace("$", ""))


def parse_date(date_str):
    """Convert "Thu, 01 Jan 2025" to datetime"""
    return datetime.strptime(date_str, "%a, %d %b %Y")


def parse_draw_number(draw_str):
    """Extract draw number from "Draw No. 1234" """
    return int(draw_str.replace("Draw No. ", "").strip())


# Test scraper
if __name__ == "__main__":
    print("1. Fetching page...")
    page = fetch_draw("1001")

    if page:
        print("✓ Page fetched successfully")

        print("\n2. Parsing latest draw...")
        result = parse_draw(page)

        if result:
            print("✓ Parsing completed")
            print("\nParsed data:")
            print("Draw Date:", result.draw_date)
            print("Draw Number:", result.draw_number)
            print("Winning Numbers:", result.winning_numbers)
            print("Additional Number:", result.additional_number)

            if result.jackpot is not None:
                print("Group 1 Prize:", f"${result.jackpot}")

            if len(result.winning_shares) != 0:
                print("\nWinning Shares:")
                for share in result.winning_shares:
                    print(
                        f"Group {share['group']}: ${share['amount']} ({share['count']} winners)"
                    )
