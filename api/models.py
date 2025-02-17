from datetime import datetime

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
    winning_numbers: list[int]
    additional_number: int
    draw_date: datetime
    jackpot: float
    created_at: datetime
    total_winners: int
    total_prize: int


class WinningShareSchema(ApiModel):
    group_number: int
    share_amount: float
    winner_count: int


class SnowballInfoSchema(ApiModel):
    group_number: int
    amount: float


class WinningLocationSchema(ApiModel):
    group_number: int
    outlet_name: str
    address: str
    entry_type: str


class DrawDetailsSchema(ApiModel):
    draw_result: DrawResultSchema
    winning_shares: list[WinningShareSchema]
    snowball_info: list[SnowballInfoSchema]
    winning_locations: list[WinningLocationSchema]
