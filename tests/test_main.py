from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.calendar_loader import CalendarStore
from app.todo_loader import TodoStore
import main


class FakeService:
    async def build(self) -> object:
        return object()


class FakeFailingService:
    async def build(self) -> object:
        raise RuntimeError("failed")


class FakeRenderer:
    def render_html(self, data: object) -> str:
        return "<!doctype html><html><body>fake</body></html>"

    async def render_bmp(self, data: object) -> bytes:
        return b"BMfake"


def test_main_uses_default_port(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_run(*args: object, **kwargs: object) -> None:
        captured["args"] = args
        captured["kwargs"] = kwargs

    monkeypatch.setattr(main.uvicorn, "run", fake_run)
    monkeypatch.setattr("sys.argv", ["main.py"])

    main.main()

    assert captured["args"] == ("main:app",)
    assert captured["kwargs"] == {"host": "0.0.0.0", "port": 8080, "reload": False}


def test_main_uses_port_argument(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_run(*args: object, **kwargs: object) -> None:
        captured["args"] = args
        captured["kwargs"] = kwargs

    monkeypatch.setattr(main.uvicorn, "run", fake_run)
    monkeypatch.setattr("sys.argv", ["main.py", "--port", "9000"])

    main.main()

    assert captured["args"] == ("main:app",)
    assert captured["kwargs"] == {"host": "0.0.0.0", "port": 9000, "reload": False}


@pytest.mark.asyncio
async def test_dashboard_bmp_response() -> None:
    main.app.state.dashboard_service = FakeService()
    main.app.state.dashboard_renderer = FakeRenderer()

    response = await main.dashboard_bmp()

    assert response.media_type == "image/bmp"
    assert response.headers["cache-control"] == "no-store"
    assert response.body == b"BMfake"


@pytest.mark.asyncio
async def test_dashboard_bmp_returns_500_on_generation_error() -> None:
    main.app.state.dashboard_service = FakeFailingService()
    main.app.state.dashboard_renderer = FakeRenderer()

    with pytest.raises(HTTPException) as exc_info:
        await main.dashboard_bmp()

    exception = exc_info.value
    assert exception.status_code == 500
    assert exception.detail == "dashboard generation failed"


@pytest.mark.asyncio
async def test_dashboard_html_response() -> None:
    main.app.state.dashboard_service = FakeService()
    main.app.state.dashboard_renderer = FakeRenderer()

    response = await main.dashboard_html()

    assert response.media_type == "text/html"
    assert response.headers["cache-control"] == "no-store"
    assert response.body == b"<!doctype html><html><body>fake</body></html>"


@pytest.mark.asyncio
async def test_dashboard_html_returns_500_on_generation_error() -> None:
    main.app.state.dashboard_service = FakeFailingService()
    main.app.state.dashboard_renderer = FakeRenderer()

    with pytest.raises(HTTPException) as exc_info:
        await main.dashboard_html()

    exception = exc_info.value
    assert exception.status_code == 500
    assert exception.detail == "dashboard generation failed"


def test_calendar_api_get_add_and_refresh(tmp_path) -> None:
    path = tmp_path / "calendar.json"
    path.write_text(
        json.dumps([{"title": "existing", "start": "2026-05-03T09:00:00"}]),
        encoding="utf-8",
    )

    with TestClient(main.app) as client:
        main.app.state.calendar_store = CalendarStore(path)

        get_response = client.get("/calendar")
        post_response = client.post(
            "/calendar/add",
            json={"title": "added", "start": "2026-05-03T10:00:00", "end": None, "location": None},
        )
        refresh_response = client.post(
            "/calendar/refresh",
            json=[{"title": "refreshed", "start": "2026-05-04T11:00:00"}],
        )
        old_post_response = client.post(
            "/calendar",
            json={"title": "old", "start": "2026-05-05T10:00:00"},
        )
        old_put_response = client.put(
            "/calendar",
            json=[{"title": "old", "start": "2026-05-05T10:00:00"}],
        )

    assert get_response.status_code == 200
    assert [item["title"] for item in get_response.json()] == ["existing"]
    assert post_response.status_code == 201
    assert [item["title"] for item in post_response.json()] == ["existing", "added"]
    assert refresh_response.status_code == 200
    assert [item["title"] for item in refresh_response.json()] == ["refreshed"]
    assert old_post_response.status_code == 405
    assert old_put_response.status_code == 405
    assert [item["title"] for item in json.loads(path.read_text(encoding="utf-8"))] == ["refreshed"]


def test_todo_api_get_add_and_refresh(tmp_path) -> None:
    path = tmp_path / "todo.json"
    path.write_text(
        json.dumps([{"title": "existing", "done": False, "due": None}]),
        encoding="utf-8",
    )

    with TestClient(main.app) as client:
        main.app.state.todo_store = TodoStore(path)

        get_response = client.get("/todo")
        post_response = client.post(
            "/todo/add",
            json={"title": "added", "done": False, "due": "2026-05-03"},
        )
        refresh_response = client.post(
            "/todo/refresh",
            json=[{"title": "refreshed", "done": True, "due": None}],
        )
        old_post_response = client.post(
            "/todo",
            json={"title": "old", "done": False, "due": None},
        )
        old_put_response = client.put(
            "/todo",
            json=[{"title": "old", "done": False, "due": None}],
        )

    assert get_response.status_code == 200
    assert [item["title"] for item in get_response.json()] == ["existing"]
    assert post_response.status_code == 201
    assert [item["title"] for item in post_response.json()] == ["existing", "added"]
    assert refresh_response.status_code == 200
    assert [item["title"] for item in refresh_response.json()] == ["refreshed"]
    assert old_post_response.status_code == 405
    assert old_put_response.status_code == 405
    assert [item["title"] for item in json.loads(path.read_text(encoding="utf-8"))] == ["refreshed"]
