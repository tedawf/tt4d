from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import SnowballInfo, TotoResult, WinningLocation, WinningShare

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


@app.get("/draws/{draw_number}")
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

    return {
        "draw": result,
        "winning_shares": shares,
        "snowball_info": snowballs,
        "winning_locations": locations,
    }


@app.get("/draws")
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

    return results


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
