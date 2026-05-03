from __future__ import annotations

import json
from pathlib import Path

from pydantic import TypeAdapter

from app.json_store import JsonListStore
from app.models import TodoItem

_TODO_ADAPTER = TypeAdapter(list[TodoItem])


class TodoLoader:
    def __init__(self, path: Path, limit: int = 8) -> None:
        self._path = path
        self._limit = limit

    def load_all(self) -> list[TodoItem]:
        with self._path.open(encoding="utf-8") as file:
            return _TODO_ADAPTER.validate_python(json.load(file))

    def load_open(self) -> list[TodoItem]:
        todos = self.load_all()
        return [todo for todo in todos if not todo.done][: self._limit]


class TodoStore(JsonListStore[TodoItem]):
    def __init__(self, path: Path) -> None:
        super().__init__(path, _TODO_ADAPTER)
