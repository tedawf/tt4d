import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from pytz import timezone

from db.database import SessionLocal
from db.queries import get_latest_draw_number, save_draw
from scheduler.scraper import fetch_draw

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_new_draw():
    db = SessionLocal()
    try:
        latest_draw_number = get_latest_draw_number(db)
        next_draw_number = latest_draw_number + 1
        current_time = datetime.now(timezone("Asia/Singapore")).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        logger.info(f"[{current_time}] Checking for draw {next_draw_number}...")

        latest_draw_result = fetch_draw(db, next_draw_number)
        if latest_draw_result:
            try:
                if save_draw(db, latest_draw_result):
                    logger.info(f"Successfully saved new draw {next_draw_number}")
                else:
                    logger.error(f"Failed to save draw {next_draw_number}")
            finally:
                db.close()
        else:
            logger.info(f"No new draw data available.")
    finally:
        db.close()


if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone=timezone("Asia/Singapore"))
    scheduler.add_job(
        fetch_new_draw,
        trigger="cron",
        day_of_week="mon,thu,fri",
        hour="18-23",  # From 6PM to 11PM
        minute="*/5",  # Every 5 minutes
        misfire_grace_time=300,  # Allow job to be run up to 5 minutes late
    )

    # Run an immediate check on startup
    logger.info("Running initial check on startup...")
    fetch_new_draw()

    try:
        logger.info("Scheduler starting...")
        scheduler.start()
        logger.info(
            "Scheduler started. Will run every 5 minutes on Monday and Thursday between 6PM-12AM"
        )
    except (KeyboardInterrupt, SystemExit):
        logger.info("Received shutdown signal")
        scheduler.shutdown()
        logger.info("Scheduler shut down successfully")
    except Exception as e:
        logger.error(f"Unexpected error in scheduler: {str(e)}", exc_info=True)
        raise
