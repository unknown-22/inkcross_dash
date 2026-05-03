from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from pydantic import TypeAdapter

from app.json_store import JsonListStore
from app.models import CalendarEvent

_EVENTS_ADAPTER = TypeAdapter(list[CalendarEvent])


class CalendarLoader:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load_all(self) -> list[CalendarEvent]:
        with self._path.open(encoding="utf-8") as file:
            return _EVENTS_ADAPTER.validate_python(json.load(file))

    def load_today(self, today: date) -> list[CalendarEvent]:
        events = self.load_all()
        return sorted(
            (event for event in events if event.start.date() == today),
            key=lambda event: event.start,
        )


class CalendarStore(JsonListStore[CalendarEvent]):
    def __init__(self, path: Path) -> None:
        super().__init__(path, _EVENTS_ADAPTER)
