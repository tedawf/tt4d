from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class ParsedWinningShare:
    group: int = 0
    amount: float = 0.0
    count: int = 0


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
    itoto_locations: Optional[List[ParsedItotoLocation]] = None

    def __post_init__(self):
        if self.itoto_locations is None:
            self.itoto_locations = []


@dataclass
class ParsedGroupResult:
    has_winner: bool = False
    prize_amount: Optional[float] = None
    winning_count: int = 0
    snowball_amount: Optional[float] = None
    winning_tickets: List[ParsedWinningTicket] = None

    def __post_init__(self):
        if self.winning_tickets is None:
            self.winning_tickets = []


@dataclass
class ParsedDrawResult:
    draw_date: datetime
    draw_number: int
    winning_numbers: List[int]
    additional_number: int
    winning_shares: List[ParsedWinningShare]
    jackpot: float
    group1_result: Optional[ParsedGroupResult] = None
    group2_result: Optional[ParsedGroupResult] = None
