from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from pydantic import TypeAdapter

from app.models import CalendarEvent

_EVENTS_ADAPTER = TypeAdapter(list[CalendarEvent])


class CalendarLoader:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load_today(self, today: date) -> list[CalendarEvent]:
        with self._path.open(encoding="utf-8") as file:
            events = _EVENTS_ADAPTER.validate_python(json.load(file))
        return sorted(
            (event for event in events if event.start.date() == today),
            key=lambda event: event.start,
        )
