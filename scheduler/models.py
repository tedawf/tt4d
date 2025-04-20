from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class WinningShare:
    group: int = 0
    amount: float = 0.0
    count: int = 0


@dataclass
class ItotoLocation:
    outlet_name: str
    outlet_address: str
    share_count: int


@dataclass
class WinningTicket:
    outlet_name: str
    outlet_address: str
    entry_type: str
    is_itoto: bool
    itoto_locations: Optional[List[ItotoLocation]] = None

    def __post_init__(self):
        if self.itoto_locations is None:
            self.itoto_locations = []


@dataclass
class GroupResult:
    has_winner: bool = False
    prize_amount: Optional[float] = None
    winning_count: int = 0
    snowball_amount: Optional[float] = None
    winning_tickets: List[WinningTicket] = None

    def __post_init__(self):
        if self.winning_tickets is None:
            self.winning_tickets = []


@dataclass
class DrawResult:
    draw_date: datetime
    draw_number: int
    winning_numbers: List[int]
    additional_number: int
    winning_shares: List[WinningShare]
    jackpot: float
    group1_result: Optional[GroupResult] = None
    group2_result: Optional[GroupResult] = None
