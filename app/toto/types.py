from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Optional


@dataclass
class ParsedWinningShare:
    group: int
    amount: float
    count: int


@dataclass
class ParsedItotoLocation:
    outlet_name: str
    outlet_address: str
    share_count: int


@dataclass
class ParsedWinningTicket:
    outlet_name: str
    outlet_address: str
    entry_type: str
    is_itoto: bool
    itoto_locations: list[ParsedItotoLocation] = field(default_factory=list)


@dataclass
class ParsedGroupResult:
    has_winner: bool = False
    prize_amount: Optional[float] = None
    winning_count: int = 0
    snowball_amount: Optional[float] = None
    winning_tickets: list[ParsedWinningTicket] = field(default_factory=list)


@dataclass
class ParsedTotoDraw:
    requested_draw_number: int
    actual_draw_number: Optional[int] = None
    draw_date: Optional[date] = None
    winning_numbers: list[int] = field(default_factory=list)
    additional_number: Optional[int] = None
    winning_shares: list[ParsedWinningShare] = field(default_factory=list)
    jackpot: Optional[float] = None
    group1_result: ParsedGroupResult = field(default_factory=ParsedGroupResult)
    group2_result: ParsedGroupResult = field(default_factory=ParsedGroupResult)
    parse_errors: list[str] = field(default_factory=list)
    is_complete: bool = True

    def normalized_payload(self) -> dict:
        return {
            "requested_draw_number": self.requested_draw_number,
            "actual_draw_number": self.actual_draw_number,
            "draw_date": self.draw_date.isoformat() if self.draw_date else None,
            "winning_numbers": self.winning_numbers,
            "additional_number": self.additional_number,
            "winning_shares": [asdict(item) for item in self.winning_shares],
            "jackpot": self.jackpot,
            "group1_result": asdict(self.group1_result),
            "group2_result": asdict(self.group2_result),
            "is_complete": self.is_complete,
            "parse_errors": self.parse_errors,
        }


@dataclass
class TotoRunResult:
    outcome: str
    requested_draw_number: int
    validation_mode: str
    actual_draw_number: Optional[int] = None
    message: Optional[str] = None
