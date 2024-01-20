from dataclasses import dataclass
from enum import Enum


class QualificationType(Enum):
    NONE = "NONE"
    LEADERBOARD = "LEADERBOARD"
    DIRECT = "DIRECT"


@dataclass
class LeaderboardScore:
    total_score: int
    rank: int
    byes: int = 0
    qualification_type: QualificationType = QualificationType.NONE
    qualification_reason: str = ""
