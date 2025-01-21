import logging
import sys
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from pytz import timezone

from scheduler.database import get_latest_draw_number, save_draw
from scheduler.scraper import fetch_draw

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],  # This ensures logs go to docker logs
)
logger = logging.getLogger(__name__)


def fetch_latest_draw():
    latest_draw_number = get_latest_draw_number()
    if latest_draw_number is None:
        logger.error("Error: Could not determine latest draw number")
        return

    next_draw_number = latest_draw_number + 1
    current_time = datetime.now(timezone("Asia/Singapore")).strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    logger.info(f"[{current_time}] Checking for draw {next_draw_number}...")

    latest_draw_result = fetch_draw(next_draw_number)
    if latest_draw_result:
        if save_draw(latest_draw_result):
            logger.info(f"Successfully saved new draw {next_draw_number}")
        else:
            logger.error(f"Failed to save draw {next_draw_number}")
    else:
        logger.info(f"No new draw data available.")


if __name__ == "__main__":
    logger.info("Scheduler started. Press Ctrl+C to exit")

    scheduler = BlockingScheduler(timezone=timezone("Asia/Singapore"))
    scheduler.add_job(
        fetch_latest_draw,
        trigger="cron",
        day_of_week="mon,thu",
        hour="18-23",  # From 6PM to 11PM
        minute="*/5",  # Every 5 minutes
        misfire_grace_time=300,  # Allow job to be run up to 5 minutes late
    )

    logger.info("Will run every 5 minutes on Monday and Thursday between 6PM-12AM")

    # Run an immediate check on startup
    logger.info("Running initial check on startup...")
    fetch_latest_draw()

    try:
        logger.info("Scheduler starting...")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Received shutdown signal")
        scheduler.shutdown()
        logger.info("Scheduler shut down successfully")
    except Exception as e:
        logger.error(f"Unexpected error in scheduler: {str(e)}", exc_info=True)
        raise
