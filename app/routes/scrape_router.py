import logging
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

import app.queries as queries
from app.database import SessionLocal, get_db
from app.schemas import ScrapeRequestSchema, ScrapeResultSchema, ScrapeTaskStatus
from app.scraper import fetch_draw
from app.auth import api_key_auth

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Scraping"])


@router.post(
    "/", response_model=ScrapeResultSchema, dependencies=[Depends(api_key_auth)]
)
async def trigger_scrape(
    request: ScrapeRequestSchema,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
):
    try:
        latest_draw_number = queries.get_latest_draw_number(db)
        latest_draw = queries.get_draw(db, latest_draw_number)

        # Determine target draw number
        target_draw_number = request.draw_number or (latest_draw_number + 1)
        logger.info(f"Target draw number: {target_draw_number}")

        if not request.force_scrape:
            # Check if we already have today's results
            # today_date = date.today()
            today_date = date(2025, 5, 13)
            if latest_draw and latest_draw.draw_date.date() == today_date:
                logger.info(
                    f"Results for today ({today_date}) already exists ({latest_draw_number})"
                )
                return ScrapeResultSchema(
                    message="Scrape skipped: Results for today already available",
                    status=ScrapeTaskStatus.ALREADY_EXISTS,
                    target_draw_number=latest_draw_number,
                )

            # Check if requested draw already exists
            if target_draw_number <= latest_draw_number:
                logger.info(f"Draw ({target_draw_number}) already exists")
                return ScrapeResultSchema(
                    message=f"Scrape skipped: Draw {target_draw_number} already exists",
                    status=ScrapeTaskStatus.ALREADY_EXISTS,
                    target_draw_number=target_draw_number,
                )

    except Exception as e:
        logger.error(f"Error in scraping prechecks: {e}")
        return ScrapeResultSchema(
            message="Failed to start scrape task due to server error",
            status=ScrapeTaskStatus.FAILED_TO_INITIATE,
            target_draw_number=None,
        )

    logger.info(f"Starting scrape task for draw ({target_draw_number})")
    background_tasks.add_task(_scrape_task, target_draw_number)

    return ScrapeResultSchema(
        message=f"Started scrape task in the background",
        status=ScrapeTaskStatus.INITIATED,
        target_draw_number=target_draw_number,
    )


def _scrape_task(draw_number: int):
    logger.info(f"[TASK] Starting scrape task for draw ({draw_number})")

    # Background task should manage its own db session
    task_db: Session = SessionLocal()
    try:
        # 1. Scrape and parse the draw
        parsed_draw = fetch_draw(task_db, draw_number)
        if not parsed_draw:
            logger.warning(f"[TASK] Did not scrape draw ({draw_number})")
            return

        # 2. Save the parsed draw
        save_successful = queries.save_draw(task_db, parsed_draw)
        if save_successful:
            logger.info(f"[TASK] Successfully scraped and saved draw ({draw_number})")
        else:
            logger.warning(f"[TASK] Scraped but did not save draw ({draw_number})")

    except Exception as e:
        logger.exception(
            f"[TASK] Error occurred during scrape for draw ({draw_number}): {e}"
        )
    finally:
        task_db.close()
        logger.info(f"[TASK] Scrape task completed for draw ({draw_number})")
