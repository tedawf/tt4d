import time

from database import save_draw
from toto_scraper import fetch_draw


def populate_past_draws(start: int, end: int):
    for draw_no in range(start, end + 1):
        try:
            print(f"Fetching draw {draw_no}...")
            draw_result = fetch_draw(draw_no)
            if draw_result:

                if save_draw(draw_result):
                    print(f"Successfully saved draw {draw_no}")
                else:
                    print(f"Failed to save draw {draw_no}")
            else:
                print(f"No data for draw {draw_no}")

            time.sleep(2)  # Be nice to the server
        except Exception as e:
            print(f"Error processing draw {draw_no}: {e}")
            import traceback

            traceback.print_exc()  # This will print the full error trace


if __name__ == "__main__":
    populate_past_draws(1193, 1194)
    populate_past_draws(2994, 2995)
