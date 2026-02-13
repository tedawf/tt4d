from datetime import date
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Path, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.core.auth import api_key_auth
from app.core.database import get_db
from app.dddd.models import DdddDraw
from app.dddd.schemas import (
    DdddDrawResultSchema,
    DdddTriggerRequest,
    DdddTriggerResponse,
)
from app.dddd.service import run_trigger_next, run_trigger_replay

draws_router = APIRouter(prefix="/dddd/draws", tags=["DDDD Draws"])
jobs_router = APIRouter(prefix="/dddd/jobs", tags=["DDDD Jobs"])


@draws_router.get("", response_model=list[DdddDrawResultSchema])
def get_draws(
    skip: int = 0,
    limit: int = 10,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    query = select(DdddDraw)
    if start_date:
        query = query.where(DdddDraw.draw_date >= start_date)
    if end_date:
        query = query.where(DdddDraw.draw_date <= end_date)

    rows = (
        db.execute(
            query.options(selectinload(DdddDraw.prizes))
            .order_by(desc(DdddDraw.draw_number))
            .offset(skip)
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [_map_draw_result(row) for row in rows]


@draws_router.get("/latest", response_model=DdddDrawResultSchema)
def get_latest_draw(db: Session = Depends(get_db)):
    row = (
        db.execute(
            select(DdddDraw)
            .options(selectinload(DdddDraw.prizes))
            .order_by(desc(DdddDraw.draw_number))
            .limit(1)
        )
        .scalars()
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No 4D draws found",
        )
    return _map_draw_result(row)


@draws_router.get("/{draw_number}", response_model=DdddDrawResultSchema)
def get_draw(draw_number: int, db: Session = Depends(get_db)):
    row = (
        db.execute(
            select(DdddDraw)
            .options(selectinload(DdddDraw.prizes))
            .where(DdddDraw.draw_number == draw_number)
        )
        .scalars()
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"4D draw ({draw_number}) not found",
        )
    return _map_draw_result(row)


@jobs_router.post(
    "/trigger", response_model=DdddTriggerResponse, dependencies=[Depends(api_key_auth)]
)
def trigger_next_draw(
    payload: DdddTriggerRequest = Body(default_factory=DdddTriggerRequest),
    db: Session = Depends(get_db),
):
    result = _run_or_400(
        run_trigger_next,
        db,
        validation_mode=payload.validation_mode,
        dry_run=payload.dry_run,
    )
    return _to_trigger_response(result)


@jobs_router.post(
    "/trigger/{draw_number}",
    response_model=DdddTriggerResponse,
    dependencies=[Depends(api_key_auth)],
)
def trigger_specific_draw(
    draw_number: int = Path(..., ge=1),
    payload: DdddTriggerRequest = Body(default_factory=DdddTriggerRequest),
    db: Session = Depends(get_db),
):
    result = _run_or_400(
        run_trigger_replay,
        db,
        draw_number=draw_number,
        validation_mode=payload.validation_mode,
        dry_run=payload.dry_run,
    )
    return _to_trigger_response(result)


def _run_or_400(trigger_fn, db: Session, **kwargs):
    try:
        return trigger_fn(db, **kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _to_trigger_response(result) -> DdddTriggerResponse:
    return DdddTriggerResponse(
        outcome=result.outcome,
        requested_draw_number=result.requested_draw_number,
        actual_draw_number=result.actual_draw_number,
        validation_mode=result.validation_mode,
        message=result.message,
    )


def _map_draw_result(row: DdddDraw) -> DdddDrawResultSchema:
    first = None
    second = None
    third = None
    starter: list[str] = []
    consolation: list[str] = []

    tier_order = {"1": 1, "2": 2, "3": 3, "S": 4, "C": 5}
    for prize in sorted(
        row.prizes,
        key=lambda item: (tier_order.get(item.tier, 99), item.tier_idx),
    ):
        if prize.tier == "1":
            first = prize.number
        elif prize.tier == "2":
            second = prize.number
        elif prize.tier == "3":
            third = prize.number
        elif prize.tier == "S":
            starter.append(prize.number)
        elif prize.tier == "C":
            consolation.append(prize.number)

    return DdddDrawResultSchema(
        draw_number=row.draw_number,
        draw_date=row.draw_date,
        first=first,
        second=second,
        third=third,
        starter=starter,
        consolation=consolation,
    )


router = jobs_router
