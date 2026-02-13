from datetime import date
from typing import Optional

from app.core.schemas import ApiModel, ValidationMode


class DdddTriggerRequest(ApiModel):
    validation_mode: ValidationMode = "current"
    dry_run: bool = False


class DdddTriggerResponse(ApiModel):
    outcome: str
    requested_draw_number: int
    actual_draw_number: Optional[int] = None
    validation_mode: ValidationMode
    message: Optional[str] = None


class DdddDrawResultSchema(ApiModel):
    draw_number: int
    draw_date: date
    first: Optional[str] = None
    second: Optional[str] = None
    third: Optional[str] = None
    starter: list[str]
    consolation: list[str]
