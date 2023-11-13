from dataclasses import dataclass
from typing import Optional


@dataclass
class ParseResult:
    """A dataclass to store the results of parsing a standings page."""

    name: str
    points: int
    record: tuple
    deck_name: Optional[str] = None
    decklist_url: Optional[str] = None
