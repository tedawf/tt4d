import re
from datetime import date, datetime
from typing import Optional


DRAW_NO_RE = re.compile(r"Draw\s+No\.\s*(\d+)")


def text_or_none(node) -> Optional[str]:
    if node is None:
        return None
    value = node.get_text(strip=True)
    return value if value else None


def parse_draw_number(value: str) -> Optional[int]:
    match = DRAW_NO_RE.search(value)
    if not match:
        return None
    return int(match.group(1))


def parse_draw_date(value: str) -> Optional[date]:
    try:
        return datetime.strptime(value, "%a, %d %b %Y").date()
    except ValueError:
        return None
