import requests
from bs4 import BeautifulSoup


class TotoScraper:
    def __init__(self):
        self.base_url = (
            "https://www.singaporepools.com.sg/en/product/sr/Pages/toto_results.aspx"
        )

    def fetch_latest_draw(self):
        try:
            response = requests.get(self.base_url)
            if response.status_code == 200:
                print("Successfully fetched latest TOTO results")
                # add parsing logic later
                return True
            else:
                print(f"Failed to fetch page: {response.status_code}")
                return False
        except Exception as e:
            print(f"Error fetching page: {e}")
            return False


# Test scraper
if __name__ == "__main__":
    scraper = TotoScraper()
    scraper.fetch_latest_draw()
