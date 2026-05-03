from __future__ import annotations

import json
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import TypeAdapter

T = TypeVar("T")


class JsonListStore(Generic[T]):
    def __init__(self, path: Path, adapter: TypeAdapter[list[T]]) -> None:
        self._path = path
        self._adapter = adapter

    def load_all(self) -> list[T]:
        with self._path.open(encoding="utf-8") as file:
            return self._adapter.validate_python(json.load(file))

    def append(self, item: T) -> list[T]:
        items = [*self.load_all(), item]
        return self.replace_all(items)

    def replace_all(self, items: list[T]) -> list[T]:
        validated_items = self._adapter.validate_python(items)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        serialized = self._adapter.dump_python(validated_items, mode="json")
        self._path.write_text(
            json.dumps(serialized, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return validated_items
