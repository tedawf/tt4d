import time

from scheduler.database import save_draw
from scheduler.scraper import fetch_draw


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

            time.sleep(1)  # Be nice to the server
        except Exception as e:
            print(f"Error processing draw {draw_no}: {e}")
            import traceback

            traceback.print_exc()  # This will print the full error trace


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Invalid arguments: Please input 2 start and end draw numbers!")
        exit()
    else:
        start = int(sys.argv[1])

        if len(sys.argv) == 2:
            end = int(sys.argv[1])
        else:
            end = int(sys.argv[2])

        # Check valid
        if end < start:
            print("End draw number cannot be before start draw number!")
            exit()

        populate_past_draws(start, end)
