from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.auth import api_key_auth
from app.database import get_db
from app.dddd.schemas import DdddFetchResponse
from app.dddd.service import is_strict_mode, run_fetch_next, run_fetch_replay

router = APIRouter(prefix="/jobs/dddd", tags=["DDDD Jobs"])


@router.post("/fetch", response_model=DdddFetchResponse, dependencies=[Depends(api_key_auth)])
def fetch_next_draw(db: Session = Depends(get_db)):
    strict = is_strict_mode()
    result = run_fetch_next(db, strict=strict)
    return DdddFetchResponse(
        outcome=result.outcome,
        requested_draw_number=result.requested_draw_number,
        actual_draw_number=result.actual_draw_number,
        strict=strict,
        message=result.message,
    )


@router.post(
    "/fetch/{draw_number}",
    response_model=DdddFetchResponse,
    dependencies=[Depends(api_key_auth)],
)
def fetch_specific_draw(
    draw_number: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    strict = is_strict_mode()
    result = run_fetch_replay(db, draw_number=draw_number, strict=strict)
    return DdddFetchResponse(
        outcome=result.outcome,
        requested_draw_number=result.requested_draw_number,
        actual_draw_number=result.actual_draw_number,
        strict=strict,
        message=result.message,
    )
