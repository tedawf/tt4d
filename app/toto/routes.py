from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.core.auth import api_key_auth
from app.core.database import get_db
from app.toto.models import TotoDraw, TotoSnowball, TotoWinningShare, TotoWinningTicket
from app.toto.schemas import (
    DrawDetailsSchema,
    DrawResultSchema,
    ItotoLocationSchema,
    SnowballInfoSchema,
    TotoTriggerRequest,
    TotoTriggerResponse,
    WinningShareSchema,
    WinningTicketSchema,
)
from app.toto.service import run_trigger_next, run_trigger_replay

draws_router = APIRouter(prefix="/toto/draws", tags=["Toto Draws"])
jobs_router = APIRouter(prefix="/toto/jobs", tags=["Toto Jobs"])


@draws_router.get("", response_model=list[DrawResultSchema])
def get_draws(
    skip: int = 0,
    limit: int = 10,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    query = select(TotoDraw)
    if start_date:
        query = query.where(TotoDraw.draw_date >= start_date)
    if end_date:
        query = query.where(TotoDraw.draw_date <= end_date)

    rows = (
        db.execute(
            query.options(selectinload(TotoDraw.winning_shares))
            .order_by(desc(TotoDraw.draw_date))
            .offset(skip)
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [_map_draw_result(row, row.winning_shares) for row in rows]


@draws_router.get("/latest", response_model=DrawResultSchema)
def get_latest_draw(db: Session = Depends(get_db)):
    row = (
        db.execute(
            select(TotoDraw)
            .options(selectinload(TotoDraw.winning_shares))
            .order_by(desc(TotoDraw.draw_date))
            .limit(1)
        )
        .scalars()
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No draws found",
        )
    return _map_draw_result(row, row.winning_shares)


@draws_router.get("/search")
def search_numbers(
    numbers: str = Query(
        ...,
        description="Space-separated numbers to search for (e.g., '12 13 14')",
        min_length=1,
        pattern=r"^\d+( \d+)*$",
    ),
    db: Session = Depends(get_db),
):
    try:
        input_numbers = [int(n) for n in numbers.split()]
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input: numbers must be space-separated integers",
        ) from exc

    if not input_numbers:
        raise HTTPException(
            status_code=400, detail="Please provide at least one number"
        )
    if not all(1 <= n <= 49 for n in input_numbers):
        raise HTTPException(
            status_code=400, detail="All numbers must be between 1 and 49"
        )
    if len(input_numbers) > 6:
        raise HTTPException(status_code=400, detail="Search must not exceed 6 numbers")
    if len(set(input_numbers)) != len(input_numbers):
        raise HTTPException(status_code=400, detail="Numbers must not repeat")

    rows = (
        db.execute(
            select(TotoDraw)
            .options(selectinload(TotoDraw.winning_shares))
            .where(TotoDraw.winning_numbers.contains(input_numbers))
            .order_by(desc(TotoDraw.draw_date))
        )
        .scalars()
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No draws found")

    return [_map_draw_result(row, row.winning_shares) for row in rows]


@draws_router.get("/{draw_number}", response_model=DrawDetailsSchema)
def get_draw(draw_number: int, db: Session = Depends(get_db)):
    row = db.get(TotoDraw, draw_number)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Draw ({draw_number}) not found",
        )

    shares = (
        db.execute(
            select(TotoWinningShare).where(TotoWinningShare.draw_number == draw_number)
        )
        .scalars()
        .all()
    )
    snowballs = (
        db.execute(select(TotoSnowball).where(TotoSnowball.draw_number == draw_number))
        .scalars()
        .all()
    )
    tickets = (
        db.execute(
            select(TotoWinningTicket)
            .options(selectinload(TotoWinningTicket.itoto_locations))
            .where(TotoWinningTicket.draw_number == draw_number)
        )
        .scalars()
        .all()
    )

    return DrawDetailsSchema(
        draw_result=_map_draw_result(row, shares),
        winning_shares=[WinningShareSchema.model_validate(s) for s in shares],
        snowball_info=[SnowballInfoSchema.model_validate(s) for s in snowballs],
        winning_tickets=_map_winning_tickets(tickets),
    )


@jobs_router.post(
    "/trigger", response_model=TotoTriggerResponse, dependencies=[Depends(api_key_auth)]
)
def trigger_next_draw(
    payload: TotoTriggerRequest = Body(default_factory=TotoTriggerRequest),
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
    response_model=TotoTriggerResponse,
    dependencies=[Depends(api_key_auth)],
)
def trigger_specific_draw(
    draw_number: int = Path(..., ge=1),
    payload: TotoTriggerRequest = Body(default_factory=TotoTriggerRequest),
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


def _to_trigger_response(result) -> TotoTriggerResponse:
    return TotoTriggerResponse(
        outcome=result.outcome,
        requested_draw_number=result.requested_draw_number,
        actual_draw_number=result.actual_draw_number,
        validation_mode=result.validation_mode,
        message=result.message,
    )


def _map_winning_tickets(tickets: list[TotoWinningTicket]) -> list[WinningTicketSchema]:
    rows: list[WinningTicketSchema] = []
    for ticket in tickets:
        if ticket.is_itoto:
            rows.append(
                WinningTicketSchema(
                    group_number=ticket.group_number,
                    outlet_name="iTOTO - System 12",
                    address="",
                    entry_type=ticket.entry_type,
                    is_itoto=True,
                    itoto_locations=[
                        ItotoLocationSchema(
                            outlet_name=item.outlet_name,
                            address=item.outlet_address,
                            share_count=item.share_count,
                        )
                        for item in ticket.itoto_locations
                    ],
                )
            )
        else:
            rows.append(
                WinningTicketSchema(
                    group_number=ticket.group_number,
                    outlet_name=ticket.outlet_name,
                    address=ticket.outlet_address,
                    entry_type=ticket.entry_type,
                    is_itoto=False,
                )
            )
    return rows


def _map_draw_result(row: TotoDraw, shares: list[TotoWinningShare]) -> DrawResultSchema:
    total_winners = sum(item.winner_count for item in shares) if shares else 0
    total_prize = float(
        sum(item.winner_count * Decimal(item.share_amount) for item in shares)
        if shares
        else 0
    )

    return DrawResultSchema(
        draw_number=row.draw_number,
        draw_date=row.draw_date,
        winning_numbers=row.winning_numbers,
        additional_number=row.additional_number,
        jackpot=float(row.jackpot) if row.jackpot is not None else None,
        total_winners=total_winners,
        total_prize=total_prize,
        is_complete=row.is_complete,
    )
