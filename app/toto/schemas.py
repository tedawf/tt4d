from datetime import date
from typing import Optional

from pydantic import Field

from app.core.schemas import ApiModel, ValidationMode


class TotoTriggerRequest(ApiModel):
    validation_mode: ValidationMode = Field(default="current")
    dry_run: bool = False


class TotoTriggerResponse(ApiModel):
    outcome: str
    requested_draw_number: int
    actual_draw_number: Optional[int] = None
    validation_mode: ValidationMode
    message: Optional[str] = None


class DrawResultSchema(ApiModel):
    draw_number: int
    draw_date: date
    winning_numbers: Optional[list[int]] = None
    additional_number: Optional[int] = None
    jackpot: Optional[float] = None
    total_winners: int
    total_prize: float
    is_complete: bool


class WinningShareSchema(ApiModel):
    group_number: int
    share_amount: float
    winner_count: int


class SnowballInfoSchema(ApiModel):
    group_number: int
    amount: float


class ItotoLocationSchema(ApiModel):
    outlet_name: str
    address: str
    share_count: int


class WinningTicketSchema(ApiModel):
    group_number: int
    outlet_name: str
    address: str
    entry_type: str
    is_itoto: bool = False
    itoto_locations: Optional[list[ItotoLocationSchema]] = None


class DrawDetailsSchema(ApiModel):
    draw_result: DrawResultSchema
    winning_shares: list[WinningShareSchema]
    snowball_info: list[SnowballInfoSchema]
    winning_tickets: list[WinningTicketSchema]
