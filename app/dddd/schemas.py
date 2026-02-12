from typing import Optional

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class DdddFetchResponse(ApiModel):
    outcome: str
    requested_draw_number: int
    actual_draw_number: Optional[int] = None
    strict: bool
    message: Optional[str] = None
