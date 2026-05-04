from __future__ import annotations

import argparse
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import cast

import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import Response

from app.calendar_loader import CalendarStore
from app.dashboard import DashboardService
from app.models import CalendarEvent, TodoItem
from app.renderer import DashboardRenderer
from app.todo_loader import TodoStore

ROOT = Path(__file__).parent
DEFAULT_PORT = 8080


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    service = DashboardService.from_project_root(ROOT)
    calendar_store = CalendarStore(ROOT / "data" / "calendar.json")
    todo_store = TodoStore(ROOT / "data" / "todo.json")
    async with DashboardRenderer(ROOT / "templates") as renderer:
        app.state.dashboard_service = service
        app.state.dashboard_renderer = renderer
        app.state.calendar_store = calendar_store
        app.state.todo_store = todo_store
        yield


app = FastAPI(title="Inkcross Dashboard", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/dashboard.bmp")
async def dashboard_bmp() -> Response:
    service = cast(DashboardService, app.state.dashboard_service)
    renderer = cast(DashboardRenderer, app.state.dashboard_renderer)
    try:
        data = await service.build()
        bmp = await renderer.render_bmp(data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="dashboard generation failed") from exc
    return Response(
        content=bmp,
        media_type="image/bmp",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/calendar")
async def get_calendar() -> list[CalendarEvent]:
    store = cast(CalendarStore, app.state.calendar_store)
    return store.load_all()


@app.post("/calendar/add", status_code=status.HTTP_201_CREATED)
async def add_calendar_event(event: CalendarEvent) -> list[CalendarEvent]:
    store = cast(CalendarStore, app.state.calendar_store)
    return store.append(event)


@app.post("/calendar/refresh")
async def refresh_calendar(events: list[CalendarEvent]) -> list[CalendarEvent]:
    store = cast(CalendarStore, app.state.calendar_store)
    return store.replace_all(events)


@app.get("/todo")
async def get_todo() -> list[TodoItem]:
    store = cast(TodoStore, app.state.todo_store)
    return store.load_all()


@app.post("/todo/add", status_code=status.HTTP_201_CREATED)
async def add_todo(todo: TodoItem) -> list[TodoItem]:
    store = cast(TodoStore, app.state.todo_store)
    return store.append(todo)


@app.post("/todo/refresh")
async def refresh_todo(todos: list[TodoItem]) -> list[TodoItem]:
    store = cast(TodoStore, app.state.todo_store)
    return store.replace_all(todos)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Inkcross Dashboard server.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    uvicorn.run("main:app", host="0.0.0.0", port=args.port, reload=False)


if __name__ == "__main__":
    main()
