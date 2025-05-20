import logging
from datetime import date, datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

import app.queries as queries
from app.auth import api_key_auth
from app.database import SessionLocal, get_db
from app.schemas import ScrapeResultSchema, ScrapeTaskStatus
from app.scraper import fetch_draw

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Scraping"])

MAX_SCRAPE_ATTEMPTS = 10
MAX_SCRAPE_JOBS = 3


@router.post(
    "/task", response_model=ScrapeResultSchema, dependencies=[Depends(api_key_auth)]
)
async def trigger_scrape_task(
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
):
    try:
        # 1. Check for any incomplete draws
        incomplete_draws = queries.get_incomplete_toto_results(
            db, limit=1, max_attempts=MAX_SCRAPE_ATTEMPTS
        )
        if incomplete_draws:
            logger.info("Found incomplete draws, adding scrape task")
        else:
            # No incomplete tasks, check if we already have today's results
            latest_draw_number = queries.get_latest_draw_number(db)
            latest_draw = queries.get_draw(db, latest_draw_number)

            if latest_draw and latest_draw.is_complete:
                today_date = date.today()
                # today_date = date(2025, 5, 13) # for testing
                if latest_draw.draw_date.date() == today_date:
                    logger.info(
                        f"Results for today ({today_date}) already exists ({latest_draw_number})"
                    )
                    return ScrapeResultSchema(
                        message="Scrape skipped: Results for today already available",
                        status=ScrapeTaskStatus.ALREADY_EXISTS,
                        target_draw_number=latest_draw_number,
                    )
                else:
                    logger.info("Latest draw is not today")
            else:
                logger.info("Latest draw is incomplete or missing")

        logger.info(f"Starting scrape task for draw")
        background_tasks.add_task(_scrape_task, MAX_SCRAPE_ATTEMPTS, MAX_SCRAPE_JOBS)

        return ScrapeResultSchema(
            message=f"Started scrape task in the background",
            status=ScrapeTaskStatus.INITIATED,
        )

    except Exception as e:
        logger.error(f"Error in scraping prechecks: {e}")
        return ScrapeResultSchema(
            message="Failed to start scrape task due to server error",
            status=ScrapeTaskStatus.FAILED_TO_INITIATE,
            target_draw_number=-1,
        )


def _scrape_task(max_attempts: int = 3, max_jobs: int = 1):
    task_name = f"[TASK-{datetime.now().strftime('%Y%m%d%H%M%S%f')}]"  #  uuid for logs
    logger.info(
        f"{task_name} Starting. Max Attempts Per Draw: ({max_attempts}), Max Incomplete Batch Size: ({max_jobs})"
    )

    # Background task should manage its own db session
    task_db: Session = SessionLocal()
    try:
        # 1. Determine all the draws to attempt in this run
        draws_to_attempt = set()

        # 1a. Check for new draw
        latest_draw_number = queries.get_latest_draw_number(task_db)
        new_draw_number = latest_draw_number + 1
        draws_to_attempt.add(new_draw_number)
        logger.info(f"{task_name} New draw number: ({new_draw_number})")

        # 1b. Check for incomplete draws
        incomplete_draws = queries.get_incomplete_toto_results(
            task_db, limit=max_jobs, max_attempts=max_attempts
        )
        if incomplete_draws:
            incomplete_draw_numbers = [res.draw_number for res in incomplete_draws]
            logger.info(
                f"{task_name} Found {len(incomplete_draws)} incomplete draws to retry: {incomplete_draw_numbers}"
            )
            for res in incomplete_draws:
                draws_to_attempt.add(res.draw_number)
        else:
            logger.info(f"{task_name} No incomplete draws found (that needs retry)")

        # Sort for consistent processing order (cos set)
        sorted_draws_to_attempt = sorted(list(draws_to_attempt))
        logger.info(
            f"{task_name} Final list of draws to attempt this run: {sorted_draws_to_attempt}"
        )

        # 2. Attempt all draws
        for draw_no in sorted_draws_to_attempt:
            logger.info(f"{task_name} Processing draw: ({draw_no})")

            # Check current status just before scraping
            existing_draw = queries.get_draw(task_db, draw_no)
            if existing_draw:
                if existing_draw.is_complete:
                    logger.info(
                        f"{task_name} Draw ({draw_no}) is already complete (re-checked). Skipping."
                    )
                    continue

                if existing_draw.scrape_attempt_count >= max_attempts:
                    logger.warning(
                        f"{task_name} Draw ({draw_no}) has reached max scrape attempts ({max_attempts}). Skipping."
                    )
                    continue

            # Actually we should force_fetch, but fetch_draw will try fetch newest data anyways
            scrape_attempt = fetch_draw(task_db, draw_no)
            if not scrape_attempt:
                logger.warning(
                    f"{task_name} fetch_draw returned None for draw ({draw_no}) Possibly missing?"
                )
                if existing_draw:
                    try:
                        logger.info(
                            f"{task_name} Incrementing attempt count for failed fetch/parse of existing draw ({draw_no})"
                        )
                        existing_draw.scrape_attempt_count = (
                            existing_draw.scrape_attempt_count or 0
                        ) + 1
                        existing_draw.last_scrape_attempt_at = datetime.now(
                            timezone.utc
                        )
                        task_db.commit()
                    except Exception as e_commit:
                        task_db.rollback()
                        logger.error(
                            f"{task_name} Failed to update attempt count for draw ({draw_no}) after fetch_draw failure: {e_commit}"
                        )

                # Might be new draw doesnt exist yet on website, will try next time
                continue

            result, is_complete = scrape_attempt

            save_successful = queries.save_or_update_draw(
                task_db, result, is_complete
            )
            if save_successful:
                logger.info(
                    f"{task_name} Successfully processed and saved/updated draw ({draw_no})"
                )

    except Exception as e:
        logger.exception(
            f"{task_name} An unexpected error occurred during the scraping: {e}"
        )
        if task_db.is_active:
            task_db.rollback()
    finally:
        if task_db:
            task_db.close()
        logger.info(f"{task_name} Task has finished")
