"""Offline Annex 2 reference scenario; never an activation schedule."""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from .const import LETTERS, PLAN

UK = ZoneInfo("Europe/London")
UTC = timezone.utc

@dataclass(frozen=True)
class Scenario:
    rota: str
    level: int
    start_date: date
    end_date: date
    plan_type: str = PLAN

    def __post_init__(self):
        if self.rota not in LETTERS or type(self.level) is not int or not 1 <= self.level <= 18:
            raise ValueError("Invalid rota or level")
        if self.plan_type != PLAN:
            raise ValueError("LLDP and actual activation schedules cannot be derived from Annex 2")
        if self.end_date < self.start_date or (self.end_date-self.start_date).days > 366:
            raise ValueError("Use an ordered range of at most 367 rota dates")

    @property
    def start(self):
        return datetime.combine(self.start_date, time(0,30), UK).astimezone(UTC)

    @property
    def end(self):
        return datetime.combine(self.end_date+timedelta(days=1), time(0,30), UK).astimezone(UTC)

    def intervals(self, tables):
        """Merged half-open OFF intervals, clipped to explicit rota-date validity."""
        row = tables[self.level-1][LETTERS.index(self.rota)]
        result = []
        day = self.start_date
        while day <= self.end_date:
            for slot in range(8):
                if not row[day.weekday()*8+slot]:
                    continue
                start = datetime.combine(day, time(0,30), UK)+timedelta(hours=slot*3)
                end = start+timedelta(hours=3)
                start, end = start.astimezone(UTC), end.astimezone(UTC)
                if result and result[-1][1] == start:
                    result[-1] = (result[-1][0], end)
                else:
                    result.append((start,end))
            day += timedelta(days=1)
        return result

    def evaluate(self, now, intervals):
        if now.tzinfo is None:
            raise ValueError("An aware datetime is required")
        now = now.astimezone(UTC)
        active = self.start <= now < self.end
        off = any(a <= now < b for a,b in intervals) if active else None
        restriction = next((a for a,b in intervals if a > now), None)
        # End of validity is not evidence of restoration.
        restoration = next((b for a,b in intervals if b > now and b < self.end), None)
        return off, restriction, restoration


def from_settings(settings):
    return Scenario(settings["rota"], settings["level"], date.fromisoformat(settings["start_date"]),
                    date.fromisoformat(settings["end_date"]), settings["plan_type"])
