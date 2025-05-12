from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import SnowballInfo, TotoResult, WinningShare, WinningTicket
from app.schemas import (
    DrawDetailsSchema,
    DrawResultSchema,
    ItotoLocationSchema,
    SnowballInfoSchema,
    WinningShareSchema,
    WinningTicketSchema,
)

router = APIRouter(tags=["Draws"])


@router.get("/")
async def root():
    return {"message": "TT4D API"}


@router.get("/draws/latest", response_model=DrawResultSchema)
async def get_latest_draw(db: Session = Depends(get_db)):
    result = db.query(TotoResult).order_by(TotoResult.draw_date.desc()).first()
    if not result:
        raise HTTPException(status_code=404, detail="No draws found")
    
    shares = (
        db.query(WinningShare)
        .filter(WinningShare.draw_number == result.draw_number)
        .all()
    )
    return get_draw_result_extra(db, result, shares)


@router.get("/draws/{draw_number}", response_model=DrawDetailsSchema)
async def get_draw(draw_number: int, db: Session = Depends(get_db)):
    # Get the draw result
    result = db.query(TotoResult).filter(TotoResult.draw_number == draw_number).first()
    if not result:
        raise HTTPException(status_code=404, detail="Draw not found")

    # Get winning shares
    shares = (
        db.query(WinningShare).filter(WinningShare.draw_number == draw_number).all()
    )

    # Get snowball info
    snowballs = (
        db.query(SnowballInfo).filter(SnowballInfo.draw_number == draw_number).all()
    )

    # Get winning tickets
    tickets = (
        db.query(WinningTicket)
        .options(selectinload(WinningTicket.itoto_locations))
        .filter(WinningTicket.draw_number == draw_number)
        .all()
    )

    processed_tickets = []

    for ticket in tickets:
        if ticket.is_itoto:
            # For iTOTO tickets
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
            # For regular tickets
            processed_tickets.append(
                WinningTicketSchema(
                    group_number=ticket.group_number,
                    outlet_name=ticket.outlet_name,
                    address=ticket.outlet_address,
                    entry_type=ticket.entry_type,
                    is_itoto=False,
                )
            )

    return DrawDetailsSchema(
        draw_result=DrawResultSchema.model_validate(
            get_draw_result_extra(db, result, shares)
        ),
        winning_shares=[WinningShareSchema.model_validate(share) for share in shares],
        snowball_info=[
            SnowballInfoSchema.model_validate(snowball) for snowball in snowballs
        ],
        winning_tickets=processed_tickets,
    )


@router.get("/draws", response_model=List[DrawResultSchema])
async def get_draws(
    skip: int = 0,
    limit: int = 10,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    query = db.query(TotoResult)

    if start_date:
        query = query.filter(TotoResult.draw_date >= start_date)
    if end_date:
        query = query.filter(TotoResult.draw_date <= end_date)

    results = (
        query.order_by(TotoResult.draw_date.desc()).offset(skip).limit(limit).all()
    )

    draw_results = []

    for result in results:
        shares = (
            db.query(WinningShare)
            .filter(WinningShare.draw_number == result.draw_number)
            .all()
        )
        draw_results.append(get_draw_result_extra(db, result, shares))

    return draw_results


def get_draw_result_extra(db, result, shares):
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
        jackpot=result.jackpot if result.jackpot is not None else 0.0,
        total_winners=total_winners,
        total_prize=total_prize,
    )


@router.get("/search")
async def search_numbers(
    numbers: str = Query(
        ..., description="Space-separated numbers to search for (e.g., '12 13 14')"
    ),
    db: Session = Depends(get_db),
):
    # Convert input string to list of integers
    input_numbers = [int(n) for n in numbers.split()]

    # Validate inputs
    if not all(1 <= n <= 49 for n in input_numbers):
        raise ValueError("All numbers must be between 1 and 49")
    if len(input_numbers) > 6:
        raise ValueError("Search must not be more than 6 numbers")
    if len(set(input_numbers)) != len(input_numbers):
        raise ValueError("Numbers must not repeat")

    query = (
        select(TotoResult)
        .where(TotoResult.winning_numbers.contains(input_numbers))
        .order_by(TotoResult.draw_date.desc())
    )

    results = db.execute(query).scalars().all()
    return results
