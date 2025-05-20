from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class DrawResultSchema(ApiModel):
    draw_number: int
    draw_date: datetime
    winning_numbers: List[int]
    additional_number: int
    jackpot: Optional[float]
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
    itoto_locations: Optional[List[ItotoLocationSchema]] = None


class DrawDetailsSchema(ApiModel):
    draw_result: DrawResultSchema
    winning_shares: List[WinningShareSchema]
    snowball_info: List[SnowballInfoSchema]
    winning_tickets: List[WinningTicketSchema]


class ScrapeTaskStatus(str, Enum):
    INITIATED = "initiated"
    ALREADY_EXISTS = "already_exists"
    FAILED_TO_INITIATE = "failed_to_initiate"


class ScrapeResultSchema(ApiModel):
    status: ScrapeTaskStatus
    message: Optional[str] = None
    target_draw_number: Optional[int] = None
