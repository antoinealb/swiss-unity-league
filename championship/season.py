import datetime
from dataclasses import dataclass


@dataclass
class Season:
    id: int
    name: str
    start_date: datetime.date
    end_date: datetime.date
    result_deadline: datetime.timedelta = datetime.timedelta(days=7)

    def can_enter_results(self, on_date: datetime.date) -> bool:
        """Checks if results can still be added to this season on a given date."""
        return on_date <= self.end_date + self.result_deadline


SEASON_2023 = Season(
    id=1,
    start_date=datetime.date(2023, 1, 1),
    end_date=datetime.date(2023, 10, 31),
    name="Season 2023",
)

SEASON_2024 = Season(
    id=2,
    start_date=datetime.date(2023, 11, 1),
    end_date=datetime.date(2024, 10, 31),
    name="Season 2024",
)

_SEASON_LIST = [SEASON_2023, SEASON_2024]
SEASON_MAP = {s.id: s for s in _SEASON_LIST}
SEASONS_WITH_INFO = _SEASON_LIST


def find_current_season(date: datetime.date):
    for season in SEASON_MAP.values():
        if season.start_date <= date <= season.end_date:
            return season
