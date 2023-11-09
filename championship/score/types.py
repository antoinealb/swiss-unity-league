from dataclasses import dataclass


@dataclass
class Score:
    total_score: int
    rank: int
    byes: int
    qualified: bool
