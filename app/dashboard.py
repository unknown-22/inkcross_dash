from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.calendar_loader import CalendarLoader
from app.models import DashboardData
from app.todo_loader import TodoLoader
from app.weather import OpenMeteoClient

WEEKDAYS = ("月", "火", "水", "木", "金", "土", "日")
TOKYO_TZ = ZoneInfo("Asia/Tokyo")


class DashboardService:
    def __init__(
        self,
        weather_client: OpenMeteoClient,
        calendar_loader: CalendarLoader,
        todo_loader: TodoLoader,
    ) -> None:
        self._weather_client = weather_client
        self._calendar_loader = calendar_loader
        self._todo_loader = todo_loader

    @classmethod
    def from_project_root(cls, root: Path) -> DashboardService:
        return cls(
            weather_client=OpenMeteoClient(),
            calendar_loader=CalendarLoader(root / "data" / "calendar.json"),
            todo_loader=TodoLoader(root / "data" / "todo.json"),
        )

    async def build(self, now: datetime | None = None) -> DashboardData:
        generated_at = now.astimezone(TOKYO_TZ) if now is not None else datetime.now(TOKYO_TZ)
        today = generated_at.date()
        return DashboardData(
            generated_at=generated_at,
            weekday=WEEKDAYS[generated_at.weekday()],
            weather=await self._weather_client.fetch(now=generated_at),
            events=self._calendar_loader.load_today(today),
            todos=self._todo_loader.load_open(),
        )
