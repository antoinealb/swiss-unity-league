from dataclasses import dataclass


@dataclass
class LeaderboardScore:
    total_score: int
    rank: int
    byes: int
    qualified: bool
