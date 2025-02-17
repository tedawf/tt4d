from datetime import datetime
from typing import Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models import (
    DrawDetailsSchema,
    DrawResultSchema,
    SnowballInfoSchema,
    WinningLocationSchema,
    WinningShareSchema,
)
from db.database import get_db
from db.models import SnowballInfo, TotoResult, WinningLocation, WinningShare
from lib.parse_utils import split_outlet_address

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "TT4D API"}


@app.get("/draws/latest")
async def get_latest_draw(db: Session = Depends(get_db)):
    result = db.query(TotoResult).order_by(TotoResult.draw_date.desc()).first()
    if not result:
        raise HTTPException(status_code=404, detail="No draws found")
    return result


@app.get("/draws/{draw_number}", response_model=DrawDetailsSchema)
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

    # Get winning locations
    locations = (
        db.query(WinningLocation)
        .filter(WinningLocation.draw_number == draw_number)
        .all()
    )
    processed_locations = []
    for location in locations:
        outlet_name, address = split_outlet_address(location.outlet_name)
        new_location = WinningLocationSchema(
            group_number=location.group_number,
            outlet_name=outlet_name,
            address=address,
            entry_type=location.entry_type,
        )
        processed_locations.append(new_location)

    return DrawDetailsSchema(
        draw_result=DrawResultSchema.model_validate(result),
        winning_shares=[WinningShareSchema.model_validate(share) for share in shares],
        snowball_info=[
            SnowballInfoSchema.model_validate(snowball) for snowball in snowballs
        ],
        winning_locations=processed_locations,
    )


@app.get("/draws", response_model=list[DrawResultSchema])
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

    draw_schemas = []

    for result in results:
        winner_shares = (
            db.query(WinningShare)
            .filter(WinningShare.draw_number == result.draw_number)
            .all()
            or []
        )

        total_winners = (
            sum(share.winner_count for share in winner_shares) if winner_shares else 0
        )
        total_prize = (
            sum(share.winner_count * share.share_amount for share in winner_shares)
            if winner_shares
            else 0
        )

        draw_schemas.append(
            DrawResultSchema(
                draw_number=result.draw_number,
                draw_date=result.draw_date,
                winning_numbers=result.winning_numbers,
                additional_number=result.additional_number,
                jackpot=result.jackpot if result.jackpot is not None else 0.0,
                total_winners=total_winners,
                total_prize=total_prize,
            )
        )

    return draw_schemas


@app.get("/search")
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


if __name__ == "__main__":
    uvicorn.run("api.main:app", host="::", reload=True)
