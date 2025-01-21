from datetime import datetime
from pytz import timezone
from apscheduler.schedulers.blocking import BlockingScheduler

from scheduler.database import get_latest_draw_number, save_draw
from scheduler.scraper import fetch_draw


def fetch_latest_draw():
    latest_draw_number = get_latest_draw_number()
    if latest_draw_number is None:
        print("Error: Could not determine latest draw number")
        return

    next_draw_number = latest_draw_number + 1
    current_time = datetime.now(timezone("Asia/Singapore")).strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    print(f"[{current_time}] Checking for draw {next_draw_number}...")

    latest_draw_result = fetch_draw(next_draw_number)
    if latest_draw_result:
        if save_draw(latest_draw_result):
            print(f"Successfully saved new draw {next_draw_number}")
        else:
            print(f"Failed to save draw {next_draw_number}")
    else:
        print(f"No new draw data available.")


if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone=timezone("Asia/Singapore"))

    scheduler.add_job(
        fetch_latest_draw,
        trigger="cron",
        day_of_week="mon,thu",
        hour="18-23",  # From 6PM to 11PM
        minute="*/5",  # Every 5 minutes
        misfire_grace_time=300,  # Allow job to be run up to 5 minutes late
    )

    print("Scheduler started. Press Ctrl+C to exit")
    print("Will run every 5 minutes on Monday and Thursday between 6PM-12AM")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("\nScheduler shut down successfully")
