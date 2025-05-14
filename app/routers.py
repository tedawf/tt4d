import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

import app.queries as queries
from app.database import SessionLocal, get_db
from app.models import SnowballInfo, TotoResult, WinningShare, WinningTicket
from app.schemas import (
    DrawDetailsSchema,
    DrawResultSchema,
    ItotoLocationSchema,
    ScrapeRequestSchema,
    ScrapeResultSchema,
    ScrapeTaskStatus,
    SnowballInfoSchema,
    WinningShareSchema,
    WinningTicketSchema,
)
from app.scraper import fetch_draw

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Draws"])


@router.get("/draws/latest", response_model=DrawResultSchema)
async def get_latest_draw(db: Session = Depends(get_db)):
    """Fetches the most recent lottery result by draw date"""
    query = (
        select(TotoResult)
        .options(selectinload(TotoResult.winning_shares))
        .order_by(desc(TotoResult.draw_date))
    )
    result = db.execute(query).scalars().first()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No draws found"
        )

    shares = result.winning_shares

    return get_draw_result_extra(result, shares)


@router.get("/draws/{draw_number}", response_model=DrawDetailsSchema)
async def get_draw(draw_number: int, db: Session = Depends(get_db)):
    """Fetches all the draw details for a given draw number"""
    result_query = select(TotoResult).where(TotoResult.draw_number == draw_number)
    result = db.execute(result_query).scalars().first()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Draw ({draw_number}) not found",
        )

    shares_query = select(WinningShare).where(WinningShare.draw_number == draw_number)
    shares = db.execute(shares_query).scalars().all()

    snowballs_query = select(SnowballInfo).where(
        SnowballInfo.draw_number == draw_number
    )
    snowballs = db.execute(snowballs_query).scalars().all()

    tickets_query = (
        select(WinningTicket)
        .options(selectinload(WinningTicket.itoto_locations))
        .where(WinningTicket.draw_number == draw_number)
    )
    tickets = db.execute(tickets_query).scalars().all()

    processed_tickets = _process_winning_tickets(tickets)

    return DrawDetailsSchema(
        draw_result=get_draw_result_extra(result, shares),
        winning_shares=[WinningShareSchema.model_validate(s) for s in shares],
        snowball_info=[SnowballInfoSchema.model_validate(sb) for sb in snowballs],
        winning_tickets=processed_tickets,
    )


def _process_winning_tickets(tickets: List[WinningTicket]) -> List[WinningTicketSchema]:
    processed_tickets = []
    for ticket in tickets:
        if ticket.is_itoto:
            itoto_locations_schema = []
            if ticket.itoto_locations:
                for loc in ticket.itoto_locations:
                    itoto_locations_schema.append(
                        ItotoLocationSchema(
                            outlet_name=loc.outlet_name,
                            address=loc.outlet_address,
                            share_count=loc.share_count,
                        )
                    )

            processed_tickets.append(
                WinningTicketSchema(
                    group_number=ticket.group_number,
                    outlet_name="iTOTO - System 12",
                    address="",
                    entry_type=ticket.entry_type,
                    is_itoto=True,
                    itoto_locations=itoto_locations_schema,
                )
            )
        else:
            # Not itoto tickets
            processed_tickets.append(
                WinningTicketSchema(
                    group_number=ticket.group_number,
                    outlet_name=ticket.outlet_name,
                    address=ticket.outlet_address,
                    entry_type=ticket.entry_type,
                    is_itoto=False,
                )
            )

    return processed_tickets


@router.get("/draws", response_model=List[DrawResultSchema])
async def get_draws(
    skip: int = 0,
    limit: int = 10,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    query = select(TotoResult)

    if start_date:
        query = query.where(TotoResult.draw_date >= start_date)
    if end_date:
        query = query.where(TotoResult.draw_date <= end_date)

    results_query = (
        query.options(selectinload(TotoResult.winning_shares))  # Eager load shares
        .order_by(desc(TotoResult.draw_date))
        .offset(skip)
        .limit(limit)
    )

    results = db.execute(results_query).scalars().all()

    draw_results = []
    for result in results:
        shares = result.winning_shares
        draw_results.append(get_draw_result_extra(result, shares))

    return draw_results


def get_draw_result_extra(
    result: TotoResult, shares: List[WinningShare]
) -> DrawResultSchema:
    total_winners = sum(share.winner_count for share in shares) if shares else 0
    total_prize = (
        sum(share.winner_count * share.share_amount for share in shares)
        if shares
        else 0.0
    )

    return DrawResultSchema(
        draw_number=result.draw_number,
        draw_date=result.draw_date,
        winning_numbers=result.winning_numbers,
        additional_number=result.additional_number,
        jackpot=result.jackpot,
        total_winners=total_winners,
        total_prize=total_prize,
    )


@router.get("/search")
async def search_numbers(
    numbers: str = Query(
        ...,
        description="Space-separated numbers to search for (e.g., '12 13 14')",
        min_length=1,
        pattern=r"^\d+( \d+)*$",  # Ensure space-separated digits
    ),
    db: Session = Depends(get_db),
):
    # Convert input string to list of integers
    try:
        input_numbers = [int(n) for n in numbers.split()]
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input: Numbers must be space-separated integers",
        )

    # Validate inputs
    if not input_numbers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide at least one number to search",
        )
    if not all(1 <= n <= 49 for n in input_numbers):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All numbers must be between 1 and 49",
        )
    if len(input_numbers) > 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search must not be more than 6 numbers",
        )
    if len(set(input_numbers)) != len(input_numbers):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Numbers must not repeat",
        )

    query = (
        select(TotoResult)
        .options(selectinload(TotoResult.winning_shares))
        .where(TotoResult.winning_numbers.contains(input_numbers))
        .order_by(desc(TotoResult.draw_date))
    )

    results = db.execute(query).scalars().all()

    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No draws found"
        )

    draw_results = []
    for result in results:
        shares = result.winning_shares
        draw_results.append(get_draw_result_extra(result, shares))

    return draw_results


@router.post("/scrape", response_model=ScrapeResultSchema, tags=["Scraping"])
async def trigger_scrape(
    request: ScrapeRequestSchema,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
):
    target_draw_number = request.draw_number
    rescrape = request.force_scrape

    if target_draw_number is None:
        try:
            latest_draw_number = queries.get_latest_draw_number(db)
            target_draw_number = latest_draw_number + 1
            logger.info(
                f"Scrape requested with no draw number provided. Latest: ({latest_draw_number}), trying: ({target_draw_number})"
            )
        except Exception as e:
            logger.error(f"Unexpected error while getting latest draw number: {e}")
            return ScrapeResultSchema(
                message="Failed to start scrape task due to server error",
                status=ScrapeTaskStatus.FAILED_TO_INITIATE,
                target_draw_number=None,
            )
    else:
        logger.info(f"Scrape requested for draw number: ({target_draw_number})")

    # Check if trying to scrape existing draw
    if not rescrape:
        try:
            existing_draw = queries.get_draw(db, target_draw_number)
            if existing_draw:
                logger.info(
                    f"Draw ({target_draw_number}) already exists. Scrape task will not be started"
                )
                return ScrapeResultSchema(
                    message=f"Failed to start scrape task as draw ({target_draw_number}) already exists",
                    status=ScrapeTaskStatus.ALREADY_EXISTS,
                    target_draw_number=target_draw_number,
                )
        except Exception as e:
            logger.error(
                f"Unexpected error while getting draw ({target_draw_number}): {e}"
            )
            return ScrapeResultSchema(
                message="Failed to start scrape task due to server error",
                status=ScrapeTaskStatus.FAILED_TO_INITIATE,
                target_draw_number=None,
            )

    background_tasks.add_task(_scrape_task, target_draw_number)

    return ScrapeResultSchema(
        message=f"Started scrape task for draw {target_draw_number} in the background",
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
