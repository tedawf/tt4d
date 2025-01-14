from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class WinningLocation:
    outlet_name: str
    entry_type: str


@dataclass
class GroupResult:
    has_winner: bool = False
    prize_amount: Optional[float] = None
    winning_count: int = 0
    snowball_amount: Optional[float] = None
    winning_locations: List[WinningLocation] = None

    def __post_init__(self):
        if self.winning_locations is None:
            self.winning_locations = []


@dataclass
class DrawResult:
    draw_date: datetime
    draw_number: int
    winning_numbers: List[int]
    additional_number: int
    winning_shares: List[Dict]
    jackpot: float
    group1_result: Optional[GroupResult] = None
    group2_result: Optional[GroupResult] = None
