from datetime import datetime
from typing import Dict, Optional

import requests
from bs4 import BeautifulSoup


class TotoScraper:
    def __init__(self):
        self.base_url = (
            "https://www.singaporepools.com.sg/en/product/sr/Pages/toto_results.aspx"
        )

    def fetch_draw(self) -> Optional[Dict]:
        """Fetch and parse the latest TOTO draw result."""
        try:
            response = requests.get(self.base_url)
            if response.status_code == 200:
                print("Successfully fetched latest TOTO results")
                return self._parse_draw_result(response.text)
            else:
                print(f"Failed to fetch page: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error fetching page: {e}")
            return None

    def _parse_draw_result(self, html_content: str) -> Optional[Dict]:
        """Parse TOTO draw results from HTML content."""
        if not html_content:
            return None

        soup = BeautifulSoup(html_content, "html.parser")

        try:
            # Get main result div
            result_div = soup.find("div", class_="divSingleDraw")
            if not result_div:
                print("Could not find draw results div")
                return None

            # Get draw date and number
            draw_date = result_div.find("th", class_="drawDate").text.strip()
            draw_number = result_div.find("th", class_="drawNumber").text.strip()

            # Get winning numbers
            winning_numbers = []
            for i in range(1, 7):
                number = result_div.find("td", class_=f"win{i}")
                if number:
                    winning_numbers.append(int(number.text.strip()))

            # Get additional number
            additional_number = int(
                result_div.find("td", class_="additional").text.strip()
            )

            # Get group 1 prize
            jackpot = result_div.find("td", class_="jackpotPrize").text.strip()

            # Get winning shares
            shares_table = result_div.find("table", class_="tableWinningShares")
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
                                "amount": self._parse_money_amount(amount),
                                "count": self._parse_number(count),
                            }
                        )

            # Create result dict
            result = {
                "draw_date": self._parse_date(draw_date),
                "draw_number": self._parse_draw_number(draw_number),
                "winning_numbers": winning_numbers,
                "additional_number": additional_number,
                "group1_prize": self._parse_money_amount(jackpot),
                "winning_shares": winning_shares,
            }

            return result

        except Exception as e:
            print(f"Error parsing draw results: {e}")
            import traceback

            traceback.print_exc()  # This will print the full error trace
            return None

    def _parse_number(self, number_str):
        """Remove "," from numbers"""
        if number_str == "-":
            return 0
        return int(number_str.replace(",", ""))

    def _parse_money_amount(self, amount_str):
        """Convert "$1,234,567" to decimal"""
        if amount_str == "-":
            return 0
        return float(amount_str.replace(",", "").replace("$", ""))

    def _parse_date(self, date_str):
        """Convert "Thu, 01 Jan 2025" to datetime"""
        return datetime.strptime(date_str, "%a, %d %b %Y")

    def _parse_draw_number(self, draw_str):
        """Extract draw number from "Draw No. 1234" """
        return int(draw_str.replace("Draw No. ", "").strip())


# Test scraper
if __name__ == "__main__":
    scraper = TotoScraper()

    print("Parsing page...")
    result = scraper.fetch_draw()
    if result:
        print("✓ Parsing completed")
        print("\nParsed data:")
        print("Draw Date:", result["draw_date"])
        print("Draw Number:", result["draw_number"])
        print("Winning Numbers:", result["winning_numbers"])
        print("Additional Number:", result["additional_number"])
        print("Group 1 Prize:", result["group1_prize"])
        print("\nWinning Shares:")
        for share in result["winning_shares"]:
            print(
                f"Group {share['group']}: ${share['amount']} ({share['count']} winners)"
            )
    else:
        print("✗ Parsing failed")
