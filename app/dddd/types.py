from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


@dataclass
class ParsedDdddDraw:
    requested_draw_number: int
    actual_draw_number: Optional[int] = None
    draw_date: Optional[date] = None
    first: Optional[str] = None
    second: Optional[str] = None
    third: Optional[str] = None
    starter: List[str] = field(default_factory=list)
    consolation: List[str] = field(default_factory=list)
    parse_errors: List[str] = field(default_factory=list)

    def all_prizes(self) -> List[str]:
        prizes: List[str] = []
        for value in [self.first, self.second, self.third]:
            if value is not None:
                prizes.append(value)
        prizes.extend(self.starter)
        prizes.extend(self.consolation)
        return prizes


@dataclass
class FetchResult:
    source_url: str
    http_status: Optional[int]
    html: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class DdddRunResult:
    outcome: str
    requested_draw_number: int
    actual_draw_number: Optional[int] = None
    message: Optional[str] = None
