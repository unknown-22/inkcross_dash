from __future__ import annotations

import json
from datetime import date, datetime

from app.calendar_loader import CalendarLoader
from app.calendar_loader import CalendarStore
from app.models import CalendarEvent, TodoItem
from app.todo_loader import TodoLoader
from app.todo_loader import TodoStore


def test_calendar_loader_filters_today_and_sorts(tmp_path) -> None:
    path = tmp_path / "calendar.json"
    path.write_text(
        json.dumps(
            [
                {"title": "later", "start": "2026-05-03T15:00:00"},
                {"title": "other day", "start": "2026-05-04T09:00:00"},
                {"title": "earlier", "start": "2026-05-03T09:00:00"},
            ]
        ),
        encoding="utf-8",
    )

    events = CalendarLoader(path).load_today(date(2026, 5, 3))

    assert [event.title for event in events] == ["earlier", "later"]


def test_todo_loader_filters_done_and_applies_limit(tmp_path) -> None:
    path = tmp_path / "todo.json"
    path.write_text(
        json.dumps(
            [
                {"title": "one", "done": False, "due": None},
                {"title": "done", "done": True, "due": None},
                {"title": "two", "done": False, "due": "2026-05-03"},
            ]
        ),
        encoding="utf-8",
    )

    todos = TodoLoader(path, limit=1).load_open()

    assert [todo.title for todo in todos] == ["one"]


def test_calendar_store_appends_and_replaces_all(tmp_path) -> None:
    path = tmp_path / "calendar.json"
    path.write_text("[]", encoding="utf-8")
    store = CalendarStore(path)

    appended = store.append(CalendarEvent(title="meeting", start=datetime(2026, 5, 3, 9)))
    replaced = store.replace_all(
        [
            CalendarEvent(
                title="lunch",
                start=datetime(2026, 5, 4, 12),
                location="Tokyo",
            )
        ]
    )

    assert [event.title for event in appended] == ["meeting"]
    assert [event.title for event in replaced] == ["lunch"]
    assert [event.title for event in store.load_all()] == ["lunch"]


def test_todo_store_appends_and_replaces_all(tmp_path) -> None:
    path = tmp_path / "todo.json"
    path.write_text("[]", encoding="utf-8")
    store = TodoStore(path)

    appended = store.append(TodoItem(title="buy milk", done=False))
    replaced = store.replace_all(
        [TodoItem(title="submit invoice", done=True, due=date(2026, 5, 3))]
    )

    assert [todo.title for todo in appended] == ["buy milk"]
    assert [todo.title for todo in replaced] == ["submit invoice"]
    assert [todo.title for todo in store.load_all()] == ["submit invoice"]
